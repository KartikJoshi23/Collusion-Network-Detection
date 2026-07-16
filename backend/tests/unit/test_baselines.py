"""Baseline correctness (§7 step 10, §9.1): rules engine, neighborhood
aggregation, XGB wrappers, screens composite — hand-checked on tiny fixtures —
plus a config-driven end-to-end run on a synthetic store."""

import numpy as np
import polars as pl
import pytest
import yaml
from collusiongraph.models import (
    Rule,
    RulesEngine,
    neighbor_mean_features,
    screens_composite_scores,
    xgb_scores,
)
from collusiongraph.schema import GraphStore
from collusiongraph.training import run_baselines


class TestRulesEngine:
    def features(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "node_id": [f"n{i}" for i in range(10)],
                "deg": [1, 1, 2, 2, 3, 3, 4, 4, 5, 100],
                "hold": [9.0, 8, 7, 6, 5, 4, 3, 2, 1, None],
            }
        )

    def test_scores_are_fraction_of_triggered_rules(self) -> None:
        engine = RulesEngine([Rule("deg", "high", 90.0), Rule("hold", "low", 10.0)]).fit(
            self.features()
        )
        scored = engine.score(self.features()).sort("node_id")
        by_id = dict(scored.iter_rows())
        assert by_id["n9"] == pytest.approx(0.5)  # deg=100 triggers; hold null never triggers
        assert by_id["n8"] == pytest.approx(0.5)  # hold=1 <= P10 triggers
        assert by_id["n4"] == pytest.approx(0.0)

    def test_thresholds_fit_on_train_only(self) -> None:
        """§9.1b negative control: extreme TEST values must not move thresholds."""
        engine = RulesEngine([Rule("deg", "high", 90.0)]).fit(self.features())
        test = pl.DataFrame({"node_id": ["t1", "t2"], "deg": [50, 1_000_000], "hold": [1.0, 1.0]})
        scored = dict(engine.score(test).iter_rows())
        assert scored["t1"] == 1.0  # 50 crosses the TRAIN P90 regardless of test extremes
        assert scored["t2"] == 1.0

    def test_unfitted_engine_refuses_to_score(self) -> None:
        with pytest.raises(RuntimeError, match="fit"):
            RulesEngine([Rule("deg", "high", 90.0)]).score(self.features())


class TestNeighborMean:
    def graph(self) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        nodes = pl.DataFrame({"node_id": ["a", "b", "c", "d"], "time_first_seen": [1, 1, 1, 1]})
        edges = pl.DataFrame(
            {
                "src": ["a", "a", "b"],
                "dst": ["b", "c", "a"],  # b<->a mutual pair collapses to one neighbor
                "timestamp": [1, 1, 1],
            }
        )
        features = pl.DataFrame({"node_id": ["a", "b", "c", "d"], "x": [10.0, 20.0, 30.0, 40.0]})
        return nodes, edges, features

    def test_mean_over_distinct_undirected_neighbors(self) -> None:
        nodes, edges, features = self.graph()
        out = neighbor_mean_features(nodes, edges, features).sort("node_id")
        vals = dict(out.select("node_id", "x_nbr_mean").iter_rows())
        assert vals["a"] == pytest.approx(25.0)  # neighbors b, c — mutual edge not doubled
        assert vals["b"] == pytest.approx(10.0)
        assert np.isnan(vals["d"])  # isolated: unknown, not zero

    def test_null_neighbor_values_are_skipped(self) -> None:
        nodes, edges, features = self.graph()
        features = features.with_columns(
            pl.when(pl.col("node_id") == "c").then(None).otherwise(pl.col("x")).alias("x")
        )
        out = neighbor_mean_features(nodes, edges, features).sort("node_id")
        vals = dict(out.select("node_id", "x_nbr_mean").iter_rows())
        assert vals["a"] == pytest.approx(20.0)  # only b contributes; c unknown


class TestXgbScores:
    def test_learns_a_separable_toy_problem(self) -> None:
        rng = np.random.default_rng(0)
        x = rng.normal(size=(200, 3))
        y = (x[:, 0] > 0.5).astype(np.int8)  # imbalanced (~30% positive)
        scores = xgb_scores(x, y, x, seed=0, n_estimators=50, max_depth=3)
        top = np.argsort(-scores)[: int(y.sum())]
        assert y[top].mean() > 0.95

    def test_single_class_training_rejected(self) -> None:
        x = np.zeros((10, 2))
        with pytest.raises(ValueError, match="both classes"):
            xgb_scores(x, np.zeros(10, dtype=np.int8), x)

    def test_deterministic_under_seed(self) -> None:
        rng = np.random.default_rng(1)
        x = rng.normal(size=(100, 3))
        y = (x[:, 1] > 0).astype(np.int8)
        a = xgb_scores(x, y, x, seed=7, n_estimators=20)
        b = xgb_scores(x, y, x, seed=7, n_estimators=20)
        assert np.array_equal(a, b)


class TestScreensComposite:
    def test_direction_adjustment_and_null_skipping(self) -> None:
        features = pl.DataFrame(
            {
                "node_id": ["f1", "f2", "f3"],
                "share": [0.1, 0.5, 0.9],  # high = risky
                "entropy": [0.9, 0.5, None],  # low = risky -> negated
            }
        )
        scored = screens_composite_scores(
            features, columns=["share", "entropy"], low_risk_columns=["entropy"]
        ).sort("node_id")
        vals = dict(scored.iter_rows())
        # f3: high share (+z) and null entropy (skipped) -> highest risk
        assert vals["f3"] > vals["f2"] > vals["f1"]

    def test_unknown_columns_rejected(self) -> None:
        with pytest.raises(ValueError, match="absent"):
            screens_composite_scores(pl.DataFrame({"node_id": ["a"], "x": [1.0]}), columns=["nope"])


