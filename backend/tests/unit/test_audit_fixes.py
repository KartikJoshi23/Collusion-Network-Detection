"""Regression tests for the deep-audit fixes (F1–F29) not covered by updates
to existing suites: as-of training labels, frozen normalization, fence
semantics, projection guards, embedded-chain matching, red-flag dedupe,
store-name sanitization, artifact size cap, attention summaries, fidelity
sanity, CLI dispatch, and the W&B logging path."""

import json

import numpy as np
import polars as pl
import pytest
import torch
from collusiongraph.adapters.procurement import mendeley_firm_labels_as_of
from collusiongraph.artifacts import build_alerts
from collusiongraph.cli import select_train_runner
from collusiongraph.explain import build_bundle, match_financial
from collusiongraph.explain.explainer_runner import attention_summaries
from collusiongraph.explain.redflags import map_red_flags
from collusiongraph.features import apply_zscore, fit_zscore
from collusiongraph.injection.generators.financial import GENERATORS as FIN
from collusiongraph.models import make_model
from collusiongraph.schema import GraphStore, SchemaError
from collusiongraph.splits import strict_temporal_split
from collusiongraph.training.labels import resolve_train_labels


class TestAsOfLabels:  # F1
    def awards(self) -> pl.DataFrame:
        attrs_clean = json.dumps({"is_cartel": 0})
        attrs_cartel = json.dumps({"is_cartel": 1})
        return pl.DataFrame(
            {
                "src": ["tender:M:T1", "tender:M:T2", "tender:M:T3"],
                "dst": ["firm:M:F1", "firm:M:F1", "firm:M:F2"],
                "edge_type": ["awarded"] * 3,
                # F1's cartel award happens AFTER 2013; F2 is cartel by 2010
                "timestamp": [2010, 2018, 2010],
                "amount": pl.Series([None] * 3, dtype=pl.Float64),
                "directed": [True] * 3,
                "raw_attrs": [attrs_clean, attrs_cartel, attrs_cartel],
            }
        )

    def test_future_cartel_activity_does_not_leak_into_train_labels(self) -> None:
        as_of = dict(
            mendeley_firm_labels_as_of(self.awards(), 2013).select("node_id", "label").iter_rows()
        )
        assert as_of["firm:M:F1"] == "licit"  # cartel award is post-2013: unknowable
        assert as_of["firm:M:F2"] == "illicit"
        full = dict(
            mendeley_firm_labels_as_of(self.awards(), 2020).select("node_id", "label").iter_rows()
        )
        assert full["firm:M:F1"] == "illicit"  # knowable once it happened

    def test_firms_without_awards_by_as_of_are_absent(self) -> None:
        labels = mendeley_firm_labels_as_of(self.awards(), 2005)
        assert labels.is_empty()

    def test_policy_resolver(self) -> None:
        stored = pl.DataFrame(
            {
                "node_id": ["firm:M:F1"],
                "label": ["illicit"],
                "label_source": ["s"],
                "confidence": [1.0],
            }
        )
        assert resolve_train_labels("static", stored, self.awards(), 2013).equals(stored)
        as_of = resolve_train_labels("mendeley_as_of", stored, self.awards(), 2013)
        assert dict(as_of.select("node_id", "label").iter_rows())["firm:M:F1"] == "licit"
        with pytest.raises(ValueError, match="unknown train_label_policy"):
            resolve_train_labels("nope", stored, self.awards(), 2013)


class TestFrozenZscore:  # F3
    def test_fit_on_train_apply_to_inference(self) -> None:
        train = pl.DataFrame({"node_id": ["a", "b"], "x": [0.0, 10.0]})
        infer = pl.DataFrame({"node_id": ["c"], "x": [20.0]})
        stats = fit_zscore(train)
        out = apply_zscore(infer, stats)
        # normalized with TRAIN mean/std (5, 7.07), not its own stats
        assert out["x"][0] == pytest.approx((20.0 - 5.0) / np.sqrt(50.0))

    def test_zero_variance_and_missing_columns(self) -> None:
        train = pl.DataFrame({"node_id": ["a", "b"], "x": [3.0, 3.0]})
        stats = fit_zscore(train)
        assert apply_zscore(train, stats)["x"].to_list() == [0.0, 0.0]
        with pytest.raises(ValueError, match="missing from features"):
            apply_zscore(pl.DataFrame({"node_id": ["a"]}), stats)


