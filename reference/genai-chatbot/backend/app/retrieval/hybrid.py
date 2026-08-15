"""
Hybrid retrieval: dense (nomic embeddings via Qdrant) + sparse (BM25 over raw
chunk text), fused with Reciprocal Rank Fusion.

BM25 index is small enough to keep in memory — the TechNova corpus is only
~50 chunks. The index is (re)built lazily on first use from Qdrant's stored
payloads, so it automatically stays in sync with whatever ingestion last
produced.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.data.embeddings import get_embedder

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"\w+")


def _tokenise(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_name: str
    section_num: int
    section_title: str
    raw_text: str
    contextual_text: str
    score: float  # fused RRF score — not directly comparable to cosine similarity


class HybridRetriever:
    """Dense + BM25 retrieval with RRF fusion over a single Qdrant collection."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = QdrantClient(url=self._settings.qdrant_url)
        self._embedder = get_embedder()
        self._bm25: BM25Okapi | None = None
        self._corpus_payloads: list[dict] = []
        self._corpus_tokens: list[list[str]] = []

    def _load_corpus(self) -> None:
        """Fetch all points from Qdrant and build the BM25 index in memory."""
        logger.info("Loading corpus from Qdrant for BM25 index...")
        collection = self._settings.qdrant_collection
        # scroll through all points; for 50 chunks this fits in one page.
        points, _ = self._client.scroll(
            collection_name=collection,
            limit=10_000,
            with_payload=True,
            with_vectors=False,
        )
        self._corpus_payloads = [p.payload for p in points]
        self._corpus_tokens = [
            _tokenise(p["raw_text"] + " " + p.get("contextual_text", ""))
            for p in self._corpus_payloads
        ]
        if not self._corpus_tokens:
            logger.warning("Qdrant collection '%s' is empty — run `make ingest`.", collection)
            self._bm25 = None
            return
        self._bm25 = BM25Okapi(self._corpus_tokens)
        logger.info("BM25 index built over %s chunks.", len(self._corpus_tokens))

    def _ensure_loaded(self) -> None:
        if self._bm25 is None and not self._corpus_payloads:
            self._load_corpus()

    def dense_search(self, query: str, k: int) -> list[tuple[str, float]]:
        """Dense vector search. Returns list of (chunk_id, score) ordered by score desc."""
        vector = self._embedder.embed_query(query)
        resp = self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            query=vector.tolist(),
            limit=k,
            with_payload=True,
        )
        return [(p.payload["chunk_id"], float(p.score)) for p in resp.points]

    def bm25_search(self, query: str, k: int) -> list[tuple[str, float]]:
        self._ensure_loaded()
        if self._bm25 is None:
            return []
        tokens = _tokenise(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            (
                (self._corpus_payloads[i]["chunk_id"], float(s))
                for i, s in enumerate(scores)
            ),
            key=lambda t: t[1],
            reverse=True,
        )
        return ranked[:k]

    def _fuse_rrf(
        self,
        dense: list[tuple[str, float]],
        sparse: list[tuple[str, float]],
        k: int,
    ) -> list[tuple[str, float]]:
        """Reciprocal Rank Fusion. score = sum(1 / (k + rank_i))."""
        rrf_k = self._settings.rrf_k
        scores: dict[str, float] = {}
        for rank, (chunk_id, _) in enumerate(dense):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        for rank, (chunk_id, _) in enumerate(sparse):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        return sorted(scores.items(), key=lambda t: t[1], reverse=True)[:k]

    def search(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        """Run dense + BM25, fuse with RRF, hydrate payloads."""
        self._ensure_loaded()
        top_k_dense = self._settings.retrieve_top_k_dense
        top_k_bm25 = self._settings.retrieve_top_k_bm25
        final_k = k if k is not None else max(top_k_dense, top_k_bm25)

        dense = self.dense_search(query, top_k_dense)
        sparse = self.bm25_search(query, top_k_bm25)
        fused = self._fuse_rrf(dense, sparse, final_k)

        payload_index = {p["chunk_id"]: p for p in self._corpus_payloads}
        # Fallback: any chunk_id in dense results that we haven't cached yet
        # gets fetched from Qdrant directly. For this small corpus not needed.
        results: list[RetrievedChunk] = []
        for chunk_id, score in fused:
            payload = payload_index.get(chunk_id)
            if payload is None:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_name=payload["doc_name"],
                    section_num=payload["section_num"],
                    section_title=payload["section_title"],
                    raw_text=payload["raw_text"],
                    contextual_text=payload.get("contextual_text", ""),
                    score=score,
                )
            )
        return results


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return HybridRetriever()
