"""Transfer-probe tests (§7 steps 20–21): wiring + leakage discipline on tiny
fixtures. Model quality on real data is the run's job, not the tests'."""

import typing

import numpy as np
import polars as pl
import pytest
from collusiongraph.schema import GraphStore
from collusiongraph.training import run_cross_domain_probe, run_loco_matrix, run_loco_transfer
from collusiongraph.training.transfer_run import _pick_val_group

RNG = np.random.default_rng(11)


def procurement_store(tmp_path) -> GraphStore:
    """Three countries, firm/tender graphs with awarded edges; every country
    carries both classes so any val_group choice is viable."""
    store = GraphStore(tmp_path / "interim")
    rows, edges, labels = [], [], []
    for c in ("c1", "c2", "c3"):
        for i in range(8):
            bad = i % 4 == 0
            firm, tender = f"firm:{c}:F{i}", f"tender:{c}:T{i}"
            year = 2010 + (i % 3)
            rows += [
                {
                    "node_id": firm,
                    "node_type": "firm",
                    "domain": "procurement",
                    "time_first_seen": year,
                    "raw_features": None,
                    "raw_attrs": None,
                },
                {
                    "node_id": tender,
                    "node_type": "tender",
                    "domain": "procurement",
                    "time_first_seen": year,
                    "raw_features": None,
                    "raw_attrs": None,
                },
            ]
            edges.append(
                {
                    "src": tender,
                    "dst": firm,
                    "edge_type": "awarded",
                    "timestamp": year,
                    "amount": None,
                    "directed": True,
                    "raw_attrs": None,
                }
            )
            # collusive firms co-award with their neighbor (a detectable pattern)
            if bad and i > 0:
                edges.append(
                    {
                        "src": tender,
                        "dst": f"firm:{c}:F{i - 1}",
                        "edge_type": "awarded",
                        "timestamp": year,
                        "amount": None,
                        "directed": True,
                        "raw_attrs": None,
                    }
                )
            labels.append(
                {
                    "node_id": firm,
                    "label": "illicit" if bad else "licit",
                    "label_source": "toy",
                    "confidence": 1.0,
                }
            )
    store.write("toyproc", "nodes", pl.DataFrame(rows))
    store.write("toyproc", "edges", pl.DataFrame(edges))
    store.write("toyproc", "labels", pl.DataFrame(labels))
    store.write_meta("toyproc", {"dataset": "toyproc", "time_unit": "year", "n_features": 0})
    return store


class TestLocoTransfer:
    def test_end_to_end_and_test_country_isolation(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        record = run_loco_transfer(
            {
                "dataset": "toyproc",
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "loco"),
                "seed": 0,
                "node_type": "firm",
                "test_group": "c3",
                "val_group": "c2",
                "model": {"name": "rgcn", "hidden_dim": 8, "dropout": 0.0},
                "epochs": 5,
                "patience": 5,
                "budgets": [4],
            }
        )
        assert record["test_group"] == "c3"
        assert record["fold"]["n_cross_group_edges_excluded"] == 0
        scores = pl.read_parquet(tmp_path / "loco" / "scores_test.parquet")
        assert scores.height > 0
        assert all(nid.startswith("firm:c3:") for nid in scores["node_id"].to_list())
        assert record["node_level"]["auc_pr"] >= 0.0

    def test_val_group_must_differ_from_test_group(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        with pytest.raises(ValueError, match="must differ"):
            run_loco_transfer(
                {
                    "dataset": "toyproc",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "x"),
                    "node_type": "firm",
                    "test_group": "c3",
                    "val_group": "c3",
                    "budgets": [4],
                }
            )


