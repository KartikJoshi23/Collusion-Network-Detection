"""
Completeness Checker — fires after Synthesiser / Cross-Validator / Arbiter,
right before Finaliser. Compares the draft answer against the pre-extracted
fact catalog to detect recall misses (facts whose categories match the
question but which aren't referenced in the draft). If any material fact is
missing, loops back through the Synthesiser with those facts forcibly in
context.

State additions:
  completeness_retry_used: int  — caps at 1 to prevent loops
  completeness_verdict: dict
  missing_facts: list[dict]
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.data.facts import Fact, format_facts_block, load_facts_for_text
from app.graph.agents._utils import parse_json_response
from app.graph.prompts import COMPLETENESS_CHECKER_SYSTEM
from app.graph.state import AgentState
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)

MAX_RETRIES = 1  # one regen round, then give up — keeps latency bounded


def should_check_completeness(state: AgentState) -> bool:
    """Skip if already retried, or if the draft is empty, or if no facts match."""
    if state.get("completeness_retry_used", 0) >= MAX_RETRIES:
        return False
    if not (state.get("draft_answer") or "").strip():
        return False
    # Only bother checking when there ARE facts to check against
    return bool(load_facts_for_text(state.get("user_query", ""), max_facts=20))


def completeness_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    facts = load_facts_for_text(state["user_query"], max_facts=20)
    facts_block = format_facts_block(facts)

    user_block = (
        f"User question: {state['user_query']}\n\n"
        f"Draft answer:\n{state.get('draft_answer', '')}\n\n"
        f"Pre-extracted candidate facts:\n{facts_block}\n\n"
        "Identify any facts that are RELEVANT to the question but MISSING "
        "from the draft. Return the JSON per the system instructions."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": COMPLETENESS_CHECKER_SYSTEM},
            {"role": "user", "content": user_block},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        payload = parse_json_response(resp.choices[0].message.content or "", context="completeness")
    except ValueError:
        payload = {"missing_facts": [], "verdict": "pass"}

    verdict = str(payload.get("verdict", "pass")).lower()
    missing = payload.get("missing_facts") or []
    if verdict not in {"pass", "retry"}:
        verdict = "pass"

    logger.info("Completeness -> %s, %d missing facts", verdict, len(missing))

    trace = state.get("trace", []) + [
        f"completeness -> {verdict} ({len(missing)} missing)"
    ]

    return {
        "completeness_verdict": {"verdict": verdict, "missing_facts": missing},
        "trace": trace,
    }


def _fact_by_id(all_facts: list[Fact], fact_id: str) -> Fact | None:
    for f in all_facts:
        if f.id == fact_id:
            return f
    return None


def completeness_reground_node(state: AgentState) -> dict:
    """If completeness flagged missing facts, regenerate the draft with those
    facts forcibly appended to the context. One shot, no loop."""
    from app.graph.agents.synthesiser import synthesiser_node

    verdict = state.get("completeness_verdict") or {}
    missing_raw = verdict.get("missing_facts") or []

    # Resolve fact IDs to full facts
    all_facts = load_facts_for_text(state["user_query"], max_facts=20)
    missing_ids = [m.get("id") for m in missing_raw if m.get("id")]
    missing_facts: list[Fact] = [f for f in all_facts if f.id in missing_ids]

    if not missing_facts:
        logger.info("Completeness reground invoked with no resolvable missing facts; passthrough.")
        return {"completeness_retry_used": state.get("completeness_retry_used", 0) + 1}

    # Re-run Synthesiser with the draft + missing-facts hint appended to the
    # most recent sub-result. This keeps the existing sub-results intact.
    missing_block = "\n".join(f"- {f.as_prompt_line()}" for f in missing_facts)
    hint_result = {
        "type": "rag",
        "question": "Missing policy / strategic context surfaced by the Completeness Checker",
        "answer": "The original draft did NOT reference the following facts. Weave them into the final answer where relevant, with inline [fact-id] tags.\n\n" + missing_block,
    }
    state_with_hint: AgentState = dict(state)  # type: ignore[assignment]
    current_subs = list(state.get("hybrid_sub_results") or [])
    state_with_hint["hybrid_sub_results"] = current_subs + [hint_result]

    updates = synthesiser_node(state_with_hint)
    updates["completeness_retry_used"] = state.get("completeness_retry_used", 0) + 1
    trace = updates.get("trace", state.get("trace", [])) + [
        f"completeness_reground -> added {len(missing_facts)} fact(s)"
    ]
    updates["trace"] = trace
    return updates
