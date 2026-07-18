"""RAG corpus + retrieval (§4.6: keep, retarget — Qdrant dropped).

The corpus is the project's OWN curated red-flag knowledge base: the FATF and
OECD indicator tables that ship in `collusiongraph.explain.redflags`
(paraphrased condensations — license-safe by construction) plus
`docs/red_flag_mappings.md` sections. Chunk ids are citable (indicator ids
like FATF-STRUCT-01 / OECD-CB-01), which is exactly what the grounding gate
checks. Retrieval is an in-process BM25 (~tiny corpus; the archive's dense
leg + reranker join later if the corpus outgrows it)."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

from collusiongraph.explain import load_indicators

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


@lru_cache(maxsize=1)
def corpus_chunks() -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for domain in ("financial", "procurement"):
        table = load_indicators(domain)
        framework = table["framework"]
        for ind in table["indicators"]:
            chunks.append(
                {
                    "chunk_id": ind["id"],
                    "source": f"{framework} indicator table ({domain})",
                    "text": f"{ind['text']} Motifs: {', '.join(ind['motifs'])}.",
                }
            )
    mappings = Path("docs/red_flag_mappings.md")
    if mappings.is_file():
        section = ""
        body: list[str] = []
        for line in mappings.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                if section and body:
                    chunks.append(
                        {
                            "chunk_id": f"DOC:{section[:40]}",
                            "source": "docs/red_flag_mappings.md",
                            "text": " ".join(body)[:1000],
                        }
                    )
                section = line.lstrip("# ").strip()
                body = []
            elif line.strip():
                body.append(line.strip())
        if section and body:
            chunks.append(
                {
                    "chunk_id": f"DOC:{section[:40]}",
                    "source": "docs/red_flag_mappings.md",
                    "text": " ".join(body)[:1000],
                }
            )
    return chunks


def bm25_search(query: str, k: int = 4) -> list[dict[str, str]]:
    """Plain BM25 (k1=1.5, b=0.75) over the chunk texts."""
    chunks = corpus_chunks()
    docs = [_tokens(c["text"]) for c in chunks]
    n = len(docs)
    avg_len = sum(len(d) for d in docs) / max(n, 1)
    df: dict[str, int] = {}
    for d in docs:
        for term in set(d):
            df[term] = df.get(term, 0) + 1
    scores = []
    q_terms = _tokens(query)
    for i, d in enumerate(docs):
        score = 0.0
        for term in q_terms:
            tf = d.count(term)
            if tf == 0:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * len(d) / avg_len))
        scores.append((score, i))
    scores.sort(reverse=True)
    return [chunks[i] for s, i in scores[:k] if s > 0]


def corpus_search(query: str, k: int = 4) -> str:
    hits = bm25_search(query, k)
    if not hits:
        return "No corpus chunks matched. The red-flag knowledge base may not cover this topic."
    return "\n\n".join(f"[{h['chunk_id']}] ({h['source']})\n{h['text']}" for h in hits)


CORPUS_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "corpus_search",
            "description": (
                "Search the curated red-flag knowledge base (FATF indicators, "
                "OECD bid-rigging checklist, methodology docs). REQUIRED for "
                "typology/red-flag questions; cite the [chunk ids] returned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 4},
                },
                "required": ["query"],
            },
        },
    },
]

CORPUS_TOOL_DISPATCH = {
    "corpus_search": lambda args: corpus_search(args["query"], k=args.get("k", 4)),
}
