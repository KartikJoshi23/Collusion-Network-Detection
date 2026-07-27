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
from functools import lru_cache
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


@lru_cache(maxsize=16)
def _bundle_motifs(explanations_dir: str) -> dict[str, str]:
    """alert_id -> proven motif name, read from the published bundles.

    WHY THIS JOIN EXISTS. The alert queue is written by the ranking stage, which
    runs BEFORE the explanation stage — so `motif_type` in `alerts.parquet` is
    null on every row, even for the alerts the matcher later proved a shape for.
    Measured 2026-07-27: 12 of the first 40 Elliptic bundles carry `fan_in` /
    `fan_out`, while all 254 queue rows reported nothing, which made the
    dashboard's Pattern column read empty on every dataset and look broken.

    Rather than regenerate every stored queue, the two published artifacts are
    joined here at read time. Nothing is invented: the motif comes from the same
    bundle the /explanations endpoint already serves. Bundles exist only for the
    head of the queue, so this scan is small. The proper long-term fix is for
    the ranking stage to back-fill the column once explanations exist.
    """
    base = Path(explanations_dir)
    if not base.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in base.glob("*.json"):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # a malformed bundle must never take the queue down
        motif = bundle.get("motif")
        if not isinstance(motif, dict):
            continue
        # bundles.py writes {"type": ...}; the schema calls it motif_type
        name = motif.get("motif_type") or motif.get("type")
        alert_id = bundle.get("alert_id")
        if name and isinstance(alert_id, str):
            out[alert_id] = str(name)
    return out


@lru_cache(maxsize=8)
def _matched_motifs(alerts_path: str, store_root: str, dataset: str, domain: str) -> dict[str, str]:
    """alert_id -> proven motif name, for EVERY alert in the queue.

    WHY THIS EXISTS. Naming the pattern was previously a side effect of writing
    a full explanation bundle, and bundles are produced only for the head of the
    queue because the *learned* explainer is expensive. That left 203 of 223
    Mendeley rows and 204 of 254 Elliptic rows admitting "not checked" — an
    indefensible thing to show a reviewer, and unnecessary, because naming the
    shape does not need the learned explainer at all. The matcher is
    deterministic graph rules over the alert's own edges.

    So we run exactly what `build_bundle` runs — `match_motifs`, then the
    largest match wins — over every alert, once per dataset, cached. One pass
    over the edge table assigns each edge to the alert whose members hold both
    of its endpoints; Leiden communities are a partition, so an edge belongs to
    at most one alert.
    """
    try:
        from collusiongraph.explain import match_motifs
    except Exception:  # pragma: no cover - matcher unavailable, stay serving
        return {}

    alerts = pl.read_parquet(alerts_path, columns=["alert_id", "member_node_ids"])
    pairs = (
        alerts.explode("member_node_ids")
        .rename({"member_node_ids": "node_id"})
        .drop_nulls("node_id")
        .unique(subset=["node_id"], keep="first")  # partition: first alert wins
    )
    edges_path = GraphStore(store_root).dataset_dir(dataset) / "edges.parquet"
    if not edges_path.is_file():
        return {}

    edges = (
        pl.scan_parquet(edges_path)
        .select("src", "dst", "edge_type", "timestamp", "amount")
        .join(pairs.lazy().rename({"node_id": "src", "alert_id": "a_src"}), on="src", how="inner")
        .join(pairs.lazy().rename({"node_id": "dst", "alert_id": "a_dst"}), on="dst", how="inner")
        .filter(pl.col("a_src") == pl.col("a_dst"))
        .collect()
    )

    out: dict[str, str] = {}
    for (alert_id,), group in edges.group_by(["a_src"]):
        member_edges = group.select("src", "dst", "edge_type", "timestamp", "amount")
        try:
            matches = match_motifs(member_edges, domain)
        except Exception:
            continue  # one awkward alert must never take the queue down
        top = max(matches, key=lambda m: len(m.member_node_ids), default=None)
        if top is not None:
            out[str(alert_id)] = str(top.motif_type)
    return out


