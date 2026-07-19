"""API tests (§7 step 22, §3.2): read-only artifact serving against a tiny
published run — alerts, windowed subgraphs, bundles, metrics, and the caveat
on every response."""

import json

import polars as pl
import pytest
from api import create_app, write_serving_index
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.schema import Alert, Domain, GraphStore, MotifType, conform
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path) -> TestClient:
    store = GraphStore(tmp_path / "interim")
    nodes = pl.DataFrame(
        {
            "node_id": [f"acct:n{i}" for i in range(6)],
            "node_type": ["account"] * 6,
            "domain": ["financial"] * 6,
            "time_first_seen": [1, 1, 2, 2, 3, 3],
            "raw_features": [[float(i)] for i in range(6)],
            "raw_attrs": [None] * 6,
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["acct:n0", "acct:n1", "acct:n2", "acct:n4"],
            "dst": ["acct:n1", "acct:n2", "acct:n3", "acct:n5"],
            "edge_type": ["pays"] * 4,
            "timestamp": [1, 2, 2, 3],
            "amount": [10.0, 20.0, 30.0, 40.0],
            "directed": [True] * 4,
            "raw_attrs": [None] * 4,
        }
    )
    store.write("toyapi", "nodes", nodes)
    store.write("toyapi", "edges", edges)

    alerts = pl.DataFrame(
        [
            Alert(
                alert_id=f"toyapi:run0:{r}",
                domain=Domain.FINANCIAL,
                dataset="toyapi",
                model_run_id="run0",
                rank=r,
                risk_score=1.0 - r / 10,
                member_node_ids=members,
                n_members=len(members),
                motif_type=MotifType.CYCLE if r == 1 else None,
            ).model_dump(mode="python")
            for r, members in [(1, ["acct:n0", "acct:n1"]), (2, ["acct:n4"])]
        ]
    )
    alerts_path = tmp_path / "alerts.parquet"
    import pyarrow.parquet as pq

    pq.write_table(conform("alerts", alerts), alerts_path)

    bundles = tmp_path / "explanations"
    bundles.mkdir()
    (bundles / "toyapi_run0_1.json").write_text(
        json.dumps({"alert_id": "toyapi:run0:1", "caveats": SCREENING_CAVEAT}), encoding="utf-8"
    )
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({"node_level": {"auc_pr": 0.5}}), encoding="utf-8")
    rigor_path = tmp_path / "multiseed.json"
    rigor_path.write_text(
        json.dumps({"kind": "multiseed_gnn", "aggregate": {"auc_pr_mean": 0.47}}),
        encoding="utf-8",
    )

    index = write_serving_index(
        tmp_path / "serving.json",
        {
            "toyapi": {
                "domain": "financial",
                "store_root": str(store.root),
                "alerts": str(alerts_path),
                "explanations": str(bundles),
                "metrics": [str(metrics_path), str(tmp_path / "absent.json")],
                "rigor": {
                    "multiseed_gatv2": str(rigor_path),
                    "absent_artifact": str(tmp_path / "nope.json"),
                },
            }
        },
    )
    return TestClient(create_app(index))


