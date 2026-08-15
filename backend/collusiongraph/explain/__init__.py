"""Explanation layer (§4.4, §7 steps 17–19): explainer, matcher, red flags, bundles.

Re-exports are LAZY (PEP 562): the torch-free serving path reaches
``load_indicators`` through this package (copilot corpus → FATF/OECD tables),
and eager imports here dragged torch in via the explainer runners — killing
the slim deployment container (2026-07-19 audit finding). Attribute access
is unchanged for every consumer; only import *timing* moved."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover — typing only, never at runtime
    from .bundles import ExplanationBundle as ExplanationBundle
    from .bundles import build_bundle as build_bundle
    from .bundles import run_explanations as run_explanations
    from .explainer_ablation import hard_fidelity as hard_fidelity
    from .explainer_ablation import run_explainer_ablation as run_explainer_ablation
    from .explainer_runner import NodeExplanation as NodeExplanation
    from .explainer_runner import explain_nodes as explain_nodes
    from .motif_matcher import MotifMatch as MotifMatch
    from .motif_matcher import match_financial as match_financial
    from .motif_matcher import match_motifs as match_motifs
    from .motif_matcher import match_procurement as match_procurement
    from .pgexplainer_runner import explain_nodes_pg as explain_nodes_pg
    from .redflags import load_indicators as load_indicators
    from .redflags import map_red_flags as map_red_flags

_P = "collusiongraph.explain"
_EXPORTS = {
    "ExplanationBundle": (f"{_P}.bundles", "ExplanationBundle"),
    "build_bundle": (f"{_P}.bundles", "build_bundle"),
    "run_explanations": (f"{_P}.bundles", "run_explanations"),
    "hard_fidelity": (f"{_P}.explainer_ablation", "hard_fidelity"),
    "run_explainer_ablation": (f"{_P}.explainer_ablation", "run_explainer_ablation"),
    "NodeExplanation": (f"{_P}.explainer_runner", "NodeExplanation"),
    "explain_nodes": (f"{_P}.explainer_runner", "explain_nodes"),
    "MotifMatch": (f"{_P}.motif_matcher", "MotifMatch"),
    "match_financial": (f"{_P}.motif_matcher", "match_financial"),
    "match_motifs": (f"{_P}.motif_matcher", "match_motifs"),
    "match_procurement": (f"{_P}.motif_matcher", "match_procurement"),
    "explain_nodes_pg": (f"{_P}.pgexplainer_runner", "explain_nodes_pg"),
    "load_indicators": (f"{_P}.redflags", "load_indicators"),
    "map_red_flags": (f"{_P}.redflags", "map_red_flags"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        import importlib

        module, attr = _EXPORTS[name]
        return getattr(importlib.import_module(module), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
