"""Leakage tests (§9.1 — the tests that protect the paper).

This suite replaces the Week-1 wiring placeholder. It proves, on constructed
fixtures, that (a) the strict-inductive temporal splitter cannot expose
test-period adjacency at training time, (b) LOCO folds share no entities,
(c) deliberately leaky inputs are REJECTED (negative tests — a check that
cannot fail protects nothing), and (d) the AMLworld post-window fence drops
the poisoned tail.
"""

import polars as pl
import pytest
from collusiongraph.splits import (
    LeakageError,
    check_group_disjoint,
    check_train_edges_within_train_nodes,
    loco_folds,
    strict_temporal_split,
)

pytestmark = pytest.mark.leakage


def temporal_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Six nodes over times 1–4 with edges inside and across the 2|3 boundary."""
    nodes = pl.DataFrame(
        {
            "node_id": ["a", "b", "c", "d", "e", "f"],
            "time_first_seen": [1, 1, 2, 3, 4, None],
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["a", "b", "c", "d", "a"],
            "dst": ["b", "c", "d", "e", "e"],
            # a->b, b->c inside train; c->d and d->e in test period; a->e crosses
            "timestamp": [1, 2, 3, 4, 4],
        }
    )
    return nodes, edges


class TestStrictTemporal:
    def test_no_test_period_adjacency_at_train_time(self) -> None:
        nodes, edges = temporal_fixture()
        split = strict_temporal_split(nodes, edges, train_end=2)
        train_pairs = set(split.train_edges.select("src", "dst").rows())
        assert train_pairs == {("a", "b"), ("b", "c")}
        assert set(split.train_nodes["node_id"]) == {"a", "b", "c"}
        assert set(split.test_nodes["node_id"]) == {"d", "e"}

    def test_inference_graph_keeps_full_adjacency(self) -> None:
        nodes, edges = temporal_fixture()
        split = strict_temporal_split(nodes, edges, train_end=2)
        assert split.inference_edges.height == 5

    def test_unplaced_nodes_belong_to_neither_side(self) -> None:
        nodes, edges = temporal_fixture()
        split = strict_temporal_split(nodes, edges, train_end=2)
        assert split.report["n_unplaced_nodes"] == 1
        for frame in (split.train_nodes, split.test_nodes):
            assert "f" not in frame["node_id"].to_list()

    def test_gap_between_train_and_test_is_supported(self) -> None:
        nodes, edges = temporal_fixture()
        split = strict_temporal_split(nodes, edges, train_end=2, test_start=4)
        assert set(split.test_nodes["node_id"]) == {"e"}
        assert split.report["n_gap_nodes"] == 1  # d (t=3) sits in the embargo gap

    def test_leaky_edge_set_is_rejected(self) -> None:
        """Negative control: an edge set reaching a test-period node must raise."""
        nodes, edges = temporal_fixture()
        split = strict_temporal_split(nodes, edges, train_end=2)
        leaky = pl.concat(
            [split.train_edges, pl.DataFrame({"src": ["a"], "dst": ["e"], "timestamp": [1]})]
        )
        with pytest.raises(LeakageError, match="outside the training node set"):
            check_train_edges_within_train_nodes(leaky, split.train_nodes["node_id"])

    def test_future_timestamp_on_train_edge_is_rejected(self) -> None:
        """Negative control: an edge between train nodes but timestamped in the
        test period (future interaction between old nodes) must not survive."""
        nodes, edges = temporal_fixture()
        edges = pl.concat([edges, pl.DataFrame({"src": ["a"], "dst": ["b"], "timestamp": [4]})])
        split = strict_temporal_split(nodes, edges, train_end=2)
        assert (split.train_edges["timestamp"] > 2).sum() == 0

    def test_invalid_boundaries_rejected(self) -> None:
        nodes, edges = temporal_fixture()
        with pytest.raises(ValueError, match="must be after"):
            strict_temporal_split(nodes, edges, train_end=3, test_start=2)


class TestAMLworldFence:
    def test_post_window_tail_is_dropped(self) -> None:
        """EDA notebook 05: rows after the primary window are 59.1% laundering —
        the fence must remove them before any temporal split is taken."""
        nodes = pl.DataFrame({"node_id": ["a", "b", "late"], "time_first_seen": [10, 20, 99]})
        edges = pl.DataFrame({"src": ["a", "b"], "dst": ["b", "late"], "timestamp": [15, 99]})
        split = strict_temporal_split(nodes, edges, train_end=12, fence_after=30)
        assert split.report["n_fenced_nodes"] == 1
        assert split.report["n_fenced_edges"] == 1
        all_ids = pl.concat([split.train_nodes, split.test_nodes])["node_id"].to_list()
        assert "late" not in all_ids
        assert split.inference_edges.height == 1


def loco_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    nodes = pl.DataFrame(
        {
            "node_id": [
                "firm:c1:F1",
                "tender:c1:T1",
                "firm:c2:F2",
                "tender:c2:T2",
                "firm:c3:F3",
            ],
            "time_first_seen": [2010, 2010, 2011, 2011, 2012],
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["tender:c1:T1", "tender:c2:T2", "firm:c1:F1"],
            "dst": ["firm:c1:F1", "firm:c2:F2", "tender:c2:T2"],
            "timestamp": [2010, 2011, 2011],
        }
    )  # third edge crosses c1->c2 deliberately
    return nodes, edges


class TestLoco:
    def test_folds_are_entity_disjoint_and_complete(self) -> None:
        nodes, edges = loco_fixture()
        folds = list(loco_folds(nodes, edges))
        assert [f.test_group for f in folds] == ["c1", "c2", "c3"]
        for fold in folds:
            train_ids = set(fold.train_nodes["node_id"])
            test_ids = set(fold.test_nodes["node_id"])
            assert not train_ids & test_ids
            assert train_ids | test_ids == set(nodes["node_id"])

    def test_cross_group_edges_never_bridge_folds(self) -> None:
        nodes, edges = loco_fixture()
        for fold in loco_folds(nodes, edges):
            assert fold.report["n_cross_group_edges_excluded"] == 1
            for frame in (fold.train_edges, fold.test_edges):
                joined = frame.join(
                    nodes.select(pl.col("node_id").alias("src"), pl.lit(1).alias("_")), on="src"
                )
                assert joined.height == frame.height  # sanity: endpoints resolve

    def test_overlapping_folds_are_rejected(self) -> None:
        """Negative control: shared entities across folds must raise."""
        with pytest.raises(LeakageError, match="both train and test"):
            check_group_disjoint(pl.Series(["firm:c1:F1", "firm:c2:F2"]), pl.Series(["firm:c1:F1"]))

    def test_single_group_is_rejected(self) -> None:
        nodes, edges = loco_fixture()
        only_c1 = nodes.filter(pl.col("node_id").str.contains(":c1:"))
        with pytest.raises(ValueError, match=">= 2 groups"):
            list(loco_folds(only_c1, edges))
