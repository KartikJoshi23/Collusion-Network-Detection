"""Investigator Copilot (§4.6, §7 step 27a) — ported from the archived
Gen-AI chatbot (`reference/genai-chatbot/`) and retargeted at the
CollusionGraph artifact store.

This first slice is the §4.6 cut-order core: the SQL agent's bounded
tool-calling loop + alert_tools over the serving artifacts, the deterministic
numeric-sanity gate, and the NEW guilt-language guard + caveat finaliser.
The full LangGraph orchestration (clarification, readback, cross-validation),
the RAG agent over `data/corpus/`, and the goldens gate follow in the next
slices (27b/27c).
"""

from .agent import answer_question
from .guard import RED_FLAG_LEXICON, apply_guilt_guard, numeric_sanity_gate

__all__ = [
    "RED_FLAG_LEXICON",
    "answer_question",
    "apply_guilt_guard",
    "numeric_sanity_gate",
]
