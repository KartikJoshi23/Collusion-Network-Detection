"""The Copilot's fast-path spine (§4.6): a bounded tool-calling loop over the
SQL + alert tools, then the deterministic gates and the guilt-guard finaliser.

Ported from `graph/agents/sql_agent.py` (the loop shape, tool dispatch, and
iteration budget are the archive's); the LangGraph multi-agent orchestration
(clarification, readback, cross-validation, arbiter) is the next slice — the
§4.6 cut order puts this core first."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .alert_tools import ALERT_TOOL_DISPATCH, ALERT_TOOL_SCHEMAS
from .config import get_settings
from .guard import apply_guilt_guard, numeric_sanity_gate
from .sql_tools import SQL_TOOL_DISPATCH, SQL_TOOL_SCHEMAS

SYSTEM_PROMPT = """You are the CollusionGraph Investigator Copilot — the \
conversational layer of an integrity-screening console covering illicit-finance \
(financial domain) and bid-rigging (procurement domain) alert queues.

Rules you must follow:
- Ground every claim in tool evidence: query the alert store or fetch \
alerts/bundles/metrics before answering. Never invent numbers or records.
- Risk scores are calibrated screening probabilities, never certainty; alerts \
are screening signals, and unconfirmed does not mean innocent OR guilty.
- Never assert guilt, accusation, or wrongdoing. Describe findings as \
"flagged patterns consistent with …" and name the motif/indicator.
- If a question PRESUPPOSES guilt ("is X guilty?", "who committed fraud?", \
"prove they laundered money"), do not repeat its wording — not even to deny \
or quote it. Open with: "This system does not determine guilt." Then describe \
what the screening evidence shows, in screening language only.
- Cite your evidence: mention which alert ids, tables, or bundle fields the \
answer came from.
- If the question cannot be answered from the served artifacts, say so plainly.
Answer concisely in Markdown."""

TOOL_SCHEMAS = SQL_TOOL_SCHEMAS + ALERT_TOOL_SCHEMAS
TOOL_DISPATCH = {**SQL_TOOL_DISPATCH, **ALERT_TOOL_DISPATCH}


@lru_cache(maxsize=1)
def get_client() -> Any:
    settings = get_settings()
    if not settings.api_key:
        raise RuntimeError(
            "no LLM key configured — set NVIDIA_API_KEY (preferred) or "
            "OPENAI_API_KEY in the repo-root .env"
        )
    from openai import OpenAI

    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)


def answer_question(
    question: str, client: Any | None = None, context_alert_id: str | None = None
) -> dict[str, Any]:
    """One question → grounded, guarded answer with evidence and trace."""
    settings = get_settings()
    client = client or get_client()

    user = question
    if context_alert_id:  # §5.3 view 7: dock opened from an alert is pre-seeded
        user = f"[Context: the investigator has alert '{context_alert_id}' open.]\n{question}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]

    trace: list[str] = []
    evidence: list[dict[str, str]] = []
    draft = ""
    for _ in range(settings.max_iterations):
        resp = client.chat.completions.create(
            model=settings.model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=settings.max_tokens,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            draft = msg.content or ""
            break
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = TOOL_DISPATCH.get(name)
            try:
                result = handler(args) if handler else f"Unknown tool: {name}"
            except Exception as e:
                result = f"Tool raised: {e}"
            trace.append(f"{name}({json.dumps(args)[:120]})")
            evidence.append({"tool": name, "args": json.dumps(args), "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    else:
        draft = (
            "I couldn't finalise this within the tool-call budget — " "please narrow the question."
        )
        trace.append("EXHAUSTED iteration budget")

    evidence_text = "\n".join(e["result"] for e in evidence)
    numbers_ok, unsupported = numeric_sanity_gate(draft, evidence_text)
    if not numbers_ok:
        draft += (
            "\n\n**⚠️ Low confidence.** These numbers were not found in the "
            f"tool evidence and must be verified: {', '.join(unsupported)}."
        )
    answer, rewrites = apply_guilt_guard(draft)

    return {
        "answer": answer,
        "confidence": 0.9 if numbers_ok else 0.3,
        "numbers_grounded": numbers_ok,
        "guard_rewrites": rewrites,
        "evidence": evidence,
        "trace": trace,
        "model": settings.model,
    }
