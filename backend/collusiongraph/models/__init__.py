"""GNN family, roll-up, calibration (§4.4) + RQ1 baselines (§4.5)."""

from .baselines import (
    Rule,
    RulesEngine,
    neighbor_mean_features,
    screens_composite_scores,
    xgb_scores,
)
from .gnn import RGCN, GATv2, GraphSAGE, make_model
from .rollup import community_scores, isotonic_calibrator, leiden_communities

__all__ = [
    "RGCN",
    "GATv2",
    "GraphSAGE",
    "Rule",
    "RulesEngine",
    "community_scores",
    "isotonic_calibrator",
    "leiden_communities",
    "make_model",
    "neighbor_mean_features",
    "screens_composite_scores",
    "xgb_scores",
]
