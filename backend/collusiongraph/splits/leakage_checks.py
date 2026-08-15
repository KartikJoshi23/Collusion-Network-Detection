"""Leakage assertions (§9.1 — highest priority: the tests that protect the paper).

These functions are called BOTH by the splitters at construction time (fail
fast in every pipeline run) and by the CI leakage suite. The ~39.5-F1 Elliptic
leakage result (arXiv:2604.19514) is the reason they exist: training-time
exposure to test-period adjacency silently inflates results.
"""

from __future__ import annotations

import polars as pl


class LeakageError(AssertionError):
    """A split violates the leakage-safety protocol (§4.5)."""


def check_no_future_nodes(
    train_nodes: pl.DataFrame, train_end: int, time_col: str = "time_first_seen"
) -> None:
    """Every training node must first appear at or before ``train_end``."""
    bad = train_nodes.filter(pl.col(time_col) > train_end)
    if bad.height:
        raise LeakageError(
            f"{bad.height} training nodes first appear after train_end={train_end} "
            f"(e.g. {bad['node_id'].head(3).to_list()})"
        )


def check_no_future_edge_timestamps(train_edges: pl.DataFrame, train_end: int) -> None:
    """No training edge may carry a timestamp after ``train_end``."""
    bad = train_edges.filter(pl.col("timestamp") > train_end)
    if bad.height:
        raise LeakageError(
            f"{bad.height} training edges are timestamped after train_end={train_end}"
        )


def check_train_edges_within_train_nodes(
    train_edges: pl.DataFrame, train_node_ids: pl.Series
) -> None:
    """Strict-inductive rule: training-time message passing is confined to the
    subgraph induced by train-period nodes — no train edge may touch any node
    outside the training node set (arXiv:2604.19514 protocol)."""
    ids = set(train_node_ids.to_list())
    bad = train_edges.filter(~pl.col("src").is_in(list(ids)) | ~pl.col("dst").is_in(list(ids)))
    if bad.height:
        example = bad.select("src", "dst").head(3).rows()
        raise LeakageError(
            f"{bad.height} training edges reach outside the training node set "
            f"(test-period adjacency exposure), e.g. {example}"
        )


def check_group_disjoint(train_node_ids: pl.Series, test_node_ids: pl.Series) -> None:
    """LOCO/LOMO rule: train and test folds share no entities (§9.1c)."""
    overlap = set(train_node_ids.to_list()) & set(test_node_ids.to_list())
    if overlap:
        raise LeakageError(
            f"{len(overlap)} entities appear in both train and test folds, "
            f"e.g. {sorted(overlap)[:3]}"
        )
