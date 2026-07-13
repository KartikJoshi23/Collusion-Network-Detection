"""
/api/chat endpoints.

Two endpoints:
  * `POST /api/chat/session` — mint a new thread id. Client stores this and
    sends it with every subsequent message.
  * `POST /api/chat/message`  — send a user message (or a clarification/
    readback response) and receive an SSE stream of events: agent trace,
    interrupt requests, and the final answer.

SSE event types emitted:
  - `trace`        { phase, text }
  - `clarification`{ question, options, round }  — graph paused, awaiting answer
  - `readback`     { readback }                    — graph paused, awaiting confirm/adjust
  - `final`        { answer, confidence, evidence, trace }
  - `error`        { message }
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.graph.orchestrator import get_graph
from app.graph.state import make_initial_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class NewSessionResponse(BaseModel):
    thread_id: str


class MessageRequest(BaseModel):
    thread_id: str
    user_input: Any  # either str (new message / free-text clarification) or dict (readback response)


@router.post("/session", response_model=NewSessionResponse)
def create_session() -> NewSessionResponse:
    return NewSessionResponse(thread_id=str(uuid.uuid4()))


def _make_sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, default=str)}


def _state_has_pending_interrupt(graph, config) -> tuple[bool, dict | None, str | None]:
    """Inspect the graph's current state to see if it's paused on an interrupt."""
    snap = graph.get_state(config)
    if not snap.tasks:
        return False, None, None
    for task in snap.tasks:
        interrupts = getattr(task, "interrupts", None) or []
        if not interrupts:
            continue
        # Interrupt value is whatever the node passed to `interrupt(...)`.
        value = getattr(interrupts[0], "value", None)
        node = task.name
        return True, value, node
    return False, None, None


async def _stream_events(thread_id: str, user_input: Any) -> AsyncGenerator[dict, None]:
    from langgraph.types import Command

    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}

        snap = graph.get_state(config)
        is_resume = bool(snap.tasks and any(getattr(t, "interrupts", None) for t in snap.tasks))

        if is_resume:
            logger.info("Resuming thread %s with user_input=%r", thread_id, user_input)
            update = Command(resume=user_input)
            stream_args: tuple = (update,)
        else:
            logger.info("New thread %s with user_input=%r", thread_id, user_input)
            if not isinstance(user_input, str):
                raise ValueError("Initial user_input must be a string.")
            initial = make_initial_state(thread_id, user_input)
            stream_args = (initial,)

        # stream_mode="updates" yields {node_name: {partial state changes}}.
        # Interrupts appear as {'__interrupt__': (Interrupt(...), ...)} —
        # we handle those inline so we can emit the SSE immediately.
        interrupt_payload: dict | None = None

        for update in graph.stream(*stream_args, config=config, stream_mode="updates"):
            for key, val in update.items():
                if key == "__interrupt__":
                    # val is a tuple of Interrupt objects. Take the first's value.
                    try:
                        first = val[0] if val else None
                        interrupt_payload = getattr(first, "value", None) or {}
                    except Exception:  # noqa: BLE001
                        interrupt_payload = {}
                    continue
                if key.startswith("__") or not isinstance(val, dict):
                    continue
                new_trace = val.get("trace") or []
                for t in new_trace[-3:]:
                    yield _make_sse("trace", {"phase": key, "text": t})

        # If we captured an interrupt during streaming, surface it now.
        if interrupt_payload is None:
            paused, value, _ = _state_has_pending_interrupt(graph, config)
            if paused:
                interrupt_payload = value or {}

        if interrupt_payload is not None:
            if "readback" in interrupt_payload:
                yield _make_sse("readback", interrupt_payload)
            else:
                yield _make_sse("clarification", interrupt_payload)
            return

        final_state = graph.get_state(config).values
        yield _make_sse("final", {
            "answer": final_state.get("final_answer", ""),
            "confidence": final_state.get("final_confidence", 0.0),
            "evidence": final_state.get("evidence", {}),
            "trace": final_state.get("trace", []),
        })

    except Exception as e:  # noqa: BLE001
        logger.exception("chat stream failed")
        yield _make_sse("error", {"message": str(e)})


@router.post("/message")
async def post_message(req: MessageRequest):
    if not req.thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")

    async def event_gen():
        async for ev in _stream_events(req.thread_id, req.user_input):
            yield ev

    return EventSourceResponse(event_gen())
