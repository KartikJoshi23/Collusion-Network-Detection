"""
End-to-end ingestion pipeline for the 10 TechNova PDFs.

For each PDF:
  1. Extract text via pdfplumber (`pdf_chunker.extract_full_text`)
  2. Split on numbered section headings (`pdf_chunker.split_into_sections`)
  3. Contextual retrieval (Anthropic technique): an LLM writes 1-2 sentences
     describing each chunk's place in the overall document. That prefix is
     prepended to the chunk text before embedding, which dramatically improves
     retrieval recall on cross-section queries.
  4. Embed (contextual_text + raw_text) with nomic-embed-text-v1.5.
  5. Upsert to Qdrant with full payload (chunk_id, doc, section, raw_text,
     contextual_text) so downstream retrieval can return the original content.

Idempotent: re-running the script re-generates contexts and overwrites points
with the same id. Run via `make ingest`.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient, models as qm

from app.config import get_settings
from app.data.embeddings import get_embedder
from app.data.fact_extraction import (
    RawFact,
    dedup_facts,
    extract_facts_from_chunk,
    extract_schema_facts,
    write_auto_facts,
)
from app.data.pdf_chunker import PDFChunk, chunk_pdf

logger = logging.getLogger(__name__)

CONTEXTUAL_PROMPT = (
    "<document>\n{document}\n</document>\n\n"
    "Here is a chunk from the document:\n"
    "<chunk>\n{chunk}\n</chunk>\n\n"
    "Write a short (1-2 sentence) context that situates this chunk within the "
    "overall document, for the purpose of improving search retrieval. "
    "Reply with only the context sentence(s). No preamble, no quotes, no bullets."
)


def _point_id(chunk_id: str) -> int:
    """Derive a stable 60-bit int from the chunk_id for use as a Qdrant point id."""
    digest = hashlib.sha256(chunk_id.encode()).hexdigest()
    return int(digest[:15], 16)


def _generate_context(full_doc: str, chunk_text: str, client: OpenAI, model: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": CONTEXTUAL_PROMPT.format(document=full_doc, chunk=chunk_text),
            }
        ],
        max_completion_tokens=160,
    )
    content = resp.choices[0].message.content or ""
    return content.strip()


def ensure_collection(client: QdrantClient, name: str, vector_size: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        logger.info("Qdrant collection '%s' already exists (skipping create).", name)
        return
    logger.info("Creating Qdrant collection '%s' (dim=%s, cosine).", name, vector_size)
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )


def ingest_all_pdfs() -> dict[str, int]:
    settings = get_settings()
    source_dir = Path(settings.unstructured_data_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Unstructured data dir not found: {source_dir}")
    pdfs = sorted(source_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs in {source_dir}")

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Populate backend/.env before running ingestion."
        )

    openai = OpenAI(api_key=settings.openai_api_key)
    qdrant = QdrantClient(url=settings.qdrant_url)
    embedder = get_embedder()

    ensure_collection(qdrant, settings.qdrant_collection, embedder.dim)

    counts: dict[str, int] = {}
    all_raw_facts: list[RawFact] = []

    for pdf_path in pdfs:
        logger.info("Processing %s", pdf_path.name)
        chunks: list[PDFChunk] = chunk_pdf(pdf_path)
        logger.info("  -> %s sections", len(chunks))

        full_doc_text = "\n\n".join(c.raw_text for c in chunks)
        for c in chunks:
            c.contextual_text = _generate_context(
                full_doc_text, c.raw_text, openai, settings.openai_model_name
            )
            logger.debug("Context for %s: %s", c.chunk_id, c.contextual_text)

        embed_inputs = [f"{c.contextual_text}\n\n{c.raw_text}" for c in chunks]
        vectors = embedder.embed_documents(embed_inputs)

        points = [
            qm.PointStruct(
                id=_point_id(c.chunk_id),
                vector=vectors[i].tolist(),
                payload={
                    "chunk_id": c.chunk_id,
                    "doc_name": c.doc_name,
                    "section_num": c.section_num,
                    "section_title": c.section_title,
                    "raw_text": c.raw_text,
                    "contextual_text": c.contextual_text,
                },
            )
            for i, c in enumerate(chunks)
        ]
        qdrant.upsert(collection_name=settings.qdrant_collection, points=points)
        counts[pdf_path.name] = len(chunks)
        logger.info("  -> upserted %s points", len(points))

        # FactForge: extract atomic facts from each chunk (one LLM call per chunk).
        for c in chunks:
            try:
                all_raw_facts.extend(extract_facts_from_chunk(c))
            except Exception as e:  # noqa: BLE001
                logger.warning("fact extraction failed for %s: %s", c.chunk_id, e)

    # Also extract schema facts from the DuckDB tables (deterministic, no LLM).
    try:
        from app.data.duckdb_loader import get_connection, list_tables
        con = get_connection(read_only=True)
        try:
            for t in list_tables():
                all_raw_facts.extend(extract_schema_facts(con, t))
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("schema fact extraction failed: %s", e)

    # Dedup across the whole corpus (PDF facts + schema facts).
    deduped = dedup_facts(all_raw_facts)

    # Write to facts_auto.yaml, sibling of facts_curated.yaml.
    auto_path = Path(__file__).parent / "facts_auto.yaml"
    write_auto_facts(deduped, str(auto_path))
    logger.info(
        "FactForge: %d PDFs → %d raw facts → %d after dedup → %s",
        len(pdfs), len(all_raw_facts), len(deduped), auto_path.name,
    )

    return counts


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    counts = ingest_all_pdfs()
    print("Ingested PDFs:")
    for name, n in sorted(counts.items()):
        print(f"  {name:<50} {n:>3} chunks")
    total = sum(counts.values())
    print(f"  {'TOTAL':<50} {total:>3} chunks")


if __name__ == "__main__":
    main()