@lru_cache(maxsize=16)
def _explained_ids(explanations_dir: str) -> frozenset[str]:
    """Which alerts actually have a bundle — i.e. which ones were checked.

    Needed to keep the UI honest: "no shape was proved" and "no check was ever
    run here" are different statements, and only alerts at the head of the queue
    are explained at all.
    """
    base = Path(explanations_dir)
    if not base.is_dir():
        return frozenset()
    ids: set[str] = set()
    for path in base.glob("*.json"):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        alert_id = bundle.get("alert_id")
        if isinstance(alert_id, str):
            ids.add(alert_id)
    return frozenset(ids)


def create_app(index_path: str | Path | None = None) -> FastAPI:
    index_path = index_path or os.environ.get("COLLUSIONGRAPH_SERVING", DEFAULT_INDEX)
    index = ServingIndex.from_file(index_path)
    app = FastAPI(
        title="CollusionGraph API",
        description="Read-only screening artifacts. " + SCREENING_CAVEAT,
        version="0.1.0",
    )

    # Investigator Copilot (§4.6, Week 11): read-only conversational layer.
    # The router itself imports the LLM stack lazily, so serving works — and
    # stays torch-free — on machines with no key configured.
    from copilot.api import router as copilot_router

    app.include_router(copilot_router, prefix="/api/v1/copilot", tags=["copilot"])

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
        top = frame.head(budget).select([c for c in _ALERT_LIST_COLS if c in frame.columns])

        # Join the proven motif in from the explanation bundles, and say which
        # alerts were checked at all — see _bundle_motifs for why the stored
        # queue cannot carry this itself.
        motifs = _bundle_motifs(entry.explanations) if entry.explanations else {}
        explained = _explained_ids(entry.explanations) if entry.explanations else frozenset()
        # Every alert gets the pattern check, not just the ones with a written
        # bundle — see _matched_motifs.
        try:
            matched = _matched_motifs(entry.alerts, entry.store_root, entry.dataset, entry.domain)
        except Exception:
            matched = {}
        rows = _rows(top)
        for row in rows:
            aid = row.get("alert_id")
            if not row.get("motif_type"):
                # the bundle's own answer wins; the queue-wide run fills the rest
                row["motif_type"] = motifs.get(aid) or matched.get(aid)
            # "checked" now means the pattern matcher ran, which it does for
            # every alert — a written case file is a separate, richer thing.
            row["pattern_checked"] = True
            row["explained"] = aid in explained

        return {
            "dataset": dataset,
            "budget": budget,
            "k_effective": top.height,
            "alerts": rows,
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

    @app.get("/api/v1/datasets/{dataset}/rigor")
    def rigor(dataset: str) -> dict:
        """Phase-2 rigor artifacts (§7 steps 28–29, 32): multi-seed aggregates,
        transfer matrices, sensitivity sweeps, robustness curves, significance
        tests — whatever this machine's serving index published."""
        entry = entry_or_404(dataset)
        out = {}
        for name, source in sorted(entry.rigor.items()):
            path = Path(source)
            if path.is_file():
                out[name] = {
                    "source": source,
                    "payload": json.loads(path.read_text(encoding="utf-8")),
                }
        if not out:
            raise HTTPException(404, f"no rigor artifacts published for {dataset!r}")
        return {"dataset": dataset, "artifacts": out, "caveat": SCREENING_CAVEAT}

    @app.get("/api/v1/stress-test")
    def stress_test() -> dict:
        """Injection-recovery studies (§7 step 30): fake cartels of known
        shapes planted into a real UNLABELED network, with measured recall per
        shape. The honest answer to "how do you evaluate with no answer key" —
        hide answers you DO know and count how many come back. Read-only over
        the stored injection artifact; absent files are omitted (thin machines
        stay honest), an empty section is a normal 404."""
        studies = {}
        for name, study in sorted(index.stress_test.items()):
            path = Path(study.recovery)
            if path.is_file():
                studies[name] = {
                    "title": study.title,
                    "reproduce": study.reproduce,
                    "note": study.note,
                    "payload": json.loads(path.read_text(encoding="utf-8")),
                }
        if not studies:
            raise HTTPException(404, "no stress-test studies published on this machine")
        return {"studies": studies, "caveat": SCREENING_CAVEAT}

    return app
