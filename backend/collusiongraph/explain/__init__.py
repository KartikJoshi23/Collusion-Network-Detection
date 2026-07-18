"""Explanation layer (§4.4, §7 steps 17–19): explainer, matcher, red flags, bundles."""

from .bundles import ExplanationBundle, build_bundle, run_explanations
from .explainer_ablation import hard_fidelity, run_explainer_ablation
from .explainer_runner import NodeExplanation, explain_nodes
from .motif_matcher import MotifMatch, match_financial, match_motifs, match_procurement
from .pgexplainer_runner import explain_nodes_pg
from .redflags import load_indicators, map_red_flags

__all__ = [
    "ExplanationBundle",
    "MotifMatch",
    "NodeExplanation",
    "build_bundle",
    "explain_nodes",
    "explain_nodes_pg",
    "hard_fidelity",
    "load_indicators",
    "map_red_flags",
    "match_financial",
    "match_motifs",
    "match_procurement",
    "run_explainer_ablation",
    "run_explanations",
]
