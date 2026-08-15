"""FastAPI serving layer — read-only, precomputed artifacts (§3.2)."""

from .app import create_app
from .serving import ServingEntry, ServingIndex, write_serving_index

__all__ = ["ServingEntry", "ServingIndex", "create_app", "write_serving_index"]
