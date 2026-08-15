"""Baseline leakage tests (§9.1b): the M1 baselines must obey the same as-of
discipline as the feature layer — training-side inputs computed on the
train-visible graph only, with negative controls proving the checks bite."""

import polars as pl
import pytest
from collusiongraph.features import restrict_as_of
from collusiongraph.models import Rule, RulesEngine, neighbor_mean_features

pytestmark = pytest.mark.leakage

AS_OF = 5


def temporal_graph() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    nodes = pl.DataFrame({"node_id": ["a", "b", "c", "f"], "time_first_seen": [1, 2, 3, 8]})
    edges = pl.DataFrame(
        {
            "src": ["a", "b", "f"],
            "dst": ["b", "c", "a"],  # f->a arrives after AS_OF
            "timestamp": [2, 3, 9],
        }
    )
    features = pl.DataFrame({"node_id": ["a", "b", "c", "f"], "x": [10.0, 20.0, 30.0, 1_000.0]})
    return nodes, edges, features


class TestNeighborAggregationAsOf:
    def test_as_of_equals_truncated_graph(self) -> None:
        nodes, edges, features = temporal_graph()
        t_nodes, t_edges = restrict_as_of(nodes, edges, AS_OF)
        assert neighbor_mean_features(nodes, edges, features, as_of=AS_OF).equals(
            neighbor_mean_features(t_nodes, t_edges, features)
        )

    def test_negative_control_future_edge_changes_full_graph_result(self) -> None:
        """Without as_of, f's 1000.0 leaks into a's neighborhood mean — proving
        the equivalence above cannot pass vacuously."""
        nodes, edges, features = temporal_graph()
        full = neighbor_mean_features(nodes, edges, features)
        past = neighbor_mean_features(nodes, edges, features, as_of=AS_OF)
        a_full = dict(full.select("node_id", "x_nbr_mean").iter_rows())["a"]
        a_past = dict(past.select("node_id", "x_nbr_mean").iter_rows())["a"]
        assert a_full == pytest.approx((20.0 + 1_000.0) / 2)
        assert a_past == pytest.approx(20.0)


class TestRuleThresholdsAreTrainOnly:
    def test_test_period_extremes_cannot_move_thresholds(self) -> None:
        """Fitting on train features then scoring wildly different test features
        must reproduce the train-fit thresholds exactly."""
        train = pl.DataFrame({"node_id": [f"n{i}" for i in range(5)], "x": [1.0, 2, 3, 4, 5]})
        engine = RulesEngine([Rule("x", "high", 80.0)]).fit(train)
        test_mild = pl.DataFrame({"node_id": ["t"], "x": [4.5]})
        test_extreme = pl.DataFrame({"node_id": ["t"], "x": [4.5]}).vstack(
            pl.DataFrame({"node_id": ["huge"], "x": [1_000_000.0]})
        )
        assert (
            dict(engine.score(test_mild).iter_rows())["t"]
            == dict(engine.score(test_extreme).iter_rows())["t"]
        )