class TestFenceKeepsUnplacedNodes:  # F6
    def test_null_time_nodes_survive_the_fence_and_count_as_unplaced(self) -> None:
        nodes = pl.DataFrame(
            {"node_id": ["a", "b", "late", "u"], "time_first_seen": [1, 2, 99, None]}
        )
        edges = pl.DataFrame({"src": ["a", "b"], "dst": ["b", "late"], "timestamp": [1, 99]})
        split = strict_temporal_split(nodes, edges, train_end=1, fence_after=10)
        assert split.report["n_fenced_nodes"] == 1  # only the post-window node
        assert split.report["n_unplaced_nodes"] == 1  # u, honestly attributed


class TestEmbeddedPassThrough:  # F8
    def test_bridged_chain_still_matches(self) -> None:
        rng = np.random.default_rng(3)
        _, edges, members = FIN["pass_through"]("t", rng, 10, 20)
        # embed the chain: unrelated inflow into the head, plus a random
        # outgoing bridge from a middle member — the old matcher went blind
        head_ts = int(edges.sort("timestamp")["timestamp"][0])
        noise = pl.DataFrame(
            {
                "src": ["bg:feeder", members[2]],
                "dst": [members[0], "bg:sink"],
                "edge_type": ["pays", "pays"],
                "timestamp": [head_ts - 4, head_ts + 1],
                "amount": [123.0, 55.0],
                "directed": [True, True],
                "raw_attrs": pl.Series([None, None], dtype=pl.Utf8),
            }
        )
        matches = match_financial(pl.concat([edges, noise], how="diagonal_relaxed"))
        chains = [m for m in matches if m.motif_type == "pass_through"]
        assert any(set(members) <= set(m.member_node_ids) for m in chains)


class TestRedFlagDedupe:  # F9
    def test_many_instances_one_citation_with_count(self) -> None:
        rng = np.random.default_rng(0)
        _, e1, _ = FIN["fan_in"]("a", rng, 10, 20)
        _, e2, _ = FIN["fan_in"]("b", rng, 10, 20)
        matches = match_financial(pl.concat([e1, e2]))
        flags = map_red_flags(matches, "financial")
        struct_flags = [f for f in flags if f["indicator_id"] == "FATF-STRUCT-01"]
        assert len(struct_flags) == 1
        assert "+1 more instances" in struct_flags[0]["matched_because"]


class TestStoreNameSanitization:  # F14
    def test_hostile_pack_names_rejected(self, tmp_path) -> None:
        store = GraphStore(tmp_path)
        frame = pl.DataFrame({"node_id": ["a"], "x": [1.0]})
        for bad in ("../escape", "a b", "x;DROP", ""):
            with pytest.raises(SchemaError, match="invalid pack name"):
                store.write_features("ds", bad, frame)
        with pytest.raises(SchemaError, match="invalid pack name"):
            store.read_features("ds", "../escape")


class TestAlertArtifactCap:  # F11 + F29
    def test_mega_communities_never_enter_the_artifact(self) -> None:
        nodes = pl.DataFrame(
            {"node_id": [f"n{i}" for i in range(120)], "time_first_seen": [1] * 120}
        )
        scored = pl.DataFrame(
            {
                "community_id": ["mega", "ok_b", "ok_a"],
                "member_node_ids": [
                    [f"n{i}" for i in range(110)],
                    ["n1", "n2"],
                    ["n3", "n4"],
                ],
                "method": ["leiden"] * 3,
                "score": [0.99, 0.5, 0.5],  # tie between the two small ones
            }
        )
        alerts = build_alerts(scored, nodes, "toy", "financial", "r0", max_members=100)
        assert alerts.height == 2
        assert alerts["n_members"].max() <= 100
        # F29: score ties break deterministically by community_id
        assert alerts.sort("rank")["community_id"].to_list() == ["ok_a", "ok_b"]


