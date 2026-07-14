"""Leave-one-country-out / leave-one-market-out folds (§4.3 D3/D4, §4.5).

IR node ids embed their group as the second ``:``-separated segment
(``firm:country_1:F1``, ``tender:Japan:T1``), so grouping needs no side table.
Cross-group edges are excluded from BOTH sides of every fold (they would let
message passing bridge train and test); by construction Mendeley and García
have none, but the splitter never assumes that.

Every fold runs the §9.1 entity-disjointness check at construction.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import polars as pl

from .leakage_checks import check_group_disjoint

GROUP_FROM_NODE_ID = pl.col("node_id").str.split(":").list.get(1)


@dataclass(frozen=True)
class LocoFold:
    test_group: str
    train_nodes: pl.DataFrame
    test_nodes: pl.DataFrame
    train_edges: pl.DataFrame
    test_edges: pl.DataFrame
    report: dict = field(default_factory=dict)


def loco_folds(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    group_expr: pl.Expr = GROUP_FROM_NODE_ID,
) -> Iterator[LocoFold]:
    """Yield one fold per group, oldest-to-newest group name order."""
    grouped = nodes.with_columns(group_expr.alias("_group"))
    groups = sorted(grouped["_group"].unique().to_list())
    if len(groups) < 2:
        raise ValueError(f"LOCO needs >= 2 groups, found {groups}")

    node_group = grouped.select("node_id", "_group")
    edges_g = edges.join(
        node_group.rename({"node_id": "src", "_group": "_src_group"}), on="src"
    ).join(node_group.rename({"node_id": "dst", "_group": "_dst_group"}), on="dst")
    cross_group = edges_g.filter(pl.col("_src_group") != pl.col("_dst_group"))

    for test_group in groups:
        train_nodes = grouped.filter(pl.col("_group") != test_group).drop("_group")
        test_nodes = grouped.filter(pl.col("_group") == test_group).drop("_group")
        within = edges_g.filter(pl.col("_src_group") == pl.col("_dst_group"))
        train_edges = within.filter(pl.col("_src_group") != test_group).drop(
            "_src_group", "_dst_group"
        )
        test_edges = within.filter(pl.col("_src_group") == test_group).drop(
            "_src_group", "_dst_group"
        )

        check_group_disjoint(train_nodes["node_id"], test_nodes["node_id"])

        yield LocoFold(
            test_group=test_group,
            train_nodes=train_nodes,
            test_nodes=test_nodes,
            train_edges=train_edges,
            test_edges=test_edges,
            report={
                "test_group": test_group,
                "n_groups": len(groups),
                "n_train_nodes": train_nodes.height,
                "n_test_nodes": test_nodes.height,
                "n_train_edges": train_edges.height,
                "n_test_edges": test_edges.height,
                "n_cross_group_edges_excluded": cross_group.height,
            },
        )
