"""Copilot router (§4.6): mounted into the serving app at /api/v1/copilot.

JSON chat endpoint + the SSE streaming variant (27b): /chat/stream emits
``trace`` events live as the agent calls tools, then one ``final`` event with
the exact /chat payload. Events use CRLF framing — the dock's client is the
archive's FIXED parser (FIX_FRONTEND.md), which normalises CRLF, so both
endings are exercised end-to-end. The router imports lazily so
`collusiongraph serve` stays usable — and torch-free — on machines with no
LLM key: /health reports configured=false instead of the app failing to
start."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from collusiongraph import SCREENING_CAVEAT
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\r\ndata: {json.dumps(data, ensure_ascii=False)}\r\n\r\n"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context_alert_id: str | None = None


@router.get("/health")
def health() -> dict:
    from .config import get_settings

    settings = get_settings()
    return {
        "configured": bool(settings.api_key),
        "provider": settings.provider,
        "model": settings.model,
        "caveat": SCREENING_CAVEAT,
    }


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    from .agent import answer_question

    try:
        result = answer_question(req.question, context_alert_id=req.context_alert_id)
    except RuntimeError as e:  # no key configured
        raise HTTPException(status_code=503, detail=str(e)) from e
    result["caveat"] = SCREENING_CAVEAT
    result["ai_generated"] = True  # §4.6: every response carries the AI label
    return result


@router.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    from .agent import answer_question_events, get_client

    try:
        client = get_client()  # eager: a missing key is a clean 503, not a broken stream
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    def events() -> Iterator[str]:
        try:
            for kind, data in answer_question_events(
                req.question, client=client, context_alert_id=req.context_alert_id
            ):
                if kind == "trace":
                    yield _sse("trace", {"step": data})
                else:
                    data["caveat"] = SCREENING_CAVEAT
                    data["ai_generated"] = True  # §4.6 label on the streamed final too
                    yield _sse("final", data)
        except Exception as e:  # surface mid-stream failures as an event
            yield _sse("error", {"detail": str(e)})

    return StreamingResponse(events(), media_type="text/event-stream")
