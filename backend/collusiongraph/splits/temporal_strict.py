"""Strict-inductive temporal splitter (§4.3 D1, §4.5, arXiv:2604.19514).

Semantics (Elliptic convention: train time steps 1–34, test 35–49):

* **train nodes** — ``time_first_seen <= train_end``
* **test nodes**  — ``time_first_seen >= test_start`` (default ``train_end + 1``)
* **train edges** — both endpoints are train nodes AND the edge timestamp is
  ``<= train_end``: training-time message passing sees only the train-induced
  subgraph. This is the strict-inductive protocol; violating it inflated
  Elliptic F1 by ~39.5 points in controlled re-evaluation.
* **inference edges** — all edges among placed nodes (train ∪ test); at test
  time the model may see the graph as it exists then. Metrics are computed on
  test nodes only.

Nodes with null time cannot be placed on a timeline and are excluded from both
sides (counted in the report). An optional ``fence_after`` drops everything
strictly after it — built for AMLworld's post-window tail, which is 59.1%
laundering (measured in EDA notebook 05) and would corrupt any temporal test
period that includes it.

Every constructed split runs the §9.1 leakage checks — a violating split
cannot be instantiated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from .leakage_checks import (
    check_group_disjoint,
    check_no_future_edge_timestamps,
    check_no_future_nodes,
    check_train_edges_within_train_nodes,
)


@dataclass(frozen=True)
class StrictTemporalSplit:
    train_nodes: pl.DataFrame
    test_nodes: pl.DataFrame
    train_edges: pl.DataFrame
    inference_edges: pl.DataFrame
    report: dict = field(default_factory=dict)


def strict_temporal_split(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    train_end: int,
    test_start: int | None = None,
    fence_after: int | None = None,
    time_col: str = "time_first_seen",
) -> StrictTemporalSplit:
    if test_start is None:
        test_start = train_end + 1
    if test_start <= train_end:
        raise ValueError(f"test_start ({test_start}) must be after train_end ({train_end})")

    n_fenced_nodes = n_fenced_edges = 0
    if fence_after is not None:
        before_n, before_e = nodes.height, edges.height
        nodes = nodes.filter(pl.col(time_col) <= fence_after)
        kept = nodes["node_id"].implode()
        edges = edges.filter(
            (pl.col("timestamp") <= fence_after)
            & pl.col("src").is_in(kept)
            & pl.col("dst").is_in(kept)
        )
        n_fenced_nodes, n_fenced_edges = before_n - nodes.height, before_e - edges.height

    unplaced = nodes.filter(pl.col(time_col).is_null())
    placed = nodes.filter(pl.col(time_col).is_not_null())

    train_nodes = placed.filter(pl.col(time_col) <= train_end)
    test_nodes = placed.filter(pl.col(time_col) >= test_start)

    train_ids = train_nodes["node_id"]
    train_ids_set = train_ids.implode()
    train_edges = edges.filter(
        pl.col("src").is_in(train_ids_set)
        & pl.col("dst").is_in(train_ids_set)
        & (pl.col("timestamp").is_null() | (pl.col("timestamp") <= train_end))
    )
    placed_ids = placed["node_id"].implode()
    inference_edges = edges.filter(
        pl.col("src").is_in(placed_ids) & pl.col("dst").is_in(placed_ids)
    )

    # §9.1 — a leaky split must be unconstructable, not merely discouraged.
    check_no_future_nodes(train_nodes, train_end, time_col)
    check_no_future_edge_timestamps(
        train_edges.filter(pl.col("timestamp").is_not_null()), train_end
    )
    check_train_edges_within_train_nodes(train_edges, train_ids)
    check_group_disjoint(train_ids, test_nodes["node_id"])

    report = {
        "train_end": train_end,
        "test_start": test_start,
        "fence_after": fence_after,
        "n_train_nodes": train_nodes.height,
        "n_test_nodes": test_nodes.height,
        "n_gap_nodes": placed.height - train_nodes.height - test_nodes.height,
        "n_unplaced_nodes": unplaced.height,
        "n_train_edges": train_edges.height,
        "n_inference_edges": inference_edges.height,
        "n_fenced_nodes": n_fenced_nodes,
        "n_fenced_edges": n_fenced_edges,
    }
    return StrictTemporalSplit(train_nodes, test_nodes, train_edges, inference_edges, report)