class TestLocoMatrix:  # §7 step 28
    # measured mendeley_eu firm label counts (n_labeled, n_illicit, n_licit),
    # 2026-07-19 — the policy fixture that pins the published pairing
    MENDELEY_STATS: typing.ClassVar[dict[str, tuple[int, int, int]]] = {
        "country_1": (30, 23, 7),
        "country_2": (750, 537, 213),
        "country_3": (63, 18, 45),
        "country_4": (76, 55, 21),
        "country_5": (60, 40, 20),
        "country_6": (9, 8, 1),
        "country_7": (13, 9, 4),
    }

    def test_val_policy_reproduces_published_pairing(self) -> None:
        # the published country_5 fold used country_7 as val — the policy's output
        assert _pick_val_group("country_5", self.MENDELEY_STATS, 3, {}) == "country_7"
        # country_6 (1 licit) is below the per-class floor — never picked for val
        assert _pick_val_group("country_7", self.MENDELEY_STATS, 3, {}) == "country_1"
        # explicit overrides win
        assert (
            _pick_val_group("country_5", self.MENDELEY_STATS, 3, {"country_5": "country_2"})
            == "country_2"
        )
        with pytest.raises(ValueError, match="viable validation group"):
            _pick_val_group("country_5", self.MENDELEY_STATS, 600, {})

    def test_matrix_end_to_end_aggregation_and_outputs(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        matrix = run_loco_matrix(
            {
                "dataset": "toyproc",
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "matrix"),
                "loco_matrix": True,
                "seeds": [0, 1],
                "node_type": "firm",
                "min_val_per_class": 2,  # toy groups carry 2 illicit / 6 licit each
                "model": {"name": "rgcn", "hidden_dim": 8, "dropout": 0.0},
                "epochs": 5,
                "patience": 5,
                "budgets": [4],
            }
        )
        assert matrix["summary"]["n_folds"] == 3
        assert matrix["summary"]["n_completed"] == 3
        for fold in matrix["folds"]:
            assert fold["status"] == "completed"
            assert fold["val_group"] != fold["test_group"]
            assert len(fold["auc_pr_per_seed"]) == 2
            assert fold["auc_pr_mean"] == pytest.approx(float(np.mean(fold["auc_pr_per_seed"])))
        # deterministic val picks: equal group sizes tie-break lexicographically
        picks = {f["test_group"]: f["val_group"] for f in matrix["folds"]}
        assert picks == {"c1": "c2", "c2": "c1", "c3": "c1"}
        assert (tmp_path / "matrix" / "matrix.json").exists()
        assert (tmp_path / "matrix" / "fold_c1_s0" / "run.json").exists()
        assert (tmp_path / "matrix" / "fold_c3_s1" / "scores_test.parquet").exists()

    def test_matrix_skips_unviable_folds_with_reason(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        matrix = run_loco_matrix(
            {
                "dataset": "toyproc",
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "matrix_skip"),
                "loco_matrix": True,
                "node_type": "firm",
                "min_val_per_class": 5,  # no toy group has 5 illicit — nothing viable
                "model": {"name": "rgcn", "hidden_dim": 8, "dropout": 0.0},
                "epochs": 2,
                "patience": 2,
                "budgets": [4],
            }
        )
        assert matrix["summary"]["n_completed"] == 0
        assert matrix["summary"]["macro_auc_pr_mean"] is None
        for fold in matrix["folds"]:
            assert fold["status"] == "skipped"
            assert "viable validation group" in fold["reason"]

    def test_test_groups_subset_limits_folds_not_val_candidates(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        base = {
            "dataset": "toyproc",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "matrix_sub"),
            "loco_matrix": True,
            "node_type": "firm",
            "min_val_per_class": 2,
            "model": {"name": "rgcn", "hidden_dim": 8, "dropout": 0.0},
            "epochs": 2,
            "patience": 2,
            "budgets": [4],
        }
        matrix = run_loco_matrix({**base, "test_groups": ["c2"]})
        assert [f["test_group"] for f in matrix["folds"]] == ["c2"]
        # val candidates come from ALL groups — chunking must not change picks
        assert matrix["folds"][0]["val_group"] == "c1"
        with pytest.raises(ValueError, match="not in the dataset's labeled groups"):
            run_loco_matrix({**base, "test_groups": ["nope"]})

    def test_cli_dispatch_routes_matrix_configs(self) -> None:
        from collusiongraph.cli import select_train_runner

        assert select_train_runner({"loco_matrix": True, "dataset": "d"}) == "loco_matrix"
        # single-fold configs keep their route
        assert select_train_runner({"test_group": "c1", "dataset": "d"}) == "loco_transfer"


