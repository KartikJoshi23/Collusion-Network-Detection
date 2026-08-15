"""
Read-back — fires on complex queries before execution.

Produces a one-sentence paraphrase of the resolved interpretation, then yields
via `interrupt()` so the UI can render a confirm/adjust card. When the user
approves, the graph resumes and executes. When the user rejects or edits, the
graph re-enters the Intent Classifier with the correction folded into the
enriched query.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import interrupt

from app.graph.prompts import READBACK_SYSTEM
from app.graph.state import AgentState
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)


def is_complex_query(state: AgentState) -> bool:
    """Trigger read-back when intent ops include a JOIN, aggregate, rank, multi-filter, or time-range."""
    intent = state.get("intent") or {}
    ops = [str(o).lower() for o in (intent.get("ops") or [])]
    if any(op.startswith(("join:", "aggregate:", "rank:", "group_by:", "window:")) for op in ops):
        return True
    filters = [op for op in ops if op.startswith("filter:")]
    if len(filters) >= 2:
        return True
    if any("date" in op or "period" in op or "quarter" in op or "year" in op for op in ops):
        return True
    return False


def readback_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    user_msg = (
        f"User question: {state['user_query']}\n\n"
        f"Resolved intent:\n```json\n{__import__('json').dumps(state.get('intent') or {}, indent=2)}\n```\n\n"
        "Produce the one-sentence read-back confirmation now."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": READBACK_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
    )
    text = (resp.choices[0].message.content or "").strip()
    logger.info("Read-back: %s", text)

    user_response: Any = interrupt({"readback": text})
    # Expected shape from HTTP layer: {"approved": bool, "adjustment": str | None}
    approved = bool(user_response.get("approved")) if isinstance(user_response, dict) else True
    adjustment = (user_response.get("adjustment") if isinstance(user_response, dict) else None) or None

    trace = state.get("trace", []) + [f"readback -> {'approved' if approved else 'adjust'}"]

    updates: dict = {
        "readback_text": text,
        "readback_approved": approved,
        "trace": trace,
    }
    if not approved and adjustment:
        updates["enriched_query"] = f"{state.get('enriched_query') or state['user_query']}\n\nCorrection: {adjustment}"
    return updates
