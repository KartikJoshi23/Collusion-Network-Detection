"""
CPU-only embedder wrapper around nomic-embed-text-v1.5.

Nomic requires task-specific prefixes:
  - `search_document: <text>` for corpus documents before indexing
  - `search_query:    <text>` for user queries at search time
Using the wrong prefix degrades retrieval quality noticeably, hence the two
separate methods.

The first instantiation downloads ~550 MB to the HuggingFace cache volume.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)


class NomicEmbedder:
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        logger.info("Loading embedder '%s' on %s", model_name, device)
        self.model = SentenceTransformer(
            model_name,
            device=device,
            trust_remote_code=True,
        )
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        prefixed = [f"search_document: {t}" for t in texts]
        return self.model.encode(
            prefixed,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def embed_query(self, text: str) -> np.ndarray:
        prefixed = f"search_query: {text}"
        return self.model.encode(
            prefixed,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )


@lru_cache(maxsize=1)
def get_embedder() -> NomicEmbedder:
    settings = get_settings()
    return NomicEmbedder(settings.embedding_model)
