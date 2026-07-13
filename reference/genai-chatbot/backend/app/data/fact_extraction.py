"""
FactForge — auto-extraction of atomic facts from PDF chunks and structured tables.

Runs at ingestion time (not query time). Produces `facts_auto.yaml`, which is
merged with the hand-curated `facts_curated.yaml` by FactLoader at query time.

Architecture:
    PDF chunk  ──▶ extract_facts_from_chunk() [LLM, temperature=0, JSON-mode]
                        │
                        ▼
                  raw fact dicts
                        │
                        ▼  (after all chunks in the corpus)
                  dedup_facts() [embedding similarity, cosine > 0.92 = same fact]
                        │
                        ▼
                  write_yaml("facts_auto.yaml")

    DuckDB table ─▶ extract_schema_facts() [deterministic, no LLM]
                        │
                        ▼
                  raw fact dicts (row counts, enum values, FK notes)
                        │
                        ▼  merged into the same dedup pool above
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import yaml

from app.data.embeddings import get_embedder
from app.data.pdf_chunker import PDFChunk
from app.graph.prompts import FACT_EXTRACTION_SYSTEM
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)

# Allow-list of categories the extractor can emit. Derived from the existing
# FactLoader category taxonomy. Kept as an explicit constant so we can audit
# additions over time.
ALLOWED_CATEGORIES: tuple[str, ...] = (
    "ai_concentration", "ai_investment", "apac", "breach", "breach_absorption",
    "budget", "capex", "cert_in", "certification", "cloud_infrastructure",
    "compensation", "compliance", "criticality", "customer_base",
    "customer_growth", "customer_relationship", "customer_retention",
    "cybersecurity_budget", "data_localization", "data_model",
    "data_privacy", "dpdp", "engineering", "esop", "finance_query",
    "financial_baseline", "geo_expansion", "geopolitical", "governance",
    "incident_baseline", "incident_response", "infrastructure", "insurance",
    "ipo_milestone", "ipo_readiness", "ipo_timeline", "legal", "liquidity",
    "nrr", "on_call", "profitability", "reconciliation", "regulatory",
    "retention", "revenue", "sla", "schema", "security", "service_taxonomy",
    "strategy", "talent", "threshold", "training", "valuation", "vendor_risk",
)

CONFIDENCE_GATE = 0.8
DEDUP_COSINE_THRESHOLD = 0.92


@dataclass(frozen=True)
class RawFact:
    """Intermediate shape before YAML serialisation — includes confidence so
    we can apply the gate and optionally log borderline facts."""
    id: str
    text: str
    source: str
    categories: tuple[str, ...]
    confidence: float
    origin: str  # "auto_pdf" | "auto_schema"

    def to_yaml_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "categories": list(self.categories),
            "origin": self.origin,
            "confidence": round(self.confidence, 3),
        }


def _fact_id(text: str, prefix: str) -> str:
    """Stable ID derived from content — same text → same ID across re-runs."""
    return f"{prefix}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:10].upper()}"


# ---------- PDF chunk extraction (LLM-driven) ----------

def extract_facts_from_chunk(chunk: PDFChunk) -> list[RawFact]:
    """One LLM call per chunk. Returns validated, confidence-gated facts."""
    client = get_openai_client()
    model = get_model_name()

    user_msg = (
        f"chunk_id: {chunk.chunk_id}\n"
        f"section: §{chunk.section_num} {chunk.section_title}\n"
        f"document: {chunk.doc_name}\n\n"
        f"Allowed categories: {', '.join(ALLOWED_CATEGORIES)}\n\n"
        f"Chunk text:\n---\n{chunk.raw_text}\n---\n\n"
        "Extract atomic facts per the instructions. JSON only."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": FACT_EXTRACTION_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("fact_extraction JSON parse failed for %s: %s", chunk.chunk_id, e)
        return []

    raw_facts = payload.get("facts") or []
    out: list[RawFact] = []
    for f in raw_facts:
        text = str(f.get("text", "")).strip()
        if not text:
            continue
        confidence = float(f.get("confidence", 0.0))
        if confidence < CONFIDENCE_GATE:
            logger.debug("fact below confidence gate (%.2f): %s", confidence, text[:80])
            continue
        cats = [c for c in (f.get("categories") or []) if c in ALLOWED_CATEGORIES]
        if not cats:
            logger.debug("fact has no allow-listed categories: %s", text[:80])
            continue
        out.append(RawFact(
            id=_fact_id(text, "F-AUTO"),
            text=text,
            source=chunk.chunk_id,
            categories=tuple(cats),
            confidence=confidence,
            origin="auto_pdf",
        ))
    logger.info("extracted %d facts from %s", len(out), chunk.chunk_id)
    return out


# ---------- DuckDB schema-fact extraction (deterministic, no LLM) ----------

def extract_schema_facts(con, table_name: str) -> list[RawFact]:
    """Extract row counts, categorical enumerations, and NOT-NULL observations
    from a DuckDB table. Deterministic — no LLM call."""
    facts: list[RawFact] = []

    # 1. Row count fact.
    n = con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
    t = f"Table `{table_name}` has {n} rows."
    facts.append(RawFact(
        id=_fact_id(t, "F-AUTO"),
        text=t, source=table_name,
        categories=("data_model", "schema"),
        confidence=1.0, origin="auto_schema",
    ))

    # 2. Categorical column enumerations (VARCHAR cols with 2-10 distinct values).
    cols = con.execute(f'DESCRIBE "{table_name}"').fetchall()
    for col_row in cols:
        col_name = col_row[0]
        col_type = str(col_row[1]).lower()
        if "varchar" not in col_type:
            continue
        try:
            distinct = con.execute(
                f'SELECT DISTINCT "{col_name}" FROM "{table_name}" '
                f'WHERE "{col_name}" IS NOT NULL '
                f'ORDER BY 1 LIMIT 12'
            ).fetchall()
        except Exception:  # noqa: BLE001
            continue
        if 2 <= len(distinct) <= 10:
            values_str = ", ".join(f"'{v[0]}'" for v in distinct)
            t = f"Column `{table_name}.{col_name}` has actual values: {values_str}."
            cat_hints = ["data_model", "schema"]
            if "transaction" in table_name or "financial" in table_name:
                cat_hints.append("finance_query")
            if "risk" in col_name or "status" in col_name:
                cat_hints.append("vendor_risk" if "vendor" in table_name else "compliance")
            facts.append(RawFact(
                id=_fact_id(t, "F-AUTO"),
                text=t, source=table_name,
                categories=tuple(cat_hints),
                confidence=1.0, origin="auto_schema",
            ))

    logger.info("extracted %d schema facts from %s", len(facts), table_name)
    return facts


# ---------- Dedup + merge pass ----------

def dedup_facts(all_facts: list[RawFact]) -> list[RawFact]:
    """Collapse near-duplicates by embedding cosine similarity. When two facts
    are near-identical, keep the higher-confidence one but UNION their sources
    so both chunks remain discoverable."""
    if len(all_facts) <= 1:
        return list(all_facts)

    logger.info("dedup pass over %d candidate facts...", len(all_facts))
    embedder = get_embedder()
    texts = [f.text for f in all_facts]
    vecs = embedder.embed_documents(texts)
    # L2-normalised embeddings from nomic; so dot product = cosine similarity.
    mat = np.asarray(vecs)

    kept: list[RawFact] = []
    merged_into: set[int] = set()

    for i in range(len(all_facts)):
        if i in merged_into:
            continue
        f_i = all_facts[i]
        dup_indices: list[int] = []
        for j in range(i + 1, len(all_facts)):
            if j in merged_into:
                continue
            sim = float(mat[i] @ mat[j])
            if sim >= DEDUP_COSINE_THRESHOLD:
                dup_indices.append(j)
        if dup_indices:
            all_sources = [f_i.source] + [all_facts[j].source for j in dup_indices]
            # Pick the fact with highest confidence as the "canonical" text.
            candidates = [f_i] + [all_facts[j] for j in dup_indices]
            canonical = max(candidates, key=lambda f: f.confidence)
            merged_cats = tuple(sorted({c for f in candidates for c in f.categories}))
            merged_source = " | ".join(sorted(set(all_sources)))
            kept.append(RawFact(
                id=canonical.id,
                text=canonical.text,
                source=merged_source,
                categories=merged_cats,
                confidence=canonical.confidence,
                origin=canonical.origin,
            ))
            merged_into.update(dup_indices)
        else:
            kept.append(f_i)

    logger.info("dedup complete: %d → %d facts", len(all_facts), len(kept))
    return kept


# ---------- YAML serialiser ----------

def write_auto_facts(facts: Iterable[RawFact], path: str) -> None:
    payload = {"facts": [f.to_yaml_dict() for f in facts]}
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True, width=120)
    logger.info("wrote %s", path)