class TestEndpoints:
    def test_domains_and_datasets(self, client) -> None:
        r = client.get("/api/v1/domains")
        assert r.status_code == 200
        assert r.json()["domains"] == {"financial": ["toyapi"]}
        d = client.get("/api/v1/datasets").json()["datasets"][0]
        assert d["has_alerts"] and d["has_explanations"]
        assert d["n_metrics_files"] == 1  # the absent file is not counted

    def test_alert_queue_budget(self, client) -> None:
        body = client.get("/api/v1/datasets/toyapi/alerts", params={"budget": 1}).json()
        assert body["k_effective"] == 1
        assert body["alerts"][0]["alert_id"] == "toyapi:run0:1"
        assert body["alerts"][0]["rank"] == 1

    def test_alert_detail_and_404(self, client) -> None:
        ok = client.get("/api/v1/datasets/toyapi/alerts/toyapi:run0:2")
        assert ok.status_code == 200
        assert ok.json()["alert"]["n_members"] == 1
        assert client.get("/api/v1/datasets/toyapi/alerts/nope").status_code == 404
        assert client.get("/api/v1/datasets/ghost/alerts").status_code == 404

    def test_subgraph_windowing(self, client) -> None:
        body = client.get(
            "/api/v1/datasets/toyapi/subgraph/toyapi:run0:1", params={"hops": 1}
        ).json()
        ids = {n["node_id"] for n in body["nodes"]}
        # members n0,n1 + 1-hop neighbor n2 — the n4-n5 component must NOT ship
        assert ids == {"acct:n0", "acct:n1", "acct:n2"}
        members = {n["node_id"] for n in body["nodes"] if n["is_member"]}
        assert members == {"acct:n0", "acct:n1"}
        assert all("raw_features" not in n for n in body["nodes"])
        pairs = {(e["src"], e["dst"]) for e in body["edges"]}
        assert pairs == {("acct:n0", "acct:n1"), ("acct:n1", "acct:n2")}

    def test_subgraph_node_cap_truncates(self, client) -> None:
        body = client.get(
            "/api/v1/datasets/toyapi/subgraph/toyapi:run0:1",
            params={"hops": 2, "node_cap": 10},
        ).json()
        assert body["truncated"] is False  # tiny graph fits
        assert len(body["nodes"]) <= 10

    def test_explanations(self, client) -> None:
        ok = client.get("/api/v1/datasets/toyapi/explanations/toyapi:run0:1")
        assert ok.status_code == 200
        assert ok.json()["bundle"]["alert_id"] == "toyapi:run0:1"
        assert client.get("/api/v1/datasets/toyapi/explanations/toyapi:run0:2").status_code == 404

    def test_explanations_path_traversal_rejected(self, client, tmp_path) -> None:
        """Audit regression: separators in alert_id must never escape the
        bundles dir (the backslash variant leaked on Windows before the fix)."""
        (tmp_path / "outside.json").write_text("{}", encoding="utf-8")
        for candidate in ("..%5Coutside", "..%2Foutside", "....//outside", "a%00b"):
            r = client.get(f"/api/v1/datasets/toyapi/explanations/{candidate}")
            assert r.status_code == 404, candidate

    def test_metrics(self, client) -> None:
        body = client.get("/api/v1/datasets/toyapi/metrics").json()
        assert body["runs"][0]["metrics"]["node_level"]["auc_pr"] == 0.5

    def test_rigor(self, client) -> None:  # §7 steps 28–29 artifacts in the console
        r = client.get("/api/v1/datasets/toyapi/rigor")
        assert r.status_code == 200
        body = r.json()
        # present artifacts load; absent ones are silently omitted, never faked
        assert body["artifacts"]["multiseed_gatv2"]["payload"]["aggregate"]["auc_pr_mean"] == 0.47
        assert "absent_artifact" not in body["artifacts"]
        assert body["caveat"] == SCREENING_CAVEAT
        assert client.get("/api/v1/datasets/nope/rigor").status_code == 404

    def test_every_response_carries_the_caveat(self, client) -> None:
        for path in (
            "/api/v1/domains",
            "/api/v1/datasets",
            "/api/v1/datasets/toyapi/alerts",
            "/api/v1/datasets/toyapi/alerts/toyapi:run0:1",
            "/api/v1/datasets/toyapi/subgraph/toyapi:run0:1",
            "/api/v1/datasets/toyapi/explanations/toyapi:run0:1",
            "/api/v1/datasets/toyapi/metrics",
        ):
            body = client.get(path).json()
            assert body.get("caveat") == SCREENING_CAVEAT, path


def test_serving_never_imports_torch(tmp_path) -> None:
    """Deployment rule (docs/deployment.md §2): the serving path must be
    importable — AND buildable via create_app, which mounts the Copilot
    router — without torch; the container ships without it. The 2026-07-19
    audit closed the import-only hole: create_app's copilot mount reached
    torch through two eager package __init__ chains (copilot → agent →
    corpus → collusiongraph.explain → explainer runners), which import-only
    pinning never exercised."""
    import subprocess
    import sys

    serving = tmp_path / "serving.json"
    serving.write_text(json.dumps({"datasets": {}}), encoding="utf-8")
    code = (
        "import sys; sys.modules['torch'] = None\n"
        "import api  # must not touch torch on import\n"
        f"app = api.create_app({str(serving)!r})  # the copilot mount must stay lazy\n"
        "from fastapi.testclient import TestClient\n"
        "assert TestClient(app).get('/api/v1/copilot/health').status_code == 200\n"
        "print('ok')"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd="backend"
    )
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout
