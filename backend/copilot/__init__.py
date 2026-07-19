"""Investigator Copilot (§4.6, §7 step 27a) — ported from the archived
Gen-AI chatbot (`reference/genai-chatbot/`) and retargeted at the
CollusionGraph artifact store.

This first slice is the §4.6 cut-order core: the SQL agent's bounded
tool-calling loop + alert_tools over the serving artifacts, the deterministic
numeric-sanity gate, and the NEW guilt-language guard + caveat finaliser.

Re-exports are LAZY (PEP 562): the serving app mounts ``copilot.api`` inside
``create_app``, and the torch-free deployment image (docs/deployment.md §2)
must be able to import this package without dragging in the agent's tool
stack at import time (2026-07-19 audit finding — the eager import chain
reached torch via collusiongraph.explain and killed the slim container)."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover — typing only, never at runtime
    from .agent import answer_question as answer_question
    from .guard import RED_FLAG_LEXICON as RED_FLAG_LEXICON
    from .guard import apply_guilt_guard as apply_guilt_guard
    from .guard import numeric_sanity_gate as numeric_sanity_gate

_EXPORTS = {
    "answer_question": ("copilot.agent", "answer_question"),
    "RED_FLAG_LEXICON": ("copilot.guard", "RED_FLAG_LEXICON"),
    "apply_guilt_guard": ("copilot.guard", "apply_guilt_guard"),
    "numeric_sanity_gate": ("copilot.guard", "numeric_sanity_gate"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        import importlib

        module, attr = _EXPORTS[name]
        return getattr(importlib.import_module(module), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
