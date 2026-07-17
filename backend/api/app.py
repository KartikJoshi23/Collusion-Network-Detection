"""FastAPI serving layer (§7 step 22, §3.2): read-only precomputed artifacts.

Endpoints (all JSON, all carrying the immutable screening-only caveat — R11):

    GET /api/v1/domains
    GET /api/v1/datasets
    GET /api/v1/datasets/{ds}/alerts?budget=k
    GET /api/v1/datasets/{ds}/alerts/{alert_id}
    GET /api/v1/datasets/{ds}/subgraph/{alert_id}?hops=1&node_cap=2000
    GET /api/v1/datasets/{ds}/explanations/{alert_id}
    GET /api/v1/datasets/{ds}/metrics

Subgraph payloads are windowed server-side (§5.4): the alert's members plus a
bounded neighbor hop, node-capped — the browser never receives a full graph.
No GPU, no torch, no writes anywhere in the request path.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import polars as pl
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.schema import GraphStore
from fastapi import FastAPI, HTTPException, Query

from .serving import ServingEntry, ServingIndex

DEFAULT_INDEX = "eval_outputs/serving.json"
_ALERT_LIST_COLS = [
    "alert_id",
    "rank",
    "risk_score",
    "n_members",
    "motif_type",
    "time_window_start",
    "time_window_end",
    "community_id",
]


def _rows(df: pl.DataFrame) -> list[dict]:
    return json.loads(df.write_json())


def create_app(index_path: str | Path | None = None) -> FastAPI:
    index_path = index_path or os.environ.get("COLLUSIONGRAPH_SERVING", DEFAULT_INDEX)
    index = ServingIndex.from_file(index_path)
    app = FastAPI(
        title="CollusionGraph API",
        description="Read-only screening artifacts. " + SCREENING_CAVEAT,
        version="0.1.0",
    )

    def entry_or_404(dataset: str) -> ServingEntry:
        entry = index.get(dataset)
        if entry is None:
            raise HTTPException(404, f"unknown dataset {dataset!r}")
        return entry

    def alerts_or_404(entry: ServingEntry) -> pl.DataFrame:
        if not entry.alerts or not Path(entry.alerts).is_file():
            raise HTTPException(404, f"no alert queue published for {entry.dataset!r}")
        return pl.read_parquet(entry.alerts)

    @app.get("/api/v1/domains")
    def domains() -> dict:
        return {"domains": index.domains(), "caveat": SCREENING_CAVEAT}

    @app.get("/api/v1/datasets")
    def datasets() -> dict:
        out = []
        for name, entry in sorted(index.entries.items()):
            out.append(
                {
                    "dataset": name,
                    "domain": entry.domain,
                    "has_alerts": bool(entry.alerts and Path(entry.alerts).is_file()),
                    "has_explanations": bool(
                        entry.explanations and Path(entry.explanations).is_dir()
                    ),
                    "n_metrics_files": sum(1 for m in entry.metrics if Path(m).is_file()),
                }
            )
        return {"datasets": out, "caveat": SCREENING_CAVEAT}

    @app.get("/api/v1/datasets/{dataset}/alerts")
    def alerts(dataset: str, budget: int = Query(default=50, ge=1, le=500)) -> dict:
        entry = entry_or_404(dataset)
        frame = alerts_or_404(entry).sort("rank")
        top = frame.head(budget)
        return {
            "dataset": dataset,
            "budget": budget,
            "k_effective": top.height,
            "alerts": _rows(top.select([c for c in _ALERT_LIST_COLS if c in top.columns])),
            "caveat": SCREENING_CAVEAT,
        }

    @app.get("/api/v1/datasets/{dataset}/alerts/{alert_id}")
    def alert_detail(dataset: str, alert_id: str) -> dict:
        entry = entry_or_404(dataset)
        row = alerts_or_404(entry).filter(pl.col("alert_id") == alert_id)
        if row.height == 0:
            raise HTTPException(404, f"unknown alert {alert_id!r}")
        return {"alert": _rows(row)[0], "caveat": SCREENING_CAVEAT}

    @app.get("/api/v1/datasets/{dataset}/subgraph/{alert_id}")
    def subgraph(
        dataset: str,
        alert_id: str,
        hops: int = Query(default=1, ge=0, le=2),
        node_cap: int = Query(default=2000, ge=10, le=5000),
    ) -> dict:
        entry = entry_or_404(dataset)
        row = alerts_or_404(entry).filter(pl.col("alert_id") == alert_id)
        if row.height == 0:
            raise HTTPException(404, f"unknown alert {alert_id!r}")
        members: list[str] = row["member_node_ids"].to_list()[0]

        store = GraphStore(entry.store_root)
        edges_lf = pl.scan_parquet(store.dataset_dir(entry.dataset) / "edges.parquet")
        keep = set(members)
        truncated = False
        for _ in range(hops):
            ids = pl.Series(sorted(keep)).implode()
            hop = (
                edges_lf.filter(pl.col("src").is_in(ids) | pl.col("dst").is_in(ids))
                .select("src", "dst")
                .collect()
            )
            neighbors = set(hop["src"].to_list()) | set(hop["dst"].to_list())
            new = sorted(neighbors - keep)
            room = node_cap - len(keep)
            if len(new) > room:
                new, truncated = new[:room], True
            keep |= set(new)
            if truncated:
                break

        ids = pl.Series(sorted(keep)).implode()
        sub_edges = (
            edges_lf.filter(pl.col("src").is_in(ids) & pl.col("dst").is_in(ids))
            .select("src", "dst", "edge_type", "timestamp", "amount")
            .collect()
        )
        sub_nodes = (
            pl.scan_parquet(store.dataset_dir(entry.dataset) / "nodes.parquet")
            .filter(pl.col("node_id").is_in(ids))
            .select("node_id", "node_type", "time_first_seen")  # never raw_features (§5.4)
            .collect()
            .with_columns(pl.col("node_id").is_in(pl.Series(members).implode()).alias("is_member"))
        )
        return {
            "alert_id": alert_id,
            "hops": hops,
            "truncated": truncated,
            "nodes": _rows(sub_nodes),
            "edges": _rows(sub_edges),
            "caveat": SCREENING_CAVEAT,
        }

    @app.get("/api/v1/datasets/{dataset}/explanations/{alert_id}")
    def explanation(dataset: str, alert_id: str) -> dict:
        entry = entry_or_404(dataset)
        if not entry.explanations:
            raise HTTPException(404, f"no explanations published for {dataset!r}")
        # Audit 2026-07-17: alert ids map to filenames — an unvalidated id could
        # traverse out of the bundles dir (proven with a backslash on Windows).
        # Allowlist + resolved-path containment, defense in depth.
        if not re.fullmatch(r"[A-Za-z0-9:_\-.]+", alert_id):
            raise HTTPException(404, f"no bundle for alert {alert_id!r}")
        base = Path(entry.explanations).resolve()
        path = (base / f"{alert_id.replace(':', '_')}.json").resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise HTTPException(404, f"no bundle for alert {alert_id!r}")
        return {"bundle": json.loads(path.read_text(encoding="utf-8")), "caveat": SCREENING_CAVEAT}

    @app.get("/api/v1/datasets/{dataset}/metrics")
    def metrics(dataset: str) -> dict:
        entry = entry_or_404(dataset)
        out = []
        for m in entry.metrics:
            path = Path(m)
            if path.is_file():
                out.append({"source": m, "metrics": json.loads(path.read_text(encoding="utf-8"))})
        if not out:
            raise HTTPException(404, f"no metrics published for {dataset!r}")
        return {"dataset": dataset, "runs": out, "caveat": SCREENING_CAVEAT}

    return app
