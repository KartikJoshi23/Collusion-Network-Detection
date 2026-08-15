"""
Tools the RAG Agent calls via OpenAI function-calling.

Wraps the hybrid retriever + cross-encoder reranker and surfaces the results
as concise Markdown so the agent can cite them by chunk_id.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.retrieval.hybrid import RetrievedChunk, get_retriever
from app.retrieval.reranker import get_reranker

logger = logging.getLogger(__name__)


def _format_chunk(c: RetrievedChunk, include_context: bool = True) -> str:
    header = (
        f"**[{c.chunk_id}]** {c.doc_name} · §{c.section_num} {c.section_title} "
        f"(score {c.score:.3f})"
    )
    ctx = f"\n_Context:_ {c.contextual_text}" if include_context and c.contextual_text else ""
    return f"{header}{ctx}\n\n{c.raw_text}"


def hybrid_search(query: str, top_k: int | None = None) -> str:
    """Run dense + BM25 retrieval, RRF fusion, then cross-encoder rerank.

    Returns the top-k chunks as Markdown. Each chunk is identified by chunk_id
    in the form 'TechNova_DocName.pdf::sec3' so the agent can cite specific
    sections in its answer.
    """
    settings = get_settings()
    retriever = get_retriever()
    candidates = retriever.search(query, k=max(settings.retrieve_top_k_dense, settings.retrieve_top_k_bm25))
    if not candidates:
        return "(no matching chunks — the Qdrant collection may be empty. Run `make ingest`.)"

    reranker = get_reranker()
    final_k = top_k if top_k is not None else settings.rerank_top_k
    ranked = reranker.rerank(query, candidates, top_k=final_k)

    return "\n\n---\n\n".join(_format_chunk(c) for c in ranked)


def fetch_full_chunk(chunk_id: str) -> str:
    """Return the raw text of a specific chunk by id (e.g. after the agent has spotted a relevant reference)."""
    retriever = get_retriever()
    retriever._ensure_loaded()
    for payload in retriever._corpus_payloads:
        if payload["chunk_id"] == chunk_id:
            return (
                f"**{chunk_id}** — {payload['doc_name']} §{payload['section_num']} "
                f"{payload['section_title']}\n\n{payload['raw_text']}"
            )
    return f"No chunk found with id '{chunk_id}'. Use hybrid_search first."


def fetch_full_doc(doc_name: str) -> str:
    """Concatenate all chunks for one PDF into a single string, in section order."""
    retriever = get_retriever()
    retriever._ensure_loaded()
    chunks = [p for p in retriever._corpus_payloads if p["doc_name"] == doc_name]
    if not chunks:
        return f"No document found with name '{doc_name}'."
    chunks.sort(key=lambda p: p["section_num"])
    parts = [f"# {doc_name}"]
    for p in chunks:
        parts.append(f"\n## §{p['section_num']} {p['section_title']}\n\n{p['raw_text']}")
    return "\n".join(parts)


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "hybrid_search",
            "description": "Retrieve the most relevant document chunks using dense embeddings + BM25 fused with RRF, then rerank with a cross-encoder. Use for any question that needs policy, architecture, or governance information from the PDFs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query — usually a paraphrase of the user's question."},
                    "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_full_chunk",
            "description": "Return the raw text of one specific chunk by its chunk_id (e.g. 'TechNova_Board_Minutes_Q4.pdf::sec5'). Use after hybrid_search when you need to see a chunk's full content.",
            "parameters": {
                "type": "object",
                "properties": {"chunk_id": {"type": "string"}},
                "required": ["chunk_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_full_doc",
            "description": "Return all sections of one PDF (by filename) concatenated. Use sparingly — costs tokens. Useful for cross-section reasoning within a single document.",
            "parameters": {
                "type": "object",
                "properties": {"doc_name": {"type": "string", "description": "e.g. 'TechNova_Salary_Structure.pdf'"}},
                "required": ["doc_name"],
            },
        },
    },
]


TOOL_DISPATCH = {
    "hybrid_search": lambda args: hybrid_search(args["query"], top_k=args.get("top_k")),
    "fetch_full_chunk": lambda args: fetch_full_chunk(args["chunk_id"]),
    "fetch_full_doc": lambda args: fetch_full_doc(args["doc_name"]),
}