def synthetic_procurement_store(tmp_path) -> GraphStore:
    """Tiny two-era market: cartel firms F1/F2 rotate wins from buyer B; clean
    firms win once each. Era 1 (2010) trains; era 2 (2020) tests."""
    store = GraphStore(tmp_path / "interim")
    firms = [f"firm:M:F{i}" for i in range(8)]
    years = [2010, 2010, 2010, 2010, 2020, 2020, 2020, 2020]
    tenders = [f"tender:M:T{i}" for i in range(16)]
    nodes = pl.concat(
        [
            pl.DataFrame({"node_id": firms, "time_first_seen": years}).with_columns(
                pl.lit("firm").alias("node_type")
            ),
            pl.DataFrame(
                {"node_id": tenders, "time_first_seen": [2010] * 8 + [2020] * 8}
            ).with_columns(pl.lit("tender").alias("node_type")),
        ]
    ).with_columns(
        pl.lit("procurement").alias("domain"),
        pl.lit(None, dtype=pl.List(pl.Float32)).alias("raw_features"),
        pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
    )
    # cartel firms (F0 train-era, F4/F5 test-era) hoard awards; clean firms win once
    winners = (
        ["firm:M:F0"] * 5
        + ["firm:M:F1", "firm:M:F2", "firm:M:F3"]
        + [
            "firm:M:F4",
            "firm:M:F5",
        ]
        * 3
        + ["firm:M:F6", "firm:M:F7"]
    )
    edges = pl.DataFrame(
        {
            "src": tenders,
            "dst": winners,
            "edge_type": ["awarded"] * 16,
            "timestamp": [2010] * 8 + [2020] * 8,
            "amount": [None] * 16,
            "directed": [True] * 16,
        }
    ).with_columns(pl.col("amount").cast(pl.Float64))
    labels = pl.DataFrame(
        {
            "node_id": firms,
            "label": [
                "illicit",
                "licit",
                "licit",
                "licit",  # era 1: F0 hoards
                "illicit",
                "illicit",
                "licit",
                "licit",  # era 2: F4/F5 hoard
            ],
            "label_source": ["toy"] * 8,
            "confidence": [1.0] * 8,
        }
    )
    store.write("toyproc", "nodes", nodes)
    store.write("toyproc", "edges", edges)
    store.write("toyproc", "labels", labels)
    store.write_meta("toyproc", {"dataset": "toyproc", "time_unit": "year"})
    return store


class TestRunBaselines:
    def test_end_to_end_scoreboard(self, tmp_path) -> None:
        store = synthetic_procurement_store(tmp_path)
        config = {
            "dataset": "toyproc",
            "domain": "procurement",
            "node_type": "firm",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "out"),
            "seed": 0,
            "split": {"train_end": 2015},
            "budgets": [2],
            "baselines": ["b1_rules", "b2_xgb", "b3_xgb_graph", "b4_screens"],
            "rules": [
                {"column": "n_awards", "direction": "high", "percentile": 75},
                {"column": "market_share", "direction": "high", "percentile": 75},
            ],
            "screens": {"columns": ["n_awards", "market_share"]},
            "xgb": {"n_estimators": 30, "max_depth": 3},
        }
        scoreboard = run_baselines(config)
        assert (tmp_path / "out" / "scoreboard.json").is_file()
        assert set(scoreboard["baselines"]) == {
            "b1_rules",
            "b2_xgb",
            "b3_xgb_graph",
            "b4_screens",
        }
        # only the 4 test-era firms are scored; each baseline wrote a parquet + metrics
        assert scoreboard["n_test_scored"] == 4
        for name in scoreboard["baselines"]:
            assert (tmp_path / "out" / "scores" / f"{name}.parquet").is_file()
            assert (tmp_path / "out" / name / "metrics.json").is_file()
            assert "auc_pr" in scoreboard["baselines"][name]
        # the hoarding pattern is learnable: rules put the cartel firms on top
        b1 = pl.read_parquet(tmp_path / "out" / "scores" / "b1_rules.parquet").sort(
            "score", descending=True
        )
        assert set(b1.head(2)["node_id"]) == {"firm:M:F4", "firm:M:F5"}

    def test_single_class_split_rejected(self, tmp_path) -> None:
        store = synthetic_procurement_store(tmp_path)
        config = {
            "dataset": "toyproc",
            "domain": "procurement",
            "node_type": "firm",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "out2"),
            "split": {"train_end": 2005},  # nothing labeled before 2005
            "budgets": [2],
            "baselines": ["b2_xgb"],
        }
        with pytest.raises(ValueError):
            run_baselines(config)

    def test_yaml_config_roundtrip(self, tmp_path) -> None:
        """The committed experiment configs drive the same entry point."""
        store = synthetic_procurement_store(tmp_path)
        cfg_path = tmp_path / "exp.yaml"
        cfg_path.write_text(
            yaml.safe_dump(
                {
                    "dataset": "toyproc",
                    "domain": "procurement",
                    "node_type": "firm",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "out3"),
                    "split": {"train_end": 2015},
                    "budgets": [2],
                    "baselines": ["b4_screens"],
                    "screens": {"columns": ["n_awards", "market_share"]},
                }
            ),
            encoding="utf-8",
        )
        scoreboard = run_baselines(cfg_path)
        assert "b4_screens" in scoreboard["baselines"]
