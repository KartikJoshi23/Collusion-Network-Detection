"""
Hybrid executor — runs each sub-question from the Planner through either the
SQL Agent or the RAG Agent, in sequence for now. (Parallel execution would
require per-sub-question sub-graphs; worth the complexity for production but
sequential runs finish in ~10-15s on this small corpus.)
"""

from __future__ import annotations

import logging
from typing import Any

from app.graph.agents.rag_agent import rag_agent_node
from app.graph.agents.sql_agent import sql_agent_node
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


def hybrid_execute_node(state: AgentState) -> dict:
    sub_qs = state.get("sub_questions") or []
    results: list[dict[str, Any]] = []

    for i, sub in enumerate(sub_qs):
        sub_question = sub.get("question", "")
        sub_type = sub.get("type", "sql")
        logger.info("Hybrid sub-question %s/%s [%s]: %s", i + 1, len(sub_qs), sub_type, sub_question)

        # Compose a brief context block from already-completed sub-answers so
        # that sub-question N can reference what sub-question N-1 actually
        # returned. Without this, each sub-question runs blind to prior
        # results, which breaks dependent sub-questions ("for each row above,
        # also do X").
        prior_block = ""
        if results:
            prior_lines: list[str] = []
            for j, prev in enumerate(results, 1):
                prior_lines.append(f"### Prior sub-answer {j} ({prev.get('type','?')}): {prev.get('question','')[:120]}")
                prior_lines.append((prev.get('answer') or '')[:1200])
                if prev.get('sql_result'):
                    rows = (prev['sql_result'].get('rows_markdown') or '')[:1500]
                    if rows:
                        prior_lines.append("Rows:")
                        prior_lines.append(rows)
                prior_lines.append("")
            prior_block = "\n".join(prior_lines)

        sub_state: AgentState = dict(state)  # type: ignore[assignment]
        if prior_block:
            sub_state["user_query"] = (
                f"{sub_question}\n\n"
                f"=== Prior sub-answers in this hybrid plan (use these where relevant) ===\n"
                f"{prior_block}"
            )
        else:
            sub_state["user_query"] = sub_question
        sub_state["enriched_query"] = sub_state["user_query"]

        if sub_type == "sql":
            out = sql_agent_node(sub_state)
            results.append({
                "type": "sql",
                "question": sub_question,
                "answer": out.get("draft_answer", ""),
                "sql_result": out.get("sql_result"),
            })
        else:
            out = rag_agent_node(sub_state)
            results.append({
                "type": "rag",
                "question": sub_question,
                "answer": out.get("draft_answer", ""),
                "rag_result": out.get("rag_result"),
            })

    trace = state.get("trace", []) + [f"hybrid_exec -> {len(results)} sub-answer(s)"]
    return {"hybrid_sub_results": results, "trace": trace}
