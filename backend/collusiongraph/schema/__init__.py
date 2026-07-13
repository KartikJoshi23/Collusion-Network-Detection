"""CollusionGraph IR: Pydantic models, Parquet schemas, DuckDB catalog, alerts (§4.2, §3.2)."""

from .store import GraphStore, SchemaError, conform
from .tables import (
    ALERTS_SCHEMA,
    COMMUNITIES_SCHEMA,
    EDGES_SCHEMA,
    LABELS_SCHEMA,
    NODES_SCHEMA,
    TABLE_SCHEMAS,
    Alert,
    Community,
    Edge,
    LabelRow,
    Node,
)
from .types import Domain, EdgeType, Label, MotifType, NodeType

__all__ = [
    "ALERTS_SCHEMA",
    "COMMUNITIES_SCHEMA",
    "EDGES_SCHEMA",
    "LABELS_SCHEMA",
    "NODES_SCHEMA",
    "TABLE_SCHEMAS",
    "Alert",
    "Community",
    "Domain",
    "Edge",
    "EdgeType",
    "GraphStore",
    "Label",
    "LabelRow",
    "MotifType",
    "Node",
    "NodeType",
    "SchemaError",
    "conform",
]
