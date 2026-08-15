"""
Cross-Validator — fires when Critic confidence is borderline.

Re-derives the answer by a DIFFERENT method than the SQL/RAG Agent used, using
the same tool arsenal. The comparison is what makes this useful — otherwise
we've only run the Critic twice.
"""

from __future__ import annotations

import json
import logging

from app.data.facts import format_facts_for_text
from app.graph.agents._utils import parse_json_response
from app.graph.prompts import CROSS_VALIDATOR_SYSTEM
from app.graph.state import AgentState, CriticVerdict
from app.llm import get_model_name, get_openai_client
from app.tools import rag_tools, sql_tools
import re

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 6

LOW_BAND, HIGH_BAND = 0.5, 0.85

_VALID_VERDICTS = {"pass", "retry", "uncertain", "fail"}
_CHUNK_ID_RE = re.compile(r"\[([A-Za-z0-9_\-.]+\.pdf::sec\d+)\]")


def should_cross_validate(state: AgentState) -> bool:
    v = state.get("critic_verdict") or {}
    conf = float(v.get("confidence", 1.0))
    # Fires on borderline confidence OR explicit uncertainty OR retry OR fail.
    # `fail` is included because many failures are recoverable — the Critic
    # might have over-penalised a presentation issue when the underlying
    # data is correct. The Cross-Validator has tools to re-derive and
    # the prompt instructs it to produce a revised_answer that fixes
    # presentation while reusing valid evidence. Better to retry once than
    # ship a 0.08-confidence answer to the user.
    if v.get("verdict") in {"uncertain", "retry", "fail"}:
        return True
    return LOW_BAND <= conf <= HIGH_BAND


def cross_validator_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    all_tools = sql_tools.TOOL_SCHEMAS + rag_tools.TOOL_SCHEMAS
    dispatch: dict = {**sql_tools.TOOL_DISPATCH, **rag_tools.TOOL_DISPATCH}

    critic_v = state.get("critic_verdict") or {}
    is_grounding_retry = (
        critic_v.get("verdict") == "retry"
        and any("grounding" in str(r).lower() for r in critic_v.get("reasons", []))
    )

    grounding_instruction = (
        "\n\nIMPORTANT: the Critic flagged this as a GROUNDING failure — the "
        "answer uses policy/fuzzy terms but cites no PDF. Your job is to RE-"
        "GROUND it:\n"
        "  1. Call `hybrid_search` with the policy terms from the question.\n"
        "  2. Read the top chunks and extract the concrete policy facts.\n"
        "  3. Produce a `revised_answer` that keeps the original SQL findings "
        "but weaves in the policy facts with inline `[doc.pdf::secN]` citations.\n"
        if is_grounding_retry
        else ""
    )

    facts_block = format_facts_for_text(state["user_query"], max_facts=20)
    user_msg = (
        f"User question: {state['user_query']}\n\n"
        f"Intent:\n```json\n{json.dumps(state.get('intent') or {}, indent=2)}\n```\n\n"
        f"Original draft answer:\n{state.get('draft_answer', '')}\n\n"
        f"Original SQL result:\n{(state.get('sql_result') or {}).get('rows_markdown', '(none)')}\n\n"
        f"Critic verdict:\n```json\n{json.dumps(critic_v, indent=2)}\n```\n\n"
        f"PRE-EXTRACTED POLICY / STRATEGIC FACTS (use any relevant ones in your revised_answer,\n"
        f"inline with their [fact-id] citations and source):\n\n{facts_block}\n"
        f"{grounding_instruction}\n"
        "At the end, return STRICT JSON with this shape:\n"
        "```\n"
        '{\n'
        '  "confidence": 0.0-1.0,\n'
        '  "reasons": ["..."],\n'
        '  "issues": ["..."],\n'
        '  "verdict": "pass"|"retry"|"uncertain"|"fail",\n'
        '  "revised_answer": "<string — ONLY include when you fixed a grounding or correctness issue; include inline [doc.pdf::secN] citations>"\n'
        '}\n'
        "```"
    )
    messages: list[dict] = [
        {"role": "system", "content": CROSS_VALIDATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    for iteration in range(MAX_ITERATIONS):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=all_tools,
            tool_choice="auto",
            temperature=0.0,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            try:
                payload = parse_json_response(msg.content or "", context="cross_validator")
            except ValueError:
                payload = {"confidence": 0.5, "reasons": ["unparseable response"], "verdict": "uncertain"}

            verdict_str = str(payload.get("verdict", "")).lower()
            if verdict_str not in _VALID_VERDICTS:
                verdict_str = "uncertain"
            v: CriticVerdict = {
                "confidence": float(payload.get("confidence", 0.5)),
                "reasons": payload.get("reasons", []) or [],
                "issues": payload.get("issues", []) or [],
                "verdict": verdict_str,  # type: ignore[typeddict-item]
            }
            logger.info("Cross-Validator -> %s (conf %.2f)", v["verdict"], v["confidence"])

            updates: dict = {
                "cross_validator_verdict": v,
                "trace": state.get("trace", []) + [
                    f"cross_validator -> {v['verdict']} ({v['confidence']:.2f})"
                ],
            }

            # If the cross-validator produced a revised answer (typically on
            # grounding-retry), swap it into draft_answer. Finaliser will pick
            # this up via _pick_authoritative_verdict + updated draft.
            revised = payload.get("revised_answer")
            if revised and v["verdict"] in {"pass", "uncertain"}:
                updates["draft_answer"] = str(revised)
                # Extract any newly-cited chunks for the evidence panel.
                cited_ids = _CHUNK_ID_RE.findall(str(revised))
                if cited_ids:
                    prior_rag = state.get("rag_result") or {}
                    existing_ids = {c.get("chunk_id") for c in (prior_rag.get("citations") or [])}
                    new_cits = list(existing_ids | set(cited_ids))
                    updates["rag_result"] = {
                        **prior_rag,
                        "answer": revised,
                        "citations": [{"chunk_id": cid} for cid in new_cits],
                    }
                logger.info("Cross-Validator emitted revised_answer (%d chars, %d cites)",
                            len(revised), len(cited_ids))

            return updates

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = dispatch.get(name)
            if handler is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = handler(args)
                except Exception as e:  # noqa: BLE001
                    result = f"Tool raised: {e}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    logger.warning("Cross-Validator exhausted iterations.")
    trace = state.get("trace", []) + ["cross_validator -> EXHAUSTED"]
    return {
        "cross_validator_verdict": {
            "confidence": 0.5,
            "reasons": ["Cross-Validator ran out of iterations."],
            "issues": [],
            "verdict": "uncertain",
        },
        "trace": trace,
    }
