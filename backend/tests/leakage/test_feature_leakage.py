"""As-of feature leakage tests (§9.1b): no feature computed with future information.

The invariant: computing features on the FULL graph with ``as_of=T`` must equal
computing them on the graph truncated at T — i.e. the future is provably
invisible, not merely down-weighted. Negative controls prove the ``as_of``
parameter actually bites (a check that cannot fail protects nothing).
"""

import polars as pl
import pytest
from collusiongraph.features import (
    award_screens,
    bid_screens,
    financial_features,
    restrict_as_of,
    structural_features,
)

pytestmark = pytest.mark.leakage

AS_OF = 5


def temporal_graph() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Past core a-b-c (t<=5); future node f and future/undated edges beyond it."""
    nodes = pl.DataFrame(
        {
            "node_id": ["a", "b", "c", "f", "u"],
            "time_first_seen": [1, 2, 3, 8, None],
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["a", "b", "a", "c", "f", "a"],
            "dst": ["b", "c", "c", "f", "a", "u"],
            "timestamp": [2, 3, 4, 8, 9, None],
            "amount": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            "edge_type": ["pays"] * 6,
            "directed": [True] * 6,
        }
    )
    return nodes, edges


def truncated() -> tuple[pl.DataFrame, pl.DataFrame]:
    """The graph as it truly existed at AS_OF (ground truth for equivalence)."""
    nodes, edges = temporal_graph()
    return restrict_as_of(nodes, edges, AS_OF)


class TestAsOfEquivalence:
    """features(full graph, as_of=T) == features(graph truncated at T)."""

    def test_structural(self) -> None:
        nodes, edges = temporal_graph()
        t_nodes, t_edges = truncated()
        assert structural_features(nodes, edges, as_of=AS_OF).equals(
            structural_features(t_nodes, t_edges)
        )

    def test_financial(self) -> None:
        nodes, edges = temporal_graph()
        t_nodes, t_edges = truncated()
        assert financial_features(nodes, edges, as_of=AS_OF).equals(
            financial_features(t_nodes, t_edges)
        )

    def test_screens(self) -> None:
        nodes = pl.DataFrame(
            {
                "node_id": ["firm:M:F1", "firm:M:F2", "tender:M:T1", "tender:M:T2", "buyer:M:B1"],
                "time_first_seen": [2010, 2010, 2010, 2020, 2010],
            }
        )
        edges = pl.DataFrame(
            {
                "src": ["tender:M:T1", "tender:M:T2", "buyer:M:B1", "firm:M:F1", "firm:M:F2"],
                "dst": ["firm:M:F1", "firm:M:F2", "tender:M:T1", "tender:M:T1", "tender:M:T1"],
                "edge_type": ["awarded", "awarded", "buys_from", "bids_on", "bids_on"],
                "timestamp": [2010, 2020, 2010, 2010, 2010],
                "amount": [None, None, None, 100.0, 110.0],
                "directed": [True] * 5,
            }
        )
        as_of = 2015
        t_nodes, t_edges = restrict_as_of(nodes, edges, as_of)
        assert award_screens(nodes, edges, as_of=as_of).equals(award_screens(t_nodes, t_edges))
        assert bid_screens(nodes, edges, as_of=as_of).equals(bid_screens(t_nodes, t_edges))
        # negative control: the 2020 award changes F2's screens when visible
        assert not award_screens(nodes, edges).equals(award_screens(t_nodes, t_edges))


class TestFutureIsInvisible:
    def test_future_nodes_absent_from_output(self) -> None:
        nodes, edges = temporal_graph()
        feats = structural_features(nodes, edges, as_of=AS_OF)
        assert "f" not in feats["node_id"].to_list()

    def test_negative_control_no_as_of_sees_the_future(self) -> None:
        """Without as_of the future edges DO change the numbers — proving the
        equivalence tests above cannot pass vacuously."""
        nodes, edges = temporal_graph()
        t_nodes, t_edges = truncated()
        assert not structural_features(nodes, edges).equals(structural_features(t_nodes, t_edges))
        assert not financial_features(nodes, edges).equals(financial_features(t_nodes, t_edges))

    def test_future_edge_does_not_leak_into_past_node_features(self) -> None:
        """a participates in a future edge (f->a at t=9): a's as-of features must
        match a world where that edge never happens."""
        nodes, edges = temporal_graph()
        without_future_edge = edges.filter(~((pl.col("src") == "f") & (pl.col("dst") == "a")))
        with_f = structural_features(nodes, edges, as_of=AS_OF)
        without_f = structural_features(nodes, without_future_edge, as_of=AS_OF)
        assert with_f.equals(without_f)

    def test_undated_edges_are_excluded_under_as_of(self) -> None:
        """An edge with a null timestamp cannot be proven past — under as-of it
        must not contribute (a->u exists only undated)."""
        nodes, edges = temporal_graph()
        feats = structural_features(nodes, edges, as_of=AS_OF).sort("node_id")
        u_row = feats.filter(pl.col("node_id") == "u")
        assert u_row["degree_total"].to_list() == [0]

    def test_undated_edges_do_count_without_as_of(self) -> None:
        """as_of=None is the LOCO/LOMO regime where undated data (García Italy)
        stays usable — the exclusion above is an as-of rule, not a data drop."""
        nodes, edges = temporal_graph()
        feats = structural_features(nodes, edges).sort("node_id")
        u_row = feats.filter(pl.col("node_id") == "u")
        assert u_row["degree_total"].to_list() == [1]
