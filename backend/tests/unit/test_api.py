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


class TestMotifBackfill:
    """Regression pin for a live bug found 2026-07-27.

    The ranking stage writes `alerts.parquet` BEFORE the explanation stage runs,
    so `motif_type` was null on every queue row even where the matcher later
    proved a shape. Measured on the real artifacts: 12 of the first 40 Elliptic
    bundles carried `fan_in` / `fan_out` while all 254 queue rows said nothing,
    so the dashboard's Pattern column was empty on every dataset and read as
    broken software. The serving layer now joins the two published artifacts.
    """

    @pytest.fixture()
    def client(self, tmp_path) -> TestClient:
        import pyarrow.parquet as pq

        store = GraphStore(tmp_path / "interim")
        store.write(
            "toy",
            "nodes",
            pl.DataFrame(
                {
                    "node_id": ["a", "b"],
                    "node_type": ["account"] * 2,
                    "domain": ["financial"] * 2,
                    "time_first_seen": [1, 1],
                    "raw_features": [[0.0], [1.0]],
                    "raw_attrs": [None, None],
                }
            ),
        )
        store.write(
            "toy",
            "edges",
            pl.DataFrame(
                {
                    "src": ["a"],
                    "dst": ["b"],
                    "edge_type": ["pays"],
                    "timestamp": [1],
                    "amount": [1.0],
                    "directed": [True],
                    "raw_attrs": [None],
                }
            ),
        )

        # BOTH rows carry a null motif, exactly as the real queues do.
        alerts = pl.DataFrame(
            [
                Alert(
                    alert_id=f"toy:run0:{r}",
                    domain=Domain.FINANCIAL,
                    dataset="toy",
                    model_run_id="run0",
                    rank=r,
                    risk_score=1.0 - r / 10,
                    member_node_ids=["a", "b"],
                    n_members=2,
                    motif_type=None,
                ).model_dump(mode="python")
                for r in (1, 2)
            ]
        )
        alerts_path = tmp_path / "alerts.parquet"
        pq.write_table(conform("alerts", alerts), alerts_path)

        bundles = tmp_path / "explanations"
        bundles.mkdir()
        # rank 1 was explained AND the matcher proved a shape — bundles.py
        # writes the name under "type", not "motif_type"
        (bundles / "toy_run0_1.json").write_text(
            json.dumps(
                {"alert_id": "toy:run0:1", "motif": {"type": "fan_in", "params": {}}},
            ),
            encoding="utf-8",
        )
        # rank 2 was explained and NOTHING was proved
        (bundles / "toy_run0_2.json").write_text(
            json.dumps({"alert_id": "toy:run0:2", "motif": None}), encoding="utf-8"
        )

        index = write_serving_index(
            tmp_path / "serving.json",
            {
                "toy": {
                    "domain": "financial",
                    "store_root": str(store.root),
                    "alerts": str(alerts_path),
                    "explanations": str(bundles),
                    "metrics": [],
                }
            },
        )
        return TestClient(create_app(index))

    def test_proven_motif_reaches_the_queue_row(self, client) -> None:
        rows = client.get("/api/v1/datasets/toy/alerts", params={"budget": 5}).json()["alerts"]
        by_id = {r["alert_id"]: r for r in rows}
        # THE BUG: this was None even though the bundle proved fan_in
        assert by_id["toy:run0:1"]["motif_type"] == "fan_in"
        assert by_id["toy:run0:1"]["explained"] is True

    def test_every_alert_is_pattern_checked_not_just_the_explained_ones(self, client) -> None:
        """No row may admit "not checked".

        Naming a shape needs only the rule matcher, not the expensive learned
        explainer, so it runs on the whole queue. Before this, the check rode
        along with the written case file and 203 of 223 Mendeley rows said "not
        checked" — an indefensible thing to put in front of a reviewer.
        """
        rows = client.get("/api/v1/datasets/toy/alerts", params={"budget": 50}).json()["alerts"]
        assert rows, "fixture produced no alerts"
        assert all(r["pattern_checked"] for r in rows)

    def test_explained_with_no_proven_shape_stays_null(self, client) -> None:
        """Absence must not be invented into a pattern name."""
        rows = client.get("/api/v1/datasets/toy/alerts", params={"budget": 5}).json()["alerts"]
        row = next(r for r in rows if r["alert_id"] == "toy:run0:2")
        assert row["motif_type"] is None
        assert row["explained"] is True  # checked, and nothing was proved


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

    def test_queue_reports_which_alerts_were_explained(self, client) -> None:
        """`explained` separates "checked, nothing proved" from "never checked".

        Only the head of the queue gets a bundle, and collapsing both cases into
        one blank cell is what made the dashboard's Pattern column look broken.
        """
        rows = client.get("/api/v1/datasets/toyapi/alerts", params={"budget": 5}).json()["alerts"]
        by_id = {r["alert_id"]: r for r in rows}
        assert by_id["toyapi:run0:1"]["explained"] is True  # has a bundle
        assert by_id["toyapi:run0:2"]["explained"] is False  # no bundle written

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


class TestStressTest:
    """The /stress-test endpoint (§7 step 30): serves the injection-recovery
    study read-only, omits absent artifacts, 404s on a thin machine."""

    def _index(self, tmp_path, with_study: bool, artifact_exists: bool = True):
        recovery = tmp_path / "injection.json"
        if artifact_exists:
            recovery.write_text(
                json.dumps({"population": 163327, "recovery": {"gae": []}}),
                encoding="utf-8",
            )
        datasets = {"toyapi": {"domain": "financial", "store_root": str(tmp_path / "s")}}
        stress = (
            {
                "ocds_georgia": {
                    "title": "Georgia — no answer key",
                    "recovery": str(recovery),
                    "reproduce": "uv run collusiongraph train -c ...",
                    "note": "plant and measure",
                }
            }
            if with_study
            else None
        )
        return write_serving_index(tmp_path / "serving.json", datasets, stress_test=stress)

    def test_study_served_with_payload_and_caveat(self, tmp_path) -> None:
        client = TestClient(create_app(self._index(tmp_path, with_study=True)))
        r = client.get("/api/v1/stress-test")
        assert r.status_code == 200
        body = r.json()
        assert body["caveat"] == SCREENING_CAVEAT
        study = body["studies"]["ocds_georgia"]
        assert study["title"] == "Georgia — no answer key"
        assert study["reproduce"].startswith("uv run")
        assert study["payload"]["population"] == 163327

    def test_404_when_no_study_published(self, tmp_path) -> None:
        client = TestClient(create_app(self._index(tmp_path, with_study=False)))
        assert client.get("/api/v1/stress-test").status_code == 404

    def test_absent_artifact_is_omitted_not_faked(self, tmp_path) -> None:
        # a study is declared but its file was never produced on this machine
        client = TestClient(
            create_app(self._index(tmp_path, with_study=True, artifact_exists=False))
        )
        assert client.get("/api/v1/stress-test").status_code == 404


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
