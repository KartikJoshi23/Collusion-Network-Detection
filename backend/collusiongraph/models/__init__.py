"""GNN family, unsupervised arm, ensemble, roll-up, dedup (§4.4) + RQ1 baselines (§4.5)."""

from .baselines import (
    Rule,
    RulesEngine,
    neighbor_mean_features,
    screens_composite_scores,
    xgb_scores,
)

__all__ = [
    "Rule",
    "RulesEngine",
    "neighbor_mean_features",
    "screens_composite_scores",
    "xgb_scores",
]
