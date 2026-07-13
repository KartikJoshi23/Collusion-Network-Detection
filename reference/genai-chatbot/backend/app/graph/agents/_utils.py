"""Shared helpers for agent nodes."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_json_response(content: str, *, context: str = "") -> dict[str, Any]:
    """Parse a JSON object from an LLM response, tolerating surrounding prose.

    GPT-family models almost always return clean JSON when instructed, but
    occasionally wrap it in prose or triple backticks. This helper strips both.
    Raises ValueError if no JSON object can be found.
    """
    if not content:
        raise ValueError(f"Empty response [{context}]")

    # Strip triple-backtick fences if present.
    stripped = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    else:
        # Take the first {...} block at the top level.
        obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if obj_match:
            stripped = obj_match.group(0)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed [%s]: %s\nPayload:\n%s", context, e, content)
        raise ValueError(f"Could not parse JSON [{context}]: {e}") from e


def format_history_for_prompt(history: list[dict[str, str]], max_turns: int = 6) -> str:
    if not history:
        return "(no prior turns)"
    recent = history[-max_turns:]
    lines: list[str] = []
    for turn in recent:
        role = turn.get("role", "?")
        content = turn.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)
