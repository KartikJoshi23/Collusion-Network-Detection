"""Synthesiser — merges hybrid sub-answers into one coherent final answer."""

from __future__ import annotations

import json
import logging

from app.data.facts import format_facts_for_text
from app.graph.prompts import SYNTHESISER_SYSTEM
from app.graph.state import AgentState
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)


def _format_sub_results(results: list[dict]) -> str:
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(f"### Sub-answer {i} ({r.get('type', 'unknown')}) — {r.get('question', '')}")
        lines.append(r.get("answer") or "(empty)")
        if r.get("sql_result") and r["sql_result"].get("sql"):
            lines.append("```sql\n" + r["sql_result"]["sql"] + "\n```")
        if r.get("rag_result") and r["rag_result"].get("citations"):
            cits = ", ".join(f"[{c.get('chunk_id')}]" for c in r["rag_result"]["citations"])
            lines.append(f"Citations: {cits}")
        lines.append("")
    return "\n".join(lines)


def synthesiser_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    results = state.get("hybrid_sub_results") or []
    if not results:
        logger.warning("Synthesiser called with no sub-results; passing through draft answer.")
        return {"draft_answer": state.get("draft_answer", "(no sub-results)")}

    facts_block = format_facts_for_text(state["user_query"], max_facts=20)
    user_msg = (
        f"User question: {state['user_query']}\n\n"
        f"Sub-answers:\n\n{_format_sub_results(results)}\n\n"
        f"PRE-EXTRACTED POLICY / STRATEGIC FACTS — you MUST use any of these that are\n"
        f"relevant to the question, inline with their [fact-id] and source:\n\n{facts_block}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYNTHESISER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )
    final = (resp.choices[0].message.content or "").strip()
    logger.info("Synthesiser produced %s chars", len(final))
    trace = state.get("trace", []) + [f"synthesiser -> {len(final)} chars"]
    return {"draft_answer": final, "trace": trace}
