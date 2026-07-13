import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.chat import router as chat_router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="TechNova Agentic Chatbot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    model: str
    qdrant_url: str
    redis_url: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=os.getenv("OPENAI_MODEL_NAME", "unset"),
        qdrant_url=os.getenv("QDRANT_URL", "unset"),
        redis_url=os.getenv("REDIS_URL", "unset"),
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "TechNova Agentic Chatbot",
        "phase": "2+ - agents online",
        "docs": "/docs",
        "chat": "/api/chat/session (POST) then /api/chat/message (POST, SSE)",
    }


app.include_router(chat_router)


@app.on_event("shutdown")
def _flush_langfuse_on_shutdown() -> None:
    try:
        from langfuse import Langfuse  # type: ignore

        lf = Langfuse()
        lf.flush()
    except Exception:
        pass  # Langfuse optional; safe to ignore failures on shutdown.
