"""
Arbiter — fires when Critic and Cross-Validator disagree.

Runs fresh derivation with full tool access and produces a definitive verdict.
If the disagreement is genuinely irresolvable, it returns `verdict: "fail"`
which downstream graceful-degradation handles with the low-confidence badge +
raw evidence presentation.
"""

from __future__ import annotations

import json
import logging

from app.graph.agents._utils import parse_json_response
from app.graph.prompts import ARBITER_SYSTEM
from app.graph.state import AgentState, CriticVerdict
from app.llm import get_model_name, get_openai_client
from app.tools import rag_tools, sql_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 6

_VALID_VERDICTS = {"pass", "retry", "uncertain", "fail"}


def should_arbitrate(state: AgentState) -> bool:
    critic = state.get("critic_verdict") or {}
    cross = state.get("cross_validator_verdict") or {}
    if not cross:
        return False
    # High-confidence pass from Cross-Validator terminates the chain — this is
    # the expected path when a grounding-retry was resolved by adding PDF
    # citations. Arbiter is only valuable for genuine disagreement.
    if cross.get("verdict") == "pass" and float(cross.get("confidence", 0)) >= 0.85:
        return False
    if critic.get("verdict") != cross.get("verdict"):
        return True
    conf_gap = abs(float(critic.get("confidence", 0)) - float(cross.get("confidence", 0)))
    return conf_gap > 0.3


def arbiter_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    all_tools = sql_tools.TOOL_SCHEMAS + rag_tools.TOOL_SCHEMAS
    dispatch: dict = {**sql_tools.TOOL_DISPATCH, **rag_tools.TOOL_DISPATCH}

    user_msg = (
        f"User question: {state['user_query']}\n\n"
        f"Intent:\n```json\n{json.dumps(state.get('intent') or {}, indent=2)}\n```\n\n"
        f"Draft answer:\n{state.get('draft_answer','')}\n\n"
        f"Critic verdict:\n```json\n{json.dumps(state.get('critic_verdict') or {}, indent=2)}\n```\n\n"
        f"Cross-Validator verdict:\n```json\n{json.dumps(state.get('cross_validator_verdict') or {}, indent=2)}\n```\n\n"
        "Re-derive from scratch. Produce a definitive verdict JSON."
    )
    messages: list[dict] = [
        {"role": "system", "content": ARBITER_SYSTEM},
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
                payload = parse_json_response(msg.content or "", context="arbiter")
            except ValueError:
                payload = {"confidence": 0.5, "reasons": ["unparseable arbiter response"], "verdict": "fail"}

            verdict_str = str(payload.get("verdict", "")).lower()
            if verdict_str not in _VALID_VERDICTS:
                verdict_str = "fail"
            v: CriticVerdict = {
                "confidence": float(payload.get("confidence", 0.5)),
                "reasons": payload.get("reasons", []) or [],
                "issues": payload.get("issues", []) or [],
                "verdict": verdict_str,  # type: ignore[typeddict-item]
            }
            logger.info("Arbiter -> %s (conf %.2f)", v["verdict"], v["confidence"])
            trace = state.get("trace", []) + [f"arbiter -> {v['verdict']} ({v['confidence']:.2f})"]
            return {"arbiter_verdict": v, "trace": trace}

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

    logger.warning("Arbiter exhausted iterations.")
    trace = state.get("trace", []) + ["arbiter -> EXHAUSTED"]
    return {
        "arbiter_verdict": {
            "confidence": 0.4,
            "reasons": ["Arbiter exhausted iterations — treating as fail."],
            "issues": [],
            "verdict": "fail",
        },
        "trace": trace,
    }
