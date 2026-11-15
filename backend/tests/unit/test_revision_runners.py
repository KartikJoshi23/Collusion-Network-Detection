"""Tests for the journal-revision runners (revision-plan.md, Part B).

Covered: the local feature set (B3), per-step baseline metrics (B1), the
baseline multi-seed wrapper (B2), the config-driven paired bootstrap (B2,
Table III), the supervised calibrated fusion (B2), the below-chance
diagnostics (B4), the pooled transfer summary (B5), derived numbers, and
the CLI dispatch. Tiny hand-built stores; wiring and arithmetic, not model
quality.
"""

import json
from itertools import pairwise
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from collusiongraph.cli import select_train_runner
from collusiongraph.eval.derived import compute_item, wilson_interval
from collusiongraph.eval.diagnostics import (
    distribution_shift,
    run_below_chance_diagnostics,
    score_checks,
)
from collusiongraph.eval.significance import compare_score_files, run_significance
from collusiongraph.eval.transfer_summary import summarise_matrix
from collusiongraph.schema import GraphStore
from collusiongraph.training.baseline_run import assemble_features, run_baselines
from collusiongraph.training.fusion_run import run_supervised_fusion

FEATURE_NAMES = [
    "Time step",
    "Local_feature_1",
    "Local_feature_2",
    "Aggregate_feature_1",
    "in_txs_degree",
]


def toy_financial_store(tmp_path: Path) -> GraphStore:
    """Six time steps; illicit nodes have high Local_feature_1. Edges chain
    nodes within a step (like Elliptic, no cross-step edges)."""
    rng = np.random.default_rng(1)
    store = GraphStore(tmp_path / "interim")
    rows, label_rows = [], []
    for t in range(1, 7):
        for i in range(10):
            bad = i < 3
            nid = f"tx:{t}_{i}"
            rows.append(
                {
                    "node_id": nid,
                    "node_type": "transaction",
                    "domain": "financial",
                    "time_first_seen": t,
                    "raw_features": [
                        float(t),
                        float(rng.normal(2.0 if bad else -2.0, 0.3)),
                        float(rng.normal(0, 1)),
                        float(rng.normal(0, 1)),
                        float(i % 3),
                    ],
                    "raw_attrs": None,
                }
            )
            label = "illicit" if bad else ("unknown" if i == 9 else "licit")
            label_rows.append(
                {"node_id": nid, "label": label, "label_source": "toy", "confidence": 1.0}
            )
    nodes = pl.DataFrame(rows).with_columns(pl.col("raw_features").cast(pl.List(pl.Float32)))
    edges = pl.DataFrame(
        [
            {
                "src": a,
                "dst": b,
                "edge_type": "pays",
                "timestamp": t,
                "amount": None,
                "directed": True,
                "raw_attrs": None,
            }
            for t in range(1, 7)
            for a, b in pairwise([f"tx:{t}_{i}" for i in range(10)])
        ]
    ).with_columns(pl.col("amount").cast(pl.Float64))
    store.write("toyfin", "nodes", nodes)
    store.write("toyfin", "edges", edges)
    store.write("toyfin", "labels", pl.DataFrame(label_rows))
    store.write_meta(
        "toyfin",
        {"dataset": "toyfin", "n_features": len(FEATURE_NAMES), "feature_names": FEATURE_NAMES},
    )
    return store


def _baseline_cfg(store: GraphStore, out: Path, **extra) -> dict:
    return {
        "dataset": "toyfin",
        "domain": "financial",
        "store_root": str(store.root),
        "output_dir": str(out),
        "seed": 0,
        "split": {"train_end": 4},
        "budgets": [3],
        "baselines": ["b2_xgb", "b3_xgb_graph"],
        "xgb": {"n_estimators": 20, "max_depth": 2},
        **extra,
    }


