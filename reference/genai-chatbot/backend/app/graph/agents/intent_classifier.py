"""Intent Classifier — structured `{entities, ops, ambiguities, clarity_score}`.

Few-shots the 3 structurally-nearest golden queries (by question text the first
time; later calls use the last structured intent, but for the first call we only
have raw text so that's the seed).
"""

from __future__ import annotations

import json
import logging

from app.graph.agents._utils import parse_json_response
from app.graph.prompts import INTENT_CLASSIFIER_SYSTEM, load_schema_text
from app.graph.state import AgentState
from app.llm import get_model_name, get_openai_client
from app.retrieval.fewshot import get_fewshot_selector

logger = logging.getLogger(__name__)


def _build_fewshot_block(goldens: list[dict]) -> str:
    if not goldens:
        return "(no golden examples available)"
    lines: list[str] = []
    for g in goldens:
        lines.append(
            f"Question: {g['question']}\nExpected intent:\n{json.dumps(g.get('expected_intent', {}), indent=2)}"
        )
    return "\n\n---\n\n".join(lines)


def intent_classifier_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()
    query = state.get("enriched_query") or state["user_query"]

    fewshot = get_fewshot_selector()
    goldens = fewshot.by_question(query, k=3)

    user_block = (
        f"User question: {query}\n\n"
        f"Database schema (abbreviated):\n```yaml\n{load_schema_text()[:3500]}\n```\n\n"
        f"Similar golden examples (for reference only — do NOT match keywords, match structure):\n"
        f"{_build_fewshot_block(goldens)}\n\n"
        f"Produce the structured intent for the user question, as JSON per the instructions."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": INTENT_CLASSIFIER_SYSTEM},
            {"role": "user", "content": user_block},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    payload = parse_json_response(resp.choices[0].message.content or "", context="intent_classifier")

    intent = {
        "entities": payload.get("entities", []) or [],
        "ops": payload.get("ops", []) or [],
        "ambiguities": payload.get("ambiguities", []) or [],
        "clarity_score": float(payload.get("clarity_score", 0.5)),
    }

    # Inherit route from Router — we'll overwrite in the clarification agent if needed.
    if state.get("route"):
        intent["route"] = state["route"]

    logger.info(
        "Intent -> entities=%s ops=%s clarity=%.2f ambiguities=%d",
        intent["entities"], intent["ops"], intent["clarity_score"], len(intent["ambiguities"]),
    )

    trace = state.get("trace", []) + [
        f"intent -> clarity={intent['clarity_score']:.2f}, {len(intent['ambiguities'])} ambiguity"
        + ("ies" if len(intent["ambiguities"]) != 1 else "y")
    ]
    return {"intent": intent, "trace": trace}
