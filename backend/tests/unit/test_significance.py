"""Bootstrap significance tests (§7 step 29): hand-computable identities,
stratification guarantees, determinism, and the file-compare join semantics."""

import numpy as np
import polars as pl
import pytest
from collusiongraph.eval import (
    bootstrap_auc_pr_ci,
    compare_score_files,
    paired_bootstrap_auc_pr,
)
from collusiongraph.schema import GraphStore

RNG = np.random.default_rng(7)


class TestBootstrapCi:
    def test_perfect_scorer_has_degenerate_ci_at_one(self) -> None:
        # perfectly separable scores stay separable under ANY resample that
        # keeps both classes — which stratification guarantees
        y = np.array([1, 1, 0, 0, 0, 0])
        s = np.array([0.9, 0.8, 0.3, 0.2, 0.1, 0.05])
        out = bootstrap_auc_pr_ci(y, s, n_boot=200, seed=0)
        assert out["auc_pr"] == 1.0
        assert out["ci_low"] == 1.0 and out["ci_high"] == 1.0
        assert out["prevalence_baseline"] == pytest.approx(2 / 6)

    def test_stratification_keeps_both_classes(self) -> None:
        # 2 pos / 2 neg: unstratified resampling would go single-class often
        # and crash auc_pr — stratified never does
        y = np.array([1, 1, 0, 0])
        s = np.array([0.6, 0.4, 0.5, 0.3])
        out = bootstrap_auc_pr_ci(y, s, n_boot=500, seed=1)
        assert np.isfinite(out["ci_low"]) and np.isfinite(out["ci_high"])

    def test_deterministic_under_seed(self) -> None:
        y = (RNG.random(80) < 0.3).astype(int)
        s = RNG.random(80)
        a = bootstrap_auc_pr_ci(y, s, n_boot=100, seed=42)
        b = bootstrap_auc_pr_ci(y, s, n_boot=100, seed=42)
        assert a == b

    def test_single_class_raises(self) -> None:
        with pytest.raises(ValueError, match="no positives"):
            bootstrap_auc_pr_ci(np.zeros(4, dtype=int), np.arange(4), n_boot=10)


class TestPairedBootstrap:
    def test_identical_scorers_are_not_significant(self) -> None:
        y = (RNG.random(60) < 0.3).astype(int)
        s = RNG.random(60)
        out = paired_bootstrap_auc_pr(y, s, s.copy(), n_boot=200, seed=0)
        assert out["delta"] == 0.0
        assert out["p_value"] == 1.0
        assert out["delta_ci_low"] == 0.0 and out["delta_ci_high"] == 0.0

    def test_strong_beats_random_significantly(self) -> None:
        rng = np.random.default_rng(3)
        y = (rng.random(300) < 0.25).astype(int)
        strong = y + rng.normal(0, 0.2, size=y.size)
        random = rng.random(y.size)
        out = paired_bootstrap_auc_pr(y, strong, random, n_boot=500, seed=0)
        assert out["delta"] > 0.3
        assert out["p_value"] < 0.01
        assert out["delta_ci_low"] > 0.0  # CI excludes zero

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="aligned"):
            paired_bootstrap_auc_pr(np.array([1, 0]), np.arange(2), np.arange(3))


class TestCompareScoreFiles:
    def test_intersection_and_confirmed_semantics(self, tmp_path) -> None:
        store = GraphStore(tmp_path / "interim")
        labels = pl.DataFrame(
            {
                "node_id": ["n1", "n2", "n3", "n4", "n5"],
                "label": ["illicit", "licit", "unknown", "illicit", "licit"],
                "label_source": ["toy"] * 5,
                "confidence": [1.0] * 5,
            }
        )
        nodes = pl.DataFrame(
            {
                "node_id": ["n1", "n2", "n3", "n4", "n5"],
                "node_type": ["account"] * 5,
                "domain": ["financial"] * 5,
                "time_first_seen": [1, 1, 1, 1, 1],
                "raw_features": [None] * 5,
                "raw_attrs": [None] * 5,
            }
        )
        store.write("toy", "nodes", nodes)
        store.write("toy", "labels", labels)
        # a scores n1..n4 (+unknown n3); b scores n1,n2,n4,n5 — intersection
        # of confirmed = n1, n2, n4
        a_path, b_path = tmp_path / "a.parquet", tmp_path / "b.parquet"
        pl.DataFrame(
            {"node_id": ["n1", "n2", "n3", "n4"], "score": [0.9, 0.1, 0.5, 0.8]}
        ).write_parquet(a_path)
        pl.DataFrame(
            {"node_id": ["n1", "n2", "n4", "n5"], "score": [0.2, 0.3, 0.1, 0.4]}
        ).write_parquet(b_path)
        out = compare_score_files(store.root, "toy", a_path, b_path, n_boot=100, seed=0)
        assert out["n"] == 3
        assert out["n_only_a"] == 1 and out["n_only_b"] == 1
        assert out["auc_pr_a"] == 1.0  # a ranks n1 and n4 above n2

    def test_empty_intersection_raises(self, tmp_path) -> None:
        store = GraphStore(tmp_path / "interim")
        store.write(
            "toy",
            "labels",
            pl.DataFrame(
                {
                    "node_id": ["n1"],
                    "label": ["illicit"],
                    "label_source": ["toy"],
                    "confidence": [1.0],
                }
            ),
        )
        a_path, b_path = tmp_path / "a.parquet", tmp_path / "b.parquet"
        pl.DataFrame({"node_id": ["n1"], "score": [0.9]}).write_parquet(a_path)
        pl.DataFrame({"node_id": ["nX"], "score": [0.2]}).write_parquet(b_path)
        with pytest.raises(ValueError, match="no confirmed nodes"):
            compare_score_files(store.root, "toy", a_path, b_path, n_boot=10)