def financial_store(tmp_path) -> GraphStore:
    """Two-era financial account graph (source AND target for the probe)."""
    store = GraphStore(tmp_path / "interim")
    rows, edges, labels = [], [], []
    bad_ids = {0, 2, 4, 8, 10}
    for i in range(16):
        bad = i in bad_ids
        t = 1 + (i % 3) if i < 10 else 5
        rows.append(
            {
                "node_id": f"acct:n{i}",
                "node_type": "account",
                "domain": "financial",
                "time_first_seen": t,
                "raw_features": None,
                "raw_attrs": None,
            }
        )
        labels.append(
            {
                "node_id": f"acct:n{i}",
                "label": "illicit" if bad else "licit",
                "label_source": "toy",
                "confidence": 1.0,
            }
        )
    for i in range(15):
        edges.append(
            {
                "src": f"acct:n{i}",
                "dst": f"acct:n{i + 1}",
                "edge_type": "pays",
                "timestamp": 1 + (i % 3) if i < 9 else 5,
                "amount": 50.0,
                "directed": True,
                "raw_attrs": None,
            }
        )
    # fan-in onto each bad node — structural signal the probe can carry over
    for b in sorted(bad_ids):
        for j in range(2):
            src = f"acct:n{(b + 5 + j) % 16}"
            edges.append(
                {
                    "src": src,
                    "dst": f"acct:n{b}",
                    "edge_type": "pays",
                    "timestamp": 2 if b < 10 else 5,
                    "amount": 9.0,
                    "directed": True,
                    "raw_attrs": None,
                }
            )
    store.write("toysrc", "nodes", pl.DataFrame(rows))
    store.write("toysrc", "edges", pl.DataFrame(edges))
    store.write("toysrc", "labels", pl.DataFrame(labels))
    store.write_meta("toysrc", {"dataset": "toysrc", "time_unit": "step", "n_features": 0})
    return store


class TestCrossDomainProbe:
    def test_probe_end_to_end(self, tmp_path) -> None:
        store = financial_store(tmp_path)
        record = run_cross_domain_probe(
            {
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "probe"),
                "seed": 0,
                "budgets": [4],
                "source": {
                    "dataset": "toysrc",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "src_run"),
                    "seed": 0,
                    "features": "structural",
                    "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
                    "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
                    "epochs": 5,
                    "patience": 5,
                    "budgets": [4],
                },
                "target": {
                    "dataset": "toysrc",
                    "split": {"train_end": 3, "test_start": 5},
                },
            }
        )
        assert record["kind"] == "cross_domain_probe"
        assert record["n_probe_train"] > 0 and record["n_probe_test"] > 0
        assert 0.0 <= record["node_level"]["auc_pr"] <= 1.0
        scores = pl.read_parquet(tmp_path / "probe" / "scores_test.parquet")
        assert ((scores["score"] >= 0.0) & (scores["score"] <= 1.0)).all()

    def test_probe_rejects_non_structural_source(self, tmp_path) -> None:
        store = financial_store(tmp_path)
        with pytest.raises(ValueError, match="structural channel"):
            run_cross_domain_probe(
                {
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "p2"),
                    "budgets": [4],
                    "source": {"dataset": "toysrc", "features": "raw"},
                    "target": {"dataset": "toysrc", "split": {"train_end": 3}},
                }
            )