class TestAttentionAndFidelity:  # F13 + F15
    def _data(self):
        from collusiongraph.training import build_graph

        ids = [f"n{i}" for i in range(12)]
        nodes = pl.DataFrame({"node_id": ids, "time_first_seen": [1] * 12})
        edges = pl.DataFrame(
            {
                "src": ids[:-1],
                "dst": ids[1:],
                "edge_type": ["pays"] * 11,
                "timestamp": [1] * 11,
                "directed": [True] * 11,
            }
        )
        labels = pl.DataFrame({"node_id": ids, "label": ["licit"] * 12})
        rng = np.random.default_rng(0)
        features = pl.DataFrame({"node_id": ids}).with_columns(
            [pl.Series(f"f{j}", rng.normal(size=12)) for j in range(4)]
        )
        return build_graph(nodes, edges, labels, features)

    def test_attention_summary_populated_for_gatv2(self) -> None:
        torch.manual_seed(0)
        data = self._data()
        model = make_model("gatv2", in_dim=4, hidden_dim=8, heads=2, dropout=0.0)
        out = attention_summaries(model, data, ["n5", "ghost"])
        assert "n5" in out and "ghost" not in out
        summary = out["n5"]
        assert 0.0 <= summary["mean_incoming_attention"] <= 1.0
        assert summary["n_heads"] == 2.0

    def test_fidelity_sanity_recorded_on_bundle(self) -> None:
        from collusiongraph.explain.explainer_runner import NodeExplanation

        alert = {
            "alert_id": "t:1",
            "rank": 1,
            "risk_score": 0.5,
            "member_node_ids": ["a", "b"],
            "n_members": 2,
            "time_window_start": 1,
            "time_window_end": 2,
        }
        nodes = pl.DataFrame({"node_id": ["a", "b"], "time_first_seen": [1, 2]})
        edges = pl.DataFrame(
            {
                "src": ["a"],
                "dst": ["b"],
                "edge_type": ["pays"],
                "timestamp": [1],
                "amount": [10.0],
                "directed": [True],
            }
        )
        insane = NodeExplanation("a", ["a", "b"], [("a", "b")], 0.1, 0.9)
        bundle = build_bundle(alert, "financial", "toy", edges, nodes, insane, 1)
        assert bundle.fidelity_sane is False
        sane = NodeExplanation("a", ["a", "b"], [("a", "b")], 0.9, 0.1)
        bundle = build_bundle(alert, "financial", "toy", edges, nodes, sane, 1)
        assert bundle.fidelity_sane is True


class TestCliDispatch:  # F22
    def test_train_config_shapes_route_correctly(self) -> None:
        assert select_train_runner({"baselines": ["b1_rules"]}) == "baselines"
        assert select_train_runner({"motifs": {"cycle": 5}}) == "injection_recovery"
        assert select_train_runner({"supervised_scores_dir": "x"}) == "ensemble"
        assert select_train_runner({"model": {"name": "gatv2"}}) == "gnn"


class TestWandbPath:  # F21
    def test_metrics_flattened_and_logged(self, monkeypatch, tmp_path) -> None:
        import sys as _sys
        import types

        from collusiongraph.eval.report import _maybe_log_wandb

        calls: dict = {}

        def fake_init(**kwargs):
            calls["init"] = kwargs
            run = types.SimpleNamespace(
                log=lambda payload: calls.setdefault("log", payload),
                finish=lambda: calls.setdefault("finished", True),
            )
            return run

        monkeypatch.setitem(_sys.modules, "wandb", types.SimpleNamespace(init=fake_init))
        metrics = {
            "dataset": "toy",
            "alert_level": {"queue": {"@2": {"precision": 0.5}}},
            "node_level": {"auc_pr": 0.9},
        }
        _maybe_log_wandb(metrics, {"wandb": {"enabled": True, "project": "p"}})
        assert calls["init"]["project"] == "p"
        assert calls["log"]["alert/@2/precision"] == 0.5
        assert calls["log"]["node/auc_pr"] == 0.9
        assert calls["finished"]
