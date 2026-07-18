"""Evaluation harness (§4.5) — the single source of truth for paper numbers.

Metrics (P@k, AUC-PR, FPR/Recall@budget), the alert unit (hit rule + NMS
dedup), and config-driven runs; transfer matrices and bootstrap CIs join in
their roadmap weeks (§7 steps 20, 29).
"""

from .alert_unit import (
    DEFAULT_JACCARD_THRESHOLD,
    DEFAULT_MAX_MEMBERS,
    DedupResult,
    apply_hit_rule,
    jaccard,
    nms_dedup,
)
from .metrics import (
    alert_queue_metrics,
    auc_pr,
    confirmed_node_vectors,
    fpr_at_k,
    illicit_coverage_at_budget,
    precision_at_k,
    recall_at_k,
)
from .report import DEFAULT_BUDGETS, load_config, resolve_budgets, run_eval

__all__ = [
    "DEFAULT_BUDGETS",
    "DEFAULT_JACCARD_THRESHOLD",
    "DEFAULT_MAX_MEMBERS",
    "DedupResult",
    "alert_queue_metrics",
    "apply_hit_rule",
    "auc_pr",
    "confirmed_node_vectors",
    "fpr_at_k",
    "illicit_coverage_at_budget",
    "jaccard",
    "load_config",
    "nms_dedup",
    "precision_at_k",
    "recall_at_k",
    "resolve_budgets",
    "run_eval",
]
