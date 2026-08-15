"""RAG Agent — tool-using loop over the PDF corpus."""

from __future__ import annotations

import json
import logging
import re

from app.graph.prompts import RAG_AGENT_SYSTEM
from app.graph.state import AgentState, RagChunkRef, RagResult
from app.llm import get_model_name, get_openai_client
from app.retrieval.fewshot import get_fewshot_selector
from app.tools import rag_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 6

_CHUNK_ID_RE = re.compile(r"\[([A-Za-z0-9_\-.]+\.pdf::sec\d+)\]")


def _build_fewshot(intent: dict) -> str:
    if not intent:
        return ""
    selector = get_fewshot_selector()
    goldens = [
        g for g in selector.by_intent(intent, k=5)
        if g.get("category", "").startswith("rag")
    ][:3]
    if not goldens:
        return ""
    blocks: list[str] = []
    for g in goldens:
        sources = ", ".join(g.get("expected_sources", []) or [])
        blocks.append(f"Example question: {g['question']}\nExpected sources: {sources}")
    return "\n\n".join(blocks)


def _extract_chunk_ids(text: str) -> list[str]:
    return list(dict.fromkeys(_CHUNK_ID_RE.findall(text)))  # de-dup preserving order


def rag_agent_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    query = state.get("enriched_query") or state["user_query"]
    intent = state.get("intent") or {}

    user_msg = (
        f"User question: {query}\n\n"
        f"Structured intent:\n```json\n{json.dumps(intent, indent=2)}\n```\n\n"
        f"Reference goldens:\n{_build_fewshot(intent) or '(none)'}"
    )
    messages: list[dict] = [
        {"role": "system", "content": RAG_AGENT_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    chunks_seen: list[RagChunkRef] = []
    iterations = 0

    for iteration in range(MAX_ITERATIONS):
        iterations = iteration + 1
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=rag_tools.TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.0,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            final_answer = msg.content or ""
            cited_ids = _extract_chunk_ids(final_answer)
            citations: list[RagChunkRef] = [
                RagChunkRef(chunk_id=cid) for cid in cited_ids  # type: ignore[call-arg]
            ]
            logger.info("RAG Agent done in %s iter(s); %s citations", iterations, len(citations))
            result: RagResult = {
                "answer": final_answer,
                "citations": citations,
                "chunks_seen": chunks_seen,
            }
            trace = state.get("trace", []) + [f"rag_agent -> {iterations} iter, {len(citations)} cites"]
            return {"rag_result": result, "draft_answer": final_answer, "trace": trace}

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = rag_tools.TOOL_DISPATCH.get(name)
            if handler is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = handler(args)
                except Exception as e:  # noqa: BLE001
                    result = f"Tool raised: {e}"

            # Track which chunks the agent has seen for transparency.
            for cid in _extract_chunk_ids(result) + re.findall(r"\*\*\[([^\]]+)\]\*\*", result):
                if not any(c.get("chunk_id") == cid for c in chunks_seen):
                    chunks_seen.append(RagChunkRef(chunk_id=cid))  # type: ignore[call-arg]

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    logger.warning("RAG Agent hit MAX_ITERATIONS (%s).", MAX_ITERATIONS)
    trace = state.get("trace", []) + [f"rag_agent -> EXHAUSTED after {iterations}"]
    return {
        "rag_result": {"answer": "I could not converge on an answer.", "citations": [], "chunks_seen": chunks_seen},
        "draft_answer": "I could not converge on a grounded answer within the retrieval budget.",
        "trace": trace,
    }
