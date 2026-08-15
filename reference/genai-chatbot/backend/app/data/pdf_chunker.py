"""
Section-based chunker for TechNova PDFs.

Every PDF in the corpus follows the same structure:
  - Header (title, department, version)
  - Numbered sections: "1. Section Title\\n...\\n2. Section Title\\n..."
  - Copyright footer.

Chunking on these numbered boundaries keeps each chunk semantically coherent
and small enough for the 8K-context embedder to handle even with the contextual
retrieval prefix. For the 10 PDFs in the corpus this produces ~40-50 chunks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)

# Matches "1. Title Line" or "2. Title", etc. at the start of a line.
# Requires the leading whitespace boundary to avoid matching references like
# "page 3. Something" mid-paragraph.
_SECTION_HEADING = re.compile(
    r"^\s*(\d+)\.\s+([A-Z][^\n]{3,100})\s*$",
    re.MULTILINE,
)

_COPYRIGHT_LINE = re.compile(
    r"Copyright\s+\d{4}(-\d{4})?\s+TechNova\s+Inc\..*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class PDFChunk:
    doc_name: str          # "TechNova_Platform_Architecture.pdf"
    section_num: int       # 1, 2, 3, ...
    section_title: str     # "System Overview"
    raw_text: str          # section body (heading included)
    contextual_text: str = ""  # populated later by pdf_ingestion.py

    @property
    def chunk_id(self) -> str:
        # Stable, human-readable, unique.
        return f"{self.doc_name}::sec{self.section_num}"


def extract_full_text(pdf_path: Path) -> str:
    """Extract all text from a PDF, preserving line breaks."""
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parts.append(text)
    return "\n".join(parts)


def _strip_copyright(text: str) -> str:
    return _COPYRIGHT_LINE.sub("", text).rstrip()


def split_into_sections(full_text: str, doc_name: str) -> list[PDFChunk]:
    """Split the full PDF text on numbered section headings.

    If no numbered headings match, return a single chunk covering the entire
    document (graceful degradation).
    """
    full_text = _strip_copyright(full_text)

    matches = list(_SECTION_HEADING.finditer(full_text))
    if not matches:
        logger.warning(
            "No numbered sections found in %s; treating entire document as one chunk.",
            doc_name,
        )
        return [
            PDFChunk(
                doc_name=doc_name,
                section_num=1,
                section_title="Full document",
                raw_text=full_text.strip(),
            )
        ]

    chunks: list[PDFChunk] = []
    for i, m in enumerate(matches):
        section_num = int(m.group(1))
        section_title = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[start:end].strip()
        chunks.append(
            PDFChunk(
                doc_name=doc_name,
                section_num=section_num,
                section_title=section_title,
                raw_text=body,
            )
        )
    return chunks


def chunk_pdf(pdf_path: Path) -> list[PDFChunk]:
    text = extract_full_text(pdf_path)
    return split_into_sections(text, pdf_path.name)
