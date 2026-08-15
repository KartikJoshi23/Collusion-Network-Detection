"""OpenAI client factory.

If Langfuse credentials are present in `.env`, we transparently swap in the
`langfuse.openai.OpenAI` wrapper — every chat completion then auto-creates a
Langfuse trace span. If Langfuse is absent or misconfigured, we fall back to
the vanilla OpenAI client. No code path elsewhere has to know which one is in
use.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class _CompletionsShim:
    """Wraps chat.completions and drops params GPT-5 reasoning models reject.

    GPT-5 models only support the default temperature (1); any explicit
    temperature (the agents pass 0.0/0.1) triggers a 400. We strip it for
    gpt-5* models while leaving other models (e.g. gpt-4.1) untouched.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def create(self, *args: Any, **kwargs: Any) -> Any:
        model = kwargs.get("model", "")
        if isinstance(model, str) and model.startswith("gpt-5"):
            t = kwargs.get("temperature")
            if t is not None and t != 1:
                kwargs.pop("temperature", None)
        return self._inner.create(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ChatShim:
    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._completions = _CompletionsShim(inner.completions)

    @property
    def completions(self) -> Any:
        return self._completions

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ClientShim:
    """Transparent proxy around an OpenAI client that normalises GPT-5 params."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._chat = _ChatShim(inner.chat)

    @property
    def chat(self) -> Any:
        return self._chat

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _make_client() -> Any:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Populate .env and restart the backend."
        )

    # Try Langfuse-wrapped client first when both keys are present.
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse.openai import OpenAI as LangfuseOpenAI  # type: ignore

            logger.info("Using Langfuse-instrumented OpenAI client.")
            return _ClientShim(LangfuseOpenAI(api_key=settings.openai_api_key))
        except Exception as e:  # noqa: BLE001
            logger.warning("Langfuse OpenAI wrapper unavailable (%s) — using plain client.", e)

    from openai import OpenAI

    return _ClientShim(OpenAI(api_key=settings.openai_api_key))


@lru_cache(maxsize=1)
def get_openai_client() -> Any:
    return _make_client()


def get_model_name() -> str:
    return get_settings().openai_model_name
