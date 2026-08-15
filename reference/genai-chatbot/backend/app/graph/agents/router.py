"""Router agent — one-shot classification into sql / rag / hybrid / clarify."""

from __future__ import annotations

import logging

from app.graph.agents._utils import parse_json_response
from app.graph.prompts import ROUTER_SYSTEM
from app.graph.state import AgentState
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)

_VALID_ROUTES = {"sql", "rag", "hybrid", "clarify"}


def router_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()
    query = state.get("enriched_query") or state["user_query"]

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    payload = parse_json_response(resp.choices[0].message.content or "", context="router")
    route = str(payload.get("route", "")).lower()
    if route not in _VALID_ROUTES:
        logger.warning("Router returned invalid route %r; defaulting to sql", route)
        route = "sql"

    logger.info("Router -> %s (reason: %s)", route, payload.get("reason"))
    trace = state.get("trace", []) + [f"router -> {route}"]
    return {"route": route, "trace": trace}
