"""Copilot router (§4.6): mounted into the serving app at /api/v1/copilot.

This slice ships the JSON chat endpoint; the SSE streaming variant (with the
archive's CRLF parser fix on the client side) lands with the 27b dock. The
router imports lazily so `collusiongraph serve` stays usable — and torch-free
— on machines with no LLM key: /health reports configured=false instead of
the app failing to start."""

from __future__ import annotations

from collusiongraph import SCREENING_CAVEAT
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


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