class TestLocalFeatureSet:
    def test_local_tabular_holds_only_local_raw_columns(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        nodes, edges = store.read("toyfin", "nodes"), store.read("toyfin", "edges")
        _, groups = assemble_features(
            "financial", nodes, edges, None, 5, feature_set="local", feature_names=FEATURE_NAMES
        )
        assert groups["tabular"] == ["raw_0", "raw_1", "raw_2"]
        # edge-derived money-flow columns and neighbour means live in 'graph'
        assert "in_count" in groups["graph"] and "velocity" in groups["graph"]
        assert "raw_1_nbr_mean" in groups["graph"]
        # the aggregate and degree columns appear nowhere
        everything = groups["tabular"] + groups["graph"]
        assert not any(c.startswith(("raw_3", "raw_4")) for c in everything)

    def test_full_set_is_unchanged(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        nodes, edges = store.read("toyfin", "nodes"), store.read("toyfin", "edges")
        _, groups = assemble_features("financial", nodes, edges, None, 5)
        assert groups["tabular"][:5] == [f"raw_{i}" for i in range(5)]
        assert "in_count" in groups["tabular"]

    def test_local_needs_feature_names_and_financial_domain(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        nodes, edges = store.read("toyfin", "nodes"), store.read("toyfin", "edges")
        with pytest.raises(ValueError, match="feature_names"):
            assemble_features("financial", nodes, edges, None, 5, feature_set="local")
        with pytest.raises(ValueError, match="financial domain"):
            assemble_features("procurement", nodes, edges, None, 0, feature_set="local")
        with pytest.raises(ValueError, match="unknown feature_set"):
            assemble_features("financial", nodes, edges, None, 5, feature_set="partial")

    def test_run_baselines_records_set_and_per_step(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        board = run_baselines(
            _baseline_cfg(store, tmp_path / "out", feature_set="local", per_time_step=True)
        )
        assert board["feature_set"] == "local"
        steps = board["baselines"]["b3_xgb_graph"]["per_time_step"]
        assert set(steps) == {"5", "6"}


class TestBaselinesMultiseed:
    def test_seeds_aggregate_and_resume(self, tmp_path) -> None:
        from collusiongraph.training.multiseed import run_baselines_multiseed

        store = toy_financial_store(tmp_path)
        cfg = _baseline_cfg(
            store,
            tmp_path / "ms",
            multiseed=True,
            seeds=[0, 1, 2],
            per_time_step=True,
            xgb={"n_estimators": 20, "max_depth": 2, "subsample": 0.8, "colsample_bytree": 0.8},
        )
        report = run_baselines_multiseed(cfg)
        b3 = report["baselines"]["b3_xgb_graph"]
        assert len(b3["auc_pr_per_seed"]) == 3
        assert b3["auc_pr_mean"] == pytest.approx(np.mean(b3["auc_pr_per_seed"]))
        assert b3["auc_pr_std"] == pytest.approx(np.std(b3["auc_pr_per_seed"], ddof=1))
        assert set(b3["per_time_step"]) == {"5", "6"}
        # resume: a second call reuses every stored seed
        again = run_baselines_multiseed(cfg)
        assert again["baselines"]["b3_xgb_graph"]["auc_pr_per_seed"] == b3["auc_pr_per_seed"]

    def test_refuses_to_resume_another_protocol(self, tmp_path) -> None:
        from collusiongraph.training.multiseed import run_baselines_multiseed

        store = toy_financial_store(tmp_path)
        cfg = _baseline_cfg(store, tmp_path / "ms", multiseed=True, seeds=[0])
        run_baselines_multiseed(cfg)
        with pytest.raises(ValueError, match="refusing to resume"):
            run_baselines_multiseed({**cfg, "feature_set": "local"})


def _write_scores(path: Path, ids: list[str], scores) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"node_id": ids, "score": np.asarray(scores, dtype=float)}).write_parquet(path)
    return path


class TestSignificanceRunner:
    def test_single_mode_matches_compare_score_files(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        labels = store.read("toyfin", "labels")
        ids = labels["node_id"].to_list()
        rng = np.random.default_rng(0)
        a = _write_scores(tmp_path / "a.parquet", ids, rng.random(len(ids)))
        b = _write_scores(tmp_path / "b.parquet", ids, rng.random(len(ids)))
        cfg = {
            "significance": True,
            "dataset": "toyfin",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "sig"),
            "n_boot": 200,
            "comparisons": {
                "x": {"label_a": "A", "label_b": "B", "scores_a": str(a), "scores_b": str(b)}
            },
        }
        report = run_significance(cfg)
        direct = compare_score_files(store.root, "toyfin", a, b, n_boot=200)
        assert report["kind"] == "paired_significance"
        assert report["comparisons"]["x"]["delta"] == direct["delta"]
        assert report["comparisons"]["x"]["delta_ci_low"] == direct["delta_ci_low"]
        assert (tmp_path / "sig" / "significance.json").is_file()

    def test_seed_mode_reports_range_and_seed_average(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        ids = store.read("toyfin", "labels")["node_id"].to_list()
        rng = np.random.default_rng(1)
        for s in range(3):
            _write_scores(tmp_path / f"a_{s}.parquet", ids, rng.random(len(ids)))
            _write_scores(tmp_path / f"b_{s}.parquet", ids, rng.random(len(ids)))
        cfg = {
            "significance": True,
            "dataset": "toyfin",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "sig"),
            "output_file": "significance_multiseed.json",
            "n_boot": 100,
            "seeds": [0, 1, 2],
            "seed_averaged": True,
            "comparisons": {
                "x": {
                    "scores_a": str(tmp_path / "a_{seed}.parquet"),
                    "scores_b": str(tmp_path / "b_{seed}.parquet"),
                }
            },
        }
        entry = run_significance(cfg)["comparisons"]["x"]
        deltas = [p["delta"] for p in entry["per_seed"]]
        assert entry["delta_min"] == min(deltas) and entry["delta_max"] == max(deltas)
        assert entry["difference_of_means"] == pytest.approx(
            np.mean([p["auc_pr_a"] for p in entry["per_seed"]])
            - np.mean([p["auc_pr_b"] for p in entry["per_seed"]])
        )
        assert "delta" in entry["seed_averaged"]


class TestSupervisedFusion:
    def test_fusion_on_a_shared_test_pool(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        nodes = store.read("toyfin", "nodes")
        labels = store.read("toyfin", "labels").to_dicts()
        bad = {r["node_id"] for r in labels if r["label"] == "illicit"}
        val_ids = nodes.filter(pl.col("time_first_seen") == 4)["node_id"].to_list()
        late_ids = nodes.filter(pl.col("time_first_seen") >= 4)["node_id"].to_list()
        test_ids = nodes.filter(pl.col("time_first_seen") >= 5)["node_id"].to_list()
        rng = np.random.default_rng(2)
        for s in (0, 1):

            def informative(ids, noise):
                return [(1.0 if i in bad else 0.0) + rng.normal(0, noise) for i in ids]

            _write_scores(tmp_path / f"g{s}/val.parquet", val_ids, informative(val_ids, 0.5))
            _write_scores(tmp_path / f"g{s}/test.parquet", test_ids, informative(test_ids, 0.5))
            _write_scores(tmp_path / f"t{s}/all.parquet", late_ids, informative(late_ids, 0.3))
        report = run_supervised_fusion(
            {
                "supervised_fusion": True,
                "dataset": "toyfin",
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "fusion"),
                "seeds": [0, 1],
                "split": {"loss_end": 3, "train_end": 4, "test_start": 5},
                "members": {
                    "gnn": {
                        "val": str(tmp_path / "g{seed}/val.parquet"),
                        "test": str(tmp_path / "g{seed}/test.parquet"),
                    },
                    "tree": {"scores": str(tmp_path / "t{seed}/all.parquet")},
                },
                "budgets": [3],
            }
        )
        assert set(report["aggregate"]) == {"gnn", "tree", "fused"}
        assert all(p["n_test_nodes"] == len(test_ids) for p in report["per_seed"])
        assert 0.0 <= report["aggregate"]["fused"]["auc_pr_mean"] <= 1.0

    def test_needs_two_members(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        with pytest.raises(ValueError, match="two members"):
            run_supervised_fusion(
                {
                    "supervised_fusion": True,
                    "dataset": "toyfin",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "f"),
                    "seeds": [0],
                    "split": {"loss_end": 3, "train_end": 4, "test_start": 5},
                    "members": {"only": {"scores": "x"}},
                    "budgets": [3],
                }
            )


class TestDiagnostics:
    def test_inverted_scorer_is_flagged(self) -> None:
        y = np.array([1, 1, 0, 0, 0, 0])
        s = np.array([0.1, 0.2, 0.9, 0.8, 0.7, 0.6])  # perfectly inverted
        out = score_checks(y, s)
        assert out["below_prevalence"] is True
        assert out["inverted_above_prevalence"] is True
        assert out["auc_pr_inverted"] == pytest.approx(1.0)

    def test_degree_shift_uses_as_of_train_features(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        shift = distribution_shift(
            store.read("toyfin", "nodes"), store.read("toyfin", "edges"), "tx:", 4, 5, "degree"
        )
        assert shift["n_train_nodes"] == 40 and shift["n_test_nodes"] == 20
        assert {r["feature"] for r in shift["top_shifted"]} >= {"degree"}

    def test_end_to_end_report(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        ids = (
            store.read("toyfin", "nodes")
            .filter(pl.col("time_first_seen") >= 5)["node_id"]
            .to_list()
        )
        path = _write_scores(tmp_path / "s.parquet", ids, np.linspace(1, 0, len(ids)))
        report = run_below_chance_diagnostics(
            {
                "diagnostics": True,
                "output_dir": str(tmp_path / "diag"),
                "cases": {
                    "toy": {
                        "dataset": "toyfin",
                        "store_root": str(store.root),
                        "node_type": "tx",
                        "scores": str(path),
                        "shift": {"train_end": 4, "test_start": 5, "features": "degree"},
                    }
                },
            }
        )
        case = report["cases"]["toy"]
        assert case["label_encoding"]["y_equals_1_for"] == "illicit"
        assert case["split_facts"]["n_nodes_test"] == 20
        assert (tmp_path / "diag" / "diagnostics.json").is_file()


class TestTransferSummary:
    def test_pooled_weighted_and_fold_cis(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        labels = store.read("toyfin", "labels")
        nodes = store.read("toyfin", "nodes")
        mdir = tmp_path / "matrix"
        folds = []
        rng = np.random.default_rng(3)
        bad = set(labels.filter(pl.col("label") == "illicit")["node_id"].to_list())
        for g, t in (("A", 5), ("B", 6)):
            ids = nodes.filter(pl.col("time_first_seen") == t)["node_id"].to_list()
            aucs = []
            for s in (0, 1):
                sc = [(1.0 if i in bad else 0.0) + rng.normal(0, 0.8) for i in ids]
                _write_scores(mdir / f"fold_{g}_s{s}" / "scores_test.parquet", ids, sc)
                aucs.append(0.5)
            folds.append(
                {
                    "test_group": g,
                    "status": "completed",
                    "n_confirmed_test": 9,
                    "prevalence_baseline": 1 / 3,
                    "auc_pr_mean": 0.5,
                    "lift_mean": 1.5 if g == "A" else 1.0,
                }
            )
        (mdir / "matrix.json").write_text(
            json.dumps(
                {
                    "dataset": "toyfin",
                    "seeds": [0, 1],
                    "folds": folds,
                    "summary": {"macro_lift_mean": 1.25},
                }
            ),
            encoding="utf-8",
        )
        out = summarise_matrix(mdir, labels, n_boot=50)
        assert out["n_confirmed_pooled"] == 18
        assert out["size_weighted_lift"] == pytest.approx(1.25)  # equal fold sizes
        assert len(out["pooled_per_seed"]) == 2
        for f in out["folds"]:
            assert f["auc_pr_ci_low"] <= f["auc_pr_ci_high"]
            assert f["lift_ci_low"] == pytest.approx(f["auc_pr_ci_low"] / f["prevalence"])


class TestDerivedNumbers:
    def test_wilson_interval_known_value(self) -> None:
        # hand check with z = 1.959964: centre 0.868615, half-width 0.110031
        lo, hi = wilson_interval(24, 26)
        assert lo == pytest.approx(0.758584, abs=1e-5)
        assert hi == pytest.approx(0.978646, abs=1e-5)

    def test_rate_reference_and_arithmetic(self, tmp_path) -> None:
        f = tmp_path / "a.json"
        f.write_text(json.dumps({"rate": 24 / 26, "n": 26, "x": [1.5, 0.5]}), encoding="utf-8")
        w = compute_item(
            {
                "op": "wilson",
                "rate": {"file": str(f), "key": "rate"},
                "n": {"file": str(f), "key": "n"},
            }
        )
        assert w["successes"] == 24 and w["n"] == 26
        d = compute_item(
            {
                "op": "difference",
                "a": {"file": str(f), "key": "x.0"},
                "b": {"file": str(f), "key": "x.1"},
            }
        )
        assert d["value"] == pytest.approx(1.0)
        r = compute_item({"op": "ratio", "a": 3, "b": 2})
        assert r["value"] == pytest.approx(1.5)
        with pytest.raises(ValueError):
            compute_item({"op": "median"})

    def test_window_auc_pr_pools_only_the_window(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        nodes = store.read("toyfin", "nodes")
        bad = set(store.read("toyfin", "labels").filter(pl.col("label") == "illicit")["node_id"])
        ids = nodes["node_id"].to_list()
        # perfect ranking in step 5, inverted ranking in step 6
        scores = [
            (1.0 if i in bad else 0.0) if i.startswith("tx:5_") else (0.0 if i in bad else 1.0)
            for i in ids
        ]
        for s in (0, 1):
            _write_scores(tmp_path / f"w{s}.parquet", ids, scores)
        base = {
            "op": "window_auc_pr",
            "dataset": "toyfin",
            "store_root": str(store.root),
            "scores": str(tmp_path / "w{seed}.parquet"),
            "seeds": [0, 1],
        }
        early = compute_item({**base, "steps": [5, 5]})
        late = compute_item({**base, "steps": [6, 6]})
        assert early["auc_pr_mean"] == pytest.approx(1.0)
        assert late["auc_pr_mean"] < early["prevalence"] + 0.1
        assert early["n_confirmed"] == 9 and early["auc_pr_std"] == 0.0


class TestDispatch:
    @pytest.mark.parametrize(
        ("cfg", "kind"),
        [
            ({"baselines": ["b2_xgb"]}, "baselines"),
            ({"baselines": ["b2_xgb"], "multiseed": True}, "baselines_multiseed"),
            ({"supervised_fusion": True, "members": {}}, "supervised_fusion"),
            ({"normalisation_rescore": True, "seeds": [0]}, "normalisation_rescore"),
        ],
    )
    def test_new_shapes(self, cfg, kind) -> None:
        assert select_train_runner(cfg) == kind


class TestLabelSmoothing:
    def test_zero_smoothing_is_the_published_loss(self) -> None:
        import torch
        from collusiongraph.training.losses import focal_loss, make_loss

        torch.manual_seed(0)
        logits = torch.randn(32)
        targets = (torch.rand(32) > 0.7).long()
        base = focal_loss(logits, targets, gamma=2.0)
        assert torch.equal(focal_loss(logits, targets, gamma=2.0, label_smoothing=0.0), base)
        assert torch.equal(make_loss("focal", gamma=2.0)(logits, targets), base)

    def test_smoothing_softens_the_targets(self) -> None:
        import torch
        import torch.nn.functional as F
        from collusiongraph.training.losses import focal_loss, make_loss

        logits = torch.tensor([4.0, -4.0])
        targets = torch.tensor([1, 0])
        # gamma = 0 reduces focal loss to plain BCE on the softened targets
        smoothed = focal_loss(logits, targets, gamma=0.0, label_smoothing=0.1)
        expected = F.binary_cross_entropy_with_logits(logits, torch.tensor([0.95, 0.05]))
        assert torch.allclose(smoothed, expected)
        assert make_loss("focal", gamma=0.0, label_smoothing=0.1)(logits, targets) == smoothed
        with pytest.raises(ValueError):
            focal_loss(logits, targets, label_smoothing=1.0)


class TestLabelAssociation:
    """B4: per-window prevalence and feature-label ROC-AUC."""

    def _assoc(self, store, windows):
        from collusiongraph.eval.diagnostics import label_association

        return label_association(
            store.read("toyfin", "nodes"),
            store.read("toyfin", "edges"),
            store.read("toyfin", "labels"),
            "tx:",
            "degree",
            4,
            windows,
        )

    def test_windows_report_prevalence_and_sign(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        out = self._assoc(
            store,
            {"train": {"side": "train", "until": 4}, "test": {"side": "test", "after": 4}},
        )
        train, test = out["windows"]["train"], out["windows"]["test"]
        # 3 illicit and 6 licit confirmed nodes per step; one unknown is dropped
        assert train["n_confirmed"] == 36 and test["n_confirmed"] == 18
        assert train["prevalence"] == pytest.approx(1 / 3)
        assert set(train["roc_auc"]) == {"degree_out", "degree_in", "degree"}
        assert "train" in out["opposite_sign_to_test"]

    def test_rejects_bad_windows(self, tmp_path) -> None:
        store = toy_financial_store(tmp_path)
        with pytest.raises(ValueError, match="side"):
            self._assoc(store, {"w": {"side": "both"}})
        with pytest.raises(ValueError, match="train_end"):
            self._assoc(store, {"w": {"side": "train", "until": 6}})


class TestExcludeFeatures:
    """B4 diagnostic ablation: named columns leave both featurisations."""

    def _cfg(self, store, out, **extra) -> dict:
        return {
            "dataset": "toysrc",
            "store_root": str(store.root),
            "output_dir": str(out),
            "seed": 0,
            "features": "structural",
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
            "epochs": 3,
            "patience": 3,
            "budgets": [4],
            **extra,
        }

    def test_columns_are_dropped_and_recorded(self, tmp_path) -> None:
        from collusiongraph.training.trainer import train_gnn

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        drop = ["community_size", "degree_rel_community"]
        record = train_gnn(self._cfg(store, tmp_path / "run", exclude_features=drop))
        assert record["exclude_features"] == drop
        stats = json.loads((tmp_path / "run" / "feature_stats.json").read_text(encoding="utf-8"))
        assert not set(drop) & set(stats["stats"])
        default = train_gnn(self._cfg(store, tmp_path / "base"))
        assert "exclude_features" not in default

    def test_unknown_column_raises(self, tmp_path) -> None:
        from collusiongraph.training.trainer import train_gnn

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        with pytest.raises(ValueError, match="unknown columns"):
            train_gnn(self._cfg(store, tmp_path / "run", exclude_features=["no_such"]))


class TestFullLabelComparison:
    """B6: the stored encoder reproduces the published probe exactly."""

    def test_frozen_probe_matches_the_probe_run(self, tmp_path) -> None:
        from collusiongraph.training.transfer_run import (
            run_cross_domain_probe,
            run_full_label_comparison,
        )

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        source = {
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
        }
        target = {"dataset": "toysrc", "split": {"train_end": 3, "test_start": 5}}
        probe = run_cross_domain_probe(
            {
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "probe"),
                "seed": 0,
                "budgets": [4],
                "source": source,
                "target": target,
            }
        )
        reference = tmp_path / "ref.json"
        reference.write_text(
            json.dumps({"baselines": {"b2_xgb": {"auc_pr_mean": 0.5, "auc_pr_std": 0.1}}}),
            encoding="utf-8",
        )
        report = run_full_label_comparison(
            {
                "full_label_comparison": True,
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "flc"),
                "seed": 0,
                "n_boot": 50,
                "directions": {
                    "toy": {
                        "source_run": str(tmp_path / "src_run"),
                        "target": {**target, "domain": "financial"},
                        "budgets": [4],
                        "in_domain_reference": {"path": str(reference), "baseline": "b2_xgb"},
                    }
                },
            }
        )
        block = report["directions"]["toy"]
        assert set(block["comparators"]) == {"frozen_probe", "structural_probe", "b2_inputs_probe"}
        frozen = block["comparators"]["frozen_probe"]["node_level"]["auc_pr"]
        assert frozen == probe["node_level"]["auc_pr"]
        assert set(block["paired"]) == {
            "frozen_probe_vs_structural_probe",
            "frozen_probe_vs_b2_inputs_probe",
        }
        assert block["in_domain_reference"]["auc_pr_mean"] == 0.5
        assert (tmp_path / "flc" / "full_label_comparison.json").is_file()

    def test_dispatch(self) -> None:
        cfg = {"full_label_comparison": True, "directions": {}}
        assert select_train_runner(cfg) == "full_label_comparison"


class TestNormalisationAblation:
    """D24: per-graph normalisation is recorded and the default is unchanged."""

    def _cfg(self, store, out, **extra) -> dict:
        return {
            "dataset": "toysrc",
            "store_root": str(store.root),
            "output_dir": str(out),
            "seed": 0,
            "features": "structural",
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
            "epochs": 3,
            "patience": 3,
            "budgets": [4],
            **extra,
        }

    def test_per_graph_is_recorded_and_changes_only_inference(self, tmp_path) -> None:
        from collusiongraph.training.trainer import train_gnn

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        frozen = train_gnn(self._cfg(store, tmp_path / "frozen"))
        per_graph = train_gnn(self._cfg(store, tmp_path / "pg", normalisation="per_graph"))
        assert "normalisation" not in frozen
        assert per_graph["normalisation"] == "per_graph"
        # training and validation run on the frozen train-graph statistics
        assert per_graph["best_val_auc_pr"] == frozen["best_val_auc_pr"]
        val_a = pl.read_parquet(tmp_path / "frozen" / "scores_val.parquet")
        val_b = pl.read_parquet(tmp_path / "pg" / "scores_val.parquet")
        assert val_a.equals(val_b)

    def test_unknown_mode_raises(self, tmp_path) -> None:
        from collusiongraph.training.trainer import train_gnn

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        with pytest.raises(ValueError, match="normalisation"):
            train_gnn(self._cfg(store, tmp_path / "x", normalisation="test_time"))


class TestNormalisationRescore:
    """D24: stored checkpoints re-scored under frozen and per-graph statistics."""

    def _source(self, store, tmp_path) -> Path:
        import yaml

        cfg = {
            "dataset": "toysrc",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "src"),
            "multiseed": True,
            "seeds": [0, 1],
            "features": "structural",
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
            "epochs": 3,
            "patience": 3,
            "budgets": [4],
        }
        path = tmp_path / "source.yaml"
        path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        return path

    def _rescore_cfg(self, source: Path, out: Path) -> dict:
        return {
            "normalisation_rescore": True,
            "source_config": str(source),
            "seeds": [0, 1],
            "output_dir": str(out),
            "n_boot": 50,
        }

    def test_frozen_reproduces_and_per_graph_matches_training(self, tmp_path) -> None:
        import yaml
        from collusiongraph.training.multiseed import run_multiseed
        from collusiongraph.training.rescore import run_normalisation_rescore
        from collusiongraph.training.trainer import train_gnn

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        source = self._source(store, tmp_path)
        campaign = run_multiseed(str(source))
        base = yaml.safe_load(source.read_text(encoding="utf-8"))
        base = {k: v for k, v in base.items() if k not in ("multiseed", "seeds", "output_dir")}
        trained_pg = train_gnn(
            {**base, "seed": 0, "output_dir": str(tmp_path / "pg"), "normalisation": "per_graph"}
        )
        report = run_normalisation_rescore(self._rescore_cfg(source, tmp_path / "out"))

        frozen = [r["auc_pr"]["frozen"] for r in report["per_seed"]]
        assert frozen == [r["auc_pr"] for r in campaign["per_seed"]]
        seed0 = report["per_seed"][0]
        assert seed0["auc_pr"]["per_graph"] == trained_pg["node_level"]["auc_pr"]
        rescored = pl.read_parquet(
            tmp_path / "out" / "seed_0" / "per_graph" / "scores_test.parquet"
        )
        trained = pl.read_parquet(tmp_path / "pg" / "scores_test.parquet")
        assert rescored.equals(trained)
        agg = report["aggregate"]
        assert agg["frozen"]["mean"] == pytest.approx(np.mean(frozen))
        deltas = [r["auc_pr"]["per_graph"] - r["auc_pr"]["frozen"] for r in report["per_seed"]]
        assert agg["delta_per_graph_minus_frozen"]["mean"] == pytest.approx(np.mean(deltas))
        paired = seed0["paired_per_graph_minus_frozen"]
        assert paired["delta"] == pytest.approx(deltas[0])
        assert (tmp_path / "out" / "normalisation_rescore.json").is_file()

    def test_tampered_checkpoint_is_refused(self, tmp_path) -> None:
        import torch
        from collusiongraph.training.multiseed import run_multiseed
        from collusiongraph.training.rescore import run_normalisation_rescore

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        source = self._source(store, tmp_path)
        run_multiseed(str(source))
        ckpt = tmp_path / "src" / "seed_1" / "model.pt"
        state = torch.load(ckpt)
        torch.save({k: v + 0.5 if v.is_floating_point() else v for k, v in state.items()}, ckpt)
        with pytest.raises(RuntimeError, match="rebuild differs from training"):
            run_normalisation_rescore(self._rescore_cfg(source, tmp_path / "out"))

    def test_rejects_a_per_graph_source(self, tmp_path) -> None:
        import yaml
        from collusiongraph.training.rescore import run_normalisation_rescore

        from .test_transfer import financial_store

        store = financial_store(tmp_path)
        source = self._source(store, tmp_path)
        cfg = yaml.safe_load(source.read_text(encoding="utf-8"))
        source.write_text(yaml.safe_dump({**cfg, "normalisation": "per_graph"}), encoding="utf-8")
        with pytest.raises(ValueError, match="frozen normalisation"):
            run_normalisation_rescore(self._rescore_cfg(source, tmp_path / "out"))
