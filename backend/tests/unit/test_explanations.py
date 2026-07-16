"""Explanation-layer correctness (§7 steps 17–19, §9.1).

The flagship is the injection-recovery cross-validation: the motif matcher
must recover EVERY injected motif family with 100% recall on fixtures —
matcher and injector are independent implementations, so this validates both.
Plus: matcher negative controls, explainer invariants on GATv2/R-GCN
fixtures, and bundle-schema invariants (caveat lock, resolvable red flags,
evidence adaptation).
"""

import numpy as np
import polars as pl
import pytest
import torch
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.explain import (
    ExplanationBundle,
    build_bundle,
    explain_nodes,
    load_indicators,
    map_red_flags,
    match_financial,
    match_motifs,
    match_procurement,
    run_explanations,
)
from collusiongraph.injection.generators.financial import GENERATORS as FIN
from collusiongraph.injection.generators.procurement import GENERATORS as PROC
from collusiongraph.models import make_model
from collusiongraph.schema import GraphStore

# injector name -> matcher vocabulary (§4.4 MotifType)
ALIAS = {"coordinated_cluster": "clique"}


class TestMatcherRecoversInjector:
    """§9.1: 100% recall over all ten generator families."""

    @pytest.mark.parametrize("motif", sorted(FIN))
    def test_financial_family_recovered(self, motif: str) -> None:
        rng = np.random.default_rng(7)
        _, edges, members = FIN[motif]("t", rng, 10, 20)
        expected = ALIAS.get(motif, motif)
        matches = match_financial(edges)
        hits = [m for m in matches if m.motif_type == expected]
        assert hits, f"{motif}: no {expected} match found"
        assert any(
            set(members) <= set(m.member_node_ids) for m in hits
        ), f"{motif}: injected members not covered by any match"

    @pytest.mark.parametrize("motif", sorted(PROC))
    def test_procurement_family_recovered(self, motif: str) -> None:
        rng = np.random.default_rng(7)
        _, edges, members = PROC[motif]("t", rng, 2014, 2021)
        expected = ALIAS.get(motif, motif)
        matches = match_procurement(edges)
        hits = [m for m in matches if m.motif_type == expected]
        assert hits, f"{motif}: no {expected} match found"
        # a hit must stay inside the injected instance and cover its firm core
        injected = set(members)
        firms = {n for n in members if n.startswith("firm:")}
        assert any(
            set(m.member_node_ids) <= injected and firms <= set(m.member_node_ids) for m in hits
        ), f"{motif}: no in-instance match covers the injected firms"

    def test_quiet_financial_graph_yields_no_matches(self) -> None:
        """Negative control: an innocuous chain must not trigger anything."""
        rng = np.random.default_rng(0)
        ids = [f"a{i}" for i in range(10)]
        edges = pl.DataFrame(
            {
                "src": ids[:-1],
                "dst": ids[1:],
                "edge_type": ["pays"] * 9,
                "timestamp": [i * 5 for i in range(9)],  # slow hops
                "amount": rng.uniform(100, 10_000, size=9),  # no retention pattern
                "directed": [True] * 9,
            }
        )
        assert match_financial(edges) == []

    def test_competitive_bidding_yields_no_matches(self) -> None:
        """Negative control: widely spread bids, one-off winners."""
        edges = pl.DataFrame(
            {
                "src": ["firm:M:A", "firm:M:B", "firm:M:C", "tender:M:T0"],
                "dst": ["tender:M:T0"] * 3 + ["firm:M:A"],
                "edge_type": ["bids_on"] * 3 + ["awarded"],
                "timestamp": [2015] * 4,
                "amount": [100.0, 150.0, 220.0, 100.0],  # spread far apart
                "directed": [True] * 4,
            }
        )
        assert match_procurement(edges) == []

    def test_unknown_domain_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown domain"):
            match_motifs(pl.DataFrame(), "energy")


class TestRedFlags:
    def test_every_motif_type_has_an_indicator(self) -> None:
        """Vocabulary completeness: each motif the matcher can emit maps to at
        least one curated indicator in its domain."""
        financial_motifs = {"cycle", "fan_in", "fan_out", "pass_through", "common_control"}
        procurement_motifs = {"rotation", "cover_bid", "partition", "clique", "common_control"}
        for domain, motifs in [
            ("financial", financial_motifs),
            ("procurement", procurement_motifs),
        ]:
            covered = {m for ind in load_indicators(domain)["indicators"] for m in ind["motifs"]}
            assert motifs <= covered, f"{domain}: unmapped motifs {motifs - covered}"

    def test_mapping_produces_resolvable_citations(self) -> None:
        rng = np.random.default_rng(0)
        _, edges, _ = FIN["fan_in"]("t", rng, 10, 20)
        flags = map_red_flags(match_financial(edges), "financial")
        assert flags
        assert all(
            f["framework"] == "FATF" and f["indicator_id"].startswith("FATF-") for f in flags
        )
        assert any("fan_in" in f["matched_because"] for f in flags)


def tiny_graph_data():
    """Small directed chain graph as PyG data via build_graph."""
    from collusiongraph.training import build_graph

    ids = [f"n{i}" for i in range(20)]
    nodes = pl.DataFrame({"node_id": ids, "time_first_seen": [1] * 20})
    edges = pl.DataFrame(
        {
            "src": ids[:-1],
            "dst": ids[1:],
            "edge_type": ["pays"] * 19,
            "timestamp": [1] * 19,
            "directed": [True] * 19,
        }
    )
    labels = pl.DataFrame({"node_id": ids, "label": ["licit"] * 10 + ["illicit"] * 10})
    rng = np.random.default_rng(0)
    features = pl.DataFrame({"node_id": ids}).with_columns(
        [pl.Series(f"f{j}", rng.normal(size=20)) for j in range(4)]
    )
    return build_graph(nodes, edges, labels, features)


