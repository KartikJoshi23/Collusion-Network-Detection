"""Line-graph flow channel (§7 step 26a): hand-computed geometry on toy
graphs, the walk-semantics conventions (self-loops, multi-edges, quorum
nulls), §9.1b as-of discipline, and trainer family registration."""

import polars as pl
import pytest
from collusiongraph.features import line_graph_features, structural_features
from collusiongraph.training.trainer import _one_family


def _frames(node_ids, edge_pairs, node_times=None, edge_times=None):
    nodes = pl.DataFrame(
        {
            "node_id": node_ids,
            "time_first_seen": node_times if node_times is not None else [1] * len(node_ids),
        }
    )
    edges = pl.DataFrame(
        {
            "src": [s for s, _ in edge_pairs],
            "dst": [d for _, d in edge_pairs],
            "timestamp": edge_times if edge_times is not None else [1] * len(edge_pairs),
            "directed": [True] * len(edge_pairs),
        },
        schema_overrides={"src": pl.Utf8, "dst": pl.Utf8, "directed": pl.Boolean},
    )
    return nodes, edges


def _row(frame: pl.DataFrame, node_id: str) -> dict:
    return frame.filter(pl.col("node_id") == node_id).to_dicts()[0]


class TestGeometry:
    def test_chain_hand_computed(self) -> None:
        """a→b→c: b passes one 2-walk through; a and c pass none."""
        out = line_graph_features(*_frames(["a", "b", "c"], [("a", "b"), ("b", "c")]))
        b = _row(out, "b")
        assert b["lg_through_count"] == 1.0
        assert b["lg_pass_ratio"] == pytest.approx(0.5)  # 1 / (1+1)
        # b's in-edge (a→b): in_deg(a)=0; b's out-edge (b→c): out_deg(c)=0
        assert b["lg_upstream_fan_mean"] == 0.0
        assert b["lg_downstream_fan_max"] == 0.0
        a = _row(out, "a")
        assert a["lg_through_count"] == 0.0
        # a has no in-edges: upstream aggregates are null (quorum rule), not 0
        assert a["lg_upstream_fan_mean"] is None
        # a's out-edge (a→b): out_deg(b)=1
        assert a["lg_downstream_fan_mean"] == 1.0

    def test_fan_in_hub_hand_computed(self) -> None:
        """u1,u2,u3→h→w: 3 two-walks pass through h; each ui sees h's out-fan."""
        pairs = [("u1", "h"), ("u2", "h"), ("u3", "h"), ("h", "w")]
        out = line_graph_features(*_frames(["u1", "u2", "u3", "h", "w"], pairs))
        h = _row(out, "h")
        assert h["lg_through_count"] == 3.0  # in 3 × out 1
        assert h["lg_pass_ratio"] == pytest.approx(3 / 4)
        u1 = _row(out, "u1")
        assert u1["lg_downstream_fan_mean"] == 1.0  # out_deg(h)=1
        w = _row(out, "w")
        assert w["lg_through_count"] == 0.0
        assert w["lg_upstream_fan_max"] == 3.0  # in-edge (h→w): in_deg(h)=3

    def test_two_cycle_and_multi_edge(self) -> None:
        """a⇄b: each node passes one 2-walk (the bounce-back is a real walk);
        a parallel duplicate edge counts with multiplicity."""
        out = line_graph_features(*_frames(["a", "b"], [("a", "b"), ("b", "a")]))
        assert _row(out, "a")["lg_through_count"] == 1.0
        assert _row(out, "a")["lg_upstream_fan_mean"] == 1.0  # in-edge (b→a): in_deg(b)=1

        multi = line_graph_features(*_frames(["a", "b", "c"], [("a", "b"), ("a", "b"), ("b", "c")]))
        b = _row(multi, "b")
        assert b["lg_through_count"] == 2.0  # in 2 (parallel) × out 1

    def test_self_loop_is_not_a_walk_continuation(self) -> None:
        with_loop = line_graph_features(*_frames(["a", "b"], [("a", "a"), ("a", "b")]))
        without = line_graph_features(*_frames(["a", "b"], [("a", "b")]))
        assert with_loop.sort("node_id").equals(without.sort("node_id"))

    def test_empty_graph_keeps_schema(self) -> None:
        out = line_graph_features(*_frames(["a", "b"], []))
        assert out["lg_through_count"].to_list() == [0.0, 0.0]
        assert out["lg_upstream_fan_mean"].to_list() == [None, None]


class TestAsOfDiscipline:  # §9.1b
    def test_as_of_equals_truncated_graph(self) -> None:
        nodes, edges = _frames(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c")],
            node_times=[1, 1, 1],
            edge_times=[1, 5],
        )
        as_of = line_graph_features(nodes, edges, as_of=2)
        truncated = line_graph_features(nodes, edges.filter(pl.col("timestamp") <= 2))
        assert as_of.sort("node_id").equals(truncated.sort("node_id"))

    def test_future_and_undated_edges_cannot_leak(self) -> None:
        """Negative control: adding a future edge and an undated edge changes
        nothing under as_of (undated edges cannot be proven past — excluded)."""
        nodes, edges = _frames(["a", "b", "c"], [("a", "b")])
        poison = pl.DataFrame(
            {
                "src": ["b", "c"],
                "dst": ["c", "a"],
                "timestamp": [9, None],
                "directed": [True, True],
            },
            schema=edges.schema,
        )
        poisoned = pl.concat([edges, poison])
        assert (
            line_graph_features(nodes, edges, as_of=1)
            .sort("node_id")
            .equals(line_graph_features(nodes, poisoned, as_of=1).sort("node_id"))
        )


class TestFamilyRegistration:
    def test_line_family_resolves_and_does_not_clash_with_structural(self) -> None:
        nodes, edges = _frames(["a", "b", "c"], [("a", "b"), ("b", "c")])
        fam = _one_family("line", nodes, edges, None, 0)
        assert "lg_through_count" in fam.columns
        structural = structural_features(nodes, edges)
        clash = (set(fam.columns) & set(structural.columns)) - {"node_id"}
        assert clash == set()  # the trainer's span tracking relies on this

    def test_unknown_family_still_rejected(self) -> None:
        nodes, edges = _frames(["a"], [])
        with pytest.raises(ValueError, match="unknown feature kind"):
            _one_family("cosmic", nodes, edges, None, 0)
