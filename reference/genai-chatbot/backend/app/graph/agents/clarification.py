"""
Clarification Agent.

Fires when the Intent Classifier reports a low clarity_score or a high-severity
ambiguity. Picks the SINGLE highest-severity ambiguity and generates one
targeted question (multiple-choice where feasible). Control then yields via
LangGraph's `interrupt()` — the HTTP layer surfaces the question to the user
and re-enters the graph with the answer.
"""

from __future__ import annotations

import json
import logging

from langgraph.types import interrupt

from app.graph.agents._utils import parse_json_response
from app.graph.prompts import CLARIFICATION_SYSTEM
from app.graph.state import AgentState, ClarificationTurn
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3
CLARITY_THRESHOLD = 0.7
SEVERITY_THRESHOLD = 0.8


def needs_clarification(state: AgentState) -> bool:
    """Rule evaluated by the graph router edge."""
    intent = state.get("intent") or {}
    route = state.get("route")
    if route == "clarify":
        return True

    rounds = state.get("clarification_rounds", 0)
    if rounds >= MAX_ROUNDS:
        return False

    clarity = float(intent.get("clarity_score", 1.0))
    if clarity < CLARITY_THRESHOLD:
        return True

    ambiguities = intent.get("ambiguities") or []
    return any(float(a.get("severity", 0.0)) >= SEVERITY_THRESHOLD for a in ambiguities)


def clarification_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()
    intent = state.get("intent") or {}
    query = state.get("enriched_query") or state["user_query"]
    turns = state.get("clarification_turns", []) or []

    already_asked = "\n".join(f"- {t['question']} → {t.get('user_answer') or '(no answer)'}" for t in turns)
    user_msg = (
        f"Original user question: {state['user_query']}\n\n"
        f"Current enriched form: {query}\n\n"
        f"Intent so far:\n```json\n{json.dumps(intent, indent=2)}\n```\n\n"
        f"Previous clarification rounds:\n{already_asked or '(none)'}\n\n"
        "Pick the single most impactful ambiguity and ask one question."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CLARIFICATION_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    payload = parse_json_response(resp.choices[0].message.content or "", context="clarification")
    question = str(payload.get("question", "")).strip() or "Could you clarify what you meant?"
    options = payload.get("options") or []

    # Hand off to the HTTP layer. `interrupt()` serialises the value, pauses
    # the graph, and when the graph is resumed with a user answer it resumes
    # execution here — `interrupt()` returns that answer.
    user_answer: str = interrupt({
        "question": question,
        "options": options,
        "round": state.get("clarification_rounds", 0) + 1,
    })

    new_turn: ClarificationTurn = {"question": question, "user_answer": user_answer}
    new_rounds = state.get("clarification_rounds", 0) + 1
    new_enriched = f"{query}\n\nClarification Q: {question}\nClarification A: {user_answer}"

    logger.info("Clarification round %s: Q=%r A=%r", new_rounds, question, user_answer)
    trace = state.get("trace", []) + [f"clarify r{new_rounds}"]

    return {
        "pending_clarification": None,
        "clarification_turns": turns + [new_turn],
        "clarification_rounds": new_rounds,
        "enriched_query": new_enriched,
        "trace": trace,
    }
