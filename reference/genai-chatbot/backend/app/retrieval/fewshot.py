"""
Few-shot selector over the golden set.

Key insight from the design discussion: users rarely phrase questions using the
same keywords we wrote goldens in, so raw-text similarity is fragile. We instead
match on STRUCTURED INTENT — concatenated `{entities} + {ops}` string — embedded
once at startup. Retrieval at inference finds the goldens whose intent *shape*
most closely matches the current query's intent shape.

Graceful fallback: if structured intent isn't yet known (e.g. Router hasn't
run), we fall back to raw-text similarity over the golden questions.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.data.embeddings import get_embedder

logger = logging.getLogger(__name__)

GOLDENS_PATH = Path(__file__).parent.parent.parent / "eval" / "goldens.json"


def _intent_signature(intent: dict) -> str:
    """Flatten a structured intent into a text string suitable for embedding."""
    entities = " ".join(intent.get("entities", []) or [])
    ops = " ".join(intent.get("ops", []) or [])
    route = intent.get("route", "") or ""
    return f"route: {route} | entities: {entities} | ops: {ops}"


class FewShotSelector:
    def __init__(self, goldens: list[dict]) -> None:
        self.goldens = goldens
        self.embedder = get_embedder()
        # Two parallel indices: one keyed on structured intent, one on raw question text.
        intent_signatures = [_intent_signature(g.get("expected_intent", {})) for g in goldens]
        self.intent_vectors = self.embedder.embed_documents(intent_signatures)
        self.question_vectors = self.embedder.embed_documents([g["question"] for g in goldens])

    def _top_k(self, query_vec: np.ndarray, matrix: np.ndarray, k: int) -> list[int]:
        scores = matrix @ query_vec
        return list(np.argsort(-scores)[:k])

    def by_intent(self, intent: dict, k: int = 3) -> list[dict]:
        sig = _intent_signature(intent)
        vec = self.embedder.embed_query(sig)
        idxs = self._top_k(vec, self.intent_vectors, k)
        return [self.goldens[i] for i in idxs]

    def by_question(self, question: str, k: int = 3) -> list[dict]:
        vec = self.embedder.embed_query(question)
        idxs = self._top_k(vec, self.question_vectors, k)
        return [self.goldens[i] for i in idxs]

    def by_category(self, category: str, k: int = 3) -> list[dict]:
        matching = [g for g in self.goldens if g.get("category") == category]
        return matching[:k]


def _load_goldens() -> list[dict]:
    if not GOLDENS_PATH.exists():
        logger.warning("Goldens file not found at %s", GOLDENS_PATH)
        return []
    with open(GOLDENS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_fewshot_selector() -> FewShotSelector:
    goldens = _load_goldens()
    return FewShotSelector(goldens)
