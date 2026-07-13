"""Planner — fires on hybrid route only. Decomposes query into ordered sub-questions."""

from __future__ import annotations

import json
import logging

from app.data.facts import format_facts_for_text
from app.graph.agents._utils import parse_json_response
from app.graph.prompts import PLANNER_SYSTEM
from app.graph.state import AgentState, SubQuestion
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)


def planner_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()
    query = state.get("enriched_query") or state["user_query"]

    facts_block = format_facts_for_text(query, max_facts=20)
    user_msg = (
        f"User question: {query}\n\n"
        f"Structured intent:\n```json\n{json.dumps(state.get('intent') or {}, indent=2)}\n```\n\n"
        f"RELEVANT PRE-EXTRACTED FACTS (you MUST decide which of these are in-scope for\n"
        f"the question and produce sub-questions that make use of them; do NOT invent a\n"
        f"RAG sub-question to re-retrieve a fact that's already listed here — instead\n"
        f"pass the fact ID through to downstream agents):\n\n{facts_block}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    payload = parse_json_response(resp.choices[0].message.content or "", context="planner")

    raw_subs = payload.get("sub_questions", []) or []
    sub_questions: list[SubQuestion] = []
    for s in raw_subs:
        qtype = str(s.get("type", "")).lower()
        if qtype not in {"sql", "rag"}:
            continue
        sub_questions.append(
            SubQuestion(type=qtype, question=str(s.get("question", "")).strip())  # type: ignore[typeddict-item]
        )
    if not sub_questions:
        # Fallback: treat the whole query as a single SQL sub-question.
        sub_questions = [SubQuestion(type="sql", question=query)]  # type: ignore[typeddict-item]

    logger.info("Planner -> %s sub-questions", len(sub_questions))
    trace = state.get("trace", []) + [f"planner -> {len(sub_questions)} sub-qs"]
    return {"sub_questions": sub_questions, "trace": trace}
