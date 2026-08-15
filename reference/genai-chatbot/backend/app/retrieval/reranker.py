"""
Cross-encoder reranker (BAAI/bge-reranker-base).

Cross-encoders score (query, doc) pairs jointly and are much more accurate
than bi-encoder cosine similarity, at the cost of O(n) forward passes per
query. For 20 candidates on CPU this takes ~200ms — acceptable for chat UX.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import get_settings
from app.retrieval.hybrid import RetrievedChunk

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        logger.info("Loading reranker '%s' on %s", model_name, device)
        self.model = CrossEncoder(model_name, device=device)

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [(query, c.contextual_text + "\n\n" + c.raw_text) for c in candidates]
        scores = self.model.predict(pairs, show_progress_bar=False).tolist()
        # Replace RRF fusion score with the (more informative) cross-encoder score.
        scored = [
            RetrievedChunk(
                chunk_id=c.chunk_id,
                doc_name=c.doc_name,
                section_num=c.section_num,
                section_title=c.section_title,
                raw_text=c.raw_text,
                contextual_text=c.contextual_text,
                score=float(s),
            )
            for c, s in zip(candidates, scores)
        ]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    settings = get_settings()
    return Reranker(settings.reranker_model)
