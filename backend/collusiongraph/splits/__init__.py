"""Strict-inductive temporal / LOCO / LOMO splitters + leakage checks (§4.3, §9.1)."""

from .leakage_checks import (
    LeakageError,
    check_group_disjoint,
    check_no_future_edge_timestamps,
    check_no_future_nodes,
    check_train_edges_within_train_nodes,
)
from .loco import GROUP_FROM_NODE_ID, LocoFold, loco_folds
from .temporal_strict import StrictTemporalSplit, strict_temporal_split

__all__ = [
    "GROUP_FROM_NODE_ID",
    "LeakageError",
    "LocoFold",
    "StrictTemporalSplit",
    "check_group_disjoint",
    "check_no_future_edge_timestamps",
    "check_no_future_nodes",
    "check_train_edges_within_train_nodes",
    "loco_folds",
    "strict_temporal_split",
]
