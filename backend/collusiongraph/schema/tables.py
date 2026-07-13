"""IR table schemas (pyarrow) + row models (Pydantic) — implementation-plan.md §4.2, §3.2.

Conventions
-----------
* ``time`` values are int64 in a **dataset-specific unit** recorded in the dataset
  meta (``time_unit``): Elliptic uses its 1–49 time step, AMLworld uses epoch
  minutes, procurement uses the year (or epoch days where full dates exist).
  Splitters and features treat time as an opaque ordered integer.
* ``raw_features`` carries the dataset's own per-node feature vector (nullable —
  procurement nodes have none); the *shared structural template* of §4.2 rule 2
  is computed later by ``features/`` and stored separately, never here.
* ``raw_attrs`` is a JSON object string for anything domain-specific we must not
  lose but no downstream component may depend on.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa
from pydantic import BaseModel, Field, field_validator

from collusiongraph import SCREENING_CAVEAT

from .types import Domain, EdgeType, Label, MotifType, NodeType

NODES_SCHEMA = pa.schema(
    [
        pa.field("node_id", pa.string(), nullable=False),
        pa.field("node_type", pa.string(), nullable=False),
        pa.field("domain", pa.string(), nullable=False),
        pa.field("time_first_seen", pa.int64()),
        pa.field("raw_features", pa.list_(pa.float32())),
        pa.field("raw_attrs", pa.string()),
    ]
)

EDGES_SCHEMA = pa.schema(
    [
        pa.field("src", pa.string(), nullable=False),
        pa.field("dst", pa.string(), nullable=False),
        pa.field("edge_type", pa.string(), nullable=False),
        pa.field("timestamp", pa.int64()),
        pa.field("amount", pa.float64()),
        pa.field("directed", pa.bool_(), nullable=False),
        pa.field("raw_attrs", pa.string()),
    ]
)

LABELS_SCHEMA = pa.schema(
    [
        pa.field("node_id", pa.string(), nullable=False),
        pa.field("label", pa.string(), nullable=False),
        pa.field("label_source", pa.string(), nullable=False),
        pa.field("confidence", pa.float32(), nullable=False),
    ]
)

COMMUNITIES_SCHEMA = pa.schema(
    [
        pa.field("community_id", pa.string(), nullable=False),
        pa.field("member_node_ids", pa.list_(pa.string()), nullable=False),
        pa.field("method", pa.string(), nullable=False),
    ]
)

# §3.2 — "the alert is the system's central artifact"
ALERTS_SCHEMA = pa.schema(
    [
        pa.field("alert_id", pa.string(), nullable=False),
        pa.field("domain", pa.string(), nullable=False),
        pa.field("dataset", pa.string(), nullable=False),
        pa.field("model_run_id", pa.string(), nullable=False),
        pa.field("rank", pa.int32(), nullable=False),
        pa.field("risk_score", pa.float64(), nullable=False),
        pa.field("community_id", pa.string()),
        pa.field("member_node_ids", pa.list_(pa.string()), nullable=False),
        pa.field("anchor_nodes", pa.list_(pa.string())),
        pa.field("anchor_edges", pa.list_(pa.string())),  # "src->dst@timestamp" keys
        pa.field("time_window_start", pa.int64()),
        pa.field("time_window_end", pa.int64()),
        pa.field("motif_type", pa.string()),
        pa.field("n_members", pa.int32(), nullable=False),
        pa.field("overlap_group", pa.int32()),
        pa.field("explanation_ref", pa.string()),
        pa.field("created_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("caveats", pa.string(), nullable=False),
    ]
)

TABLE_SCHEMAS: dict[str, pa.Schema] = {
    "nodes": NODES_SCHEMA,
    "edges": EDGES_SCHEMA,
    "labels": LABELS_SCHEMA,
    "communities": COMMUNITIES_SCHEMA,
    "alerts": ALERTS_SCHEMA,
}


class Node(BaseModel):
    node_id: str
    node_type: NodeType
    domain: Domain
    time_first_seen: int | None = None
    raw_features: list[float] | None = None
    raw_attrs: str | None = None


class Edge(BaseModel):
    src: str
    dst: str
    edge_type: EdgeType
    timestamp: int | None = None
    amount: float | None = None
    directed: bool = True
    raw_attrs: str | None = None


class LabelRow(BaseModel):
    node_id: str
    label: Label
    label_source: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class Community(BaseModel):
    community_id: str
    member_node_ids: list[str]
    method: str


class Alert(BaseModel):
    """§3.2 alert schema. ``caveats`` is immutable by construction (R11)."""

    alert_id: str
    domain: Domain
    dataset: str
    model_run_id: str
    rank: int = Field(ge=1)
    risk_score: float
    community_id: str | None = None
    member_node_ids: list[str]
    anchor_nodes: list[str] | None = None
    anchor_edges: list[str] | None = None
    time_window_start: int | None = None
    time_window_end: int | None = None
    motif_type: MotifType | None = None
    n_members: int = Field(ge=1)
    overlap_group: int | None = None
    explanation_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    caveats: str = SCREENING_CAVEAT

    @field_validator("caveats")
    @classmethod
    def _caveat_is_fixed(cls, v: str) -> str:
        if v != SCREENING_CAVEAT:
            raise ValueError(
                "the alert caveat is a fixed screening-only string and must not be altered"
            )
        return v