class TestExplainerRunner:
    def test_explanation_invariants(self) -> None:
        torch.manual_seed(0)
        data = tiny_graph_data()
        model = make_model("gatv2", in_dim=4, hidden_dim=8, num_layers=2, heads=2, dropout=0.0)
        out = explain_nodes(model, data, ["n5"], num_hops=2, epochs=20, top_edges=5)
        exp = out["n5"]
        assert set(exp.subgraph_node_ids) <= set(data.node_ids)  # subgraph ⊆ graph
        assert exp.subgraph_node_ids  # non-empty (§9.1)
        assert all(s in data.node_ids and d in data.node_ids for s, d in exp.subgraph_edges)
        assert isinstance(exp.fidelity_plus, float) and isinstance(exp.fidelity_minus, float)

    @pytest.mark.parametrize("name", ["graphsage", "rgcn"])
    def test_sliced_edge_models_are_rejected(self, name: str) -> None:
        """R12 de-risk, documented: SAGE slices edges by direction and RGCNConv
        propagates per relation — mask-based explanation cannot align; R-GCN
        needs HeteroExplanation over true HeteroData (ledger follow-up)."""
        data = tiny_graph_data()
        model = make_model(name, in_dim=4, num_relations=2, hidden_dim=8, dropout=0.0)
        with pytest.raises(TypeError, match="GATv2 only"):
            explain_nodes(model, data, ["n5"])

    def test_missing_nodes_are_skipped(self) -> None:
        torch.manual_seed(0)
        data = tiny_graph_data()
        model = make_model("gatv2", in_dim=4, hidden_dim=8, heads=2, dropout=0.0)
        out = explain_nodes(model, data, ["ghost"], epochs=5)
        assert out == {}


def fan_in_alert_fixture():
    rng = np.random.default_rng(0)
    nodes_f, edges_f, members = FIN["fan_in"]("t", rng, 10, 20)
    alert = {
        "alert_id": "toy:run:1",
        "rank": 1,
        "risk_score": 0.9,
        "member_node_ids": members,
        "n_members": len(members),
        "time_window_start": 10,
        "time_window_end": 20,
    }
    return alert, nodes_f, edges_f


class TestBundles:
    def test_bundle_carries_motif_flags_and_locked_caveat(self) -> None:
        alert, nodes, edges = fan_in_alert_fixture()
        bundle = build_bundle(alert, "financial", "toy", edges, nodes, None, budget_position=1)
        assert bundle.motif and bundle.motif["type"] == "fan_in"
        assert any(f["indicator_id"] == "FATF-STRUCT-01" for f in bundle.red_flags)
        assert bundle.caveats == SCREENING_CAVEAT
        assert set(bundle.minimal_subgraph.nodes) <= set(alert["member_node_ids"])
        # amount evidence present: the generator writes amounts (unlike Elliptic)
        assert "amount_total" in bundle.evidence

    def test_weakened_caveat_is_unconstructable(self) -> None:
        alert, nodes, edges = fan_in_alert_fixture()
        bundle = build_bundle(alert, "financial", "toy", edges, nodes, None, budget_position=1)
        with pytest.raises(ValueError, match="fixed"):
            ExplanationBundle(**{**bundle.model_dump(), "caveats": "may indicate guilt"})

    def test_amountless_evidence_adapts(self) -> None:
        """D1: Elliptic-style graphs carry no amounts — the bundle leads with
        structural/temporal evidence and never fabricates amount fields."""
        alert, nodes, edges = fan_in_alert_fixture()
        edges = edges.with_columns(pl.lit(None, dtype=pl.Float64).alias("amount"))
        bundle = build_bundle(alert, "financial", "toy", edges, nodes, None, budget_position=1)
        assert "amount_total" not in bundle.evidence
        assert bundle.evidence["time_window"] == [10, 20]

    def test_run_explanations_writes_validated_bundles(self, tmp_path) -> None:
        alert, nodes, edges = fan_in_alert_fixture()
        store = GraphStore(tmp_path / "interim")
        store.write("toy", "nodes", nodes)
        store.write("toy", "edges", edges)
        store.write(
            "toy",
            "labels",
            pl.DataFrame(
                {
                    "node_id": alert["member_node_ids"],
                    "label": ["unknown"] * alert["n_members"],
                    "label_source": ["toy"] * alert["n_members"],
                    "confidence": [1.0] * alert["n_members"],
                }
            ),
        )
        store.write_meta("toy", {"dataset": "toy", "n_features": 0})
        alerts = pl.DataFrame(
            {
                "alert_id": [alert["alert_id"]],
                "rank": [1],
                "risk_score": [0.9],
                "member_node_ids": [alert["member_node_ids"]],
                "n_members": [alert["n_members"]],
                "time_window_start": [10],
                "time_window_end": [20],
            }
        )
        alerts_path = tmp_path / "alerts.parquet"
        alerts.write_parquet(alerts_path)
        summary = run_explanations(
            {
                "dataset": "toy",
                "domain": "financial",
                "store_root": str(store.root),
                "alerts": str(alerts_path),
                "output_dir": str(tmp_path / "bundles"),
                "top_k": 5,
            }
        )
        assert summary["n_bundles"] == 1
        assert summary["n_with_motif"] == 1
        assert summary["n_with_red_flags"] == 1
        files = list((tmp_path / "bundles").glob("toy_run_1.json"))
        assert len(files) == 1
