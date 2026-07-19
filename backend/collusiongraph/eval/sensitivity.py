"""Protocol-sensitivity curves (§7 step 29 iii) over a STORED alert queue.

One config = one sweep: the §4.5 alert pipeline (NMS dedup → hit rule →
budget metrics) re-runs on the SAME ``alerts.parquet`` + labels artifacts for
every grid point of ``jaccard_thresholds`` × ``min_fractions`` — nothing
retrains, node-level protocol is untouched, and the published setting
(jaccard 0.5, min_fraction null) is just one grid point, so the sweep
contextualizes the headline numbers instead of replacing them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

import polars as pl

from collusiongraph.schema import GraphStore

from .alert_unit import DEFAULT_MAX_MEMBERS, apply_hit_rule, nms_dedup
from .metrics import alert_queue_metrics, illicit_coverage_at_budget
from .report import load_config, resolve_budgets


def run_sensitivity(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    dataset: str = cfg["dataset"]
    store = GraphStore(cfg.get("store_root", "data/interim"))
    alerts = pl.read_parquet(cfg["alerts"])
    labels = pl.read_parquet(cfg["labels"]) if "labels" in cfg else store.read(dataset, "labels")
    raw_budgets: list[int | str] = cfg["budgets"]
    sweep = cfg.get("sweep", {})
    jaccard_thresholds = [float(t) for t in sweep.get("jaccard_thresholds", [0.5])]
    # None = the published ≥1-confirmed-member rule; floats are the stricter
    # Phase-2 fractional rules (§4.5)
    min_fractions = [None if f is None else float(f) for f in sweep.get("min_fractions", [None])]
    max_members = int(cfg.get("max_members", DEFAULT_MAX_MEMBERS))

    rows: list[dict[str, Any]] = []
    for jt, mf in product(jaccard_thresholds, min_fractions):
        dedup = nms_dedup(alerts, jaccard_threshold=jt, max_members=max_members)
        queue = apply_hit_rule(dedup.kept, labels, min_confirmed=1, min_fraction=mf)
        budgets = resolve_budgets(raw_budgets, queue.height)
        rows.append(
            {
                "jaccard_threshold": jt,
                "min_fraction": mf,
                "n_kept": dedup.report["n_kept"],
                "n_suppressed": dedup.report["n_suppressed"],
                "n_hits_total": int(queue["is_hit"].sum()),
                "queue": alert_queue_metrics(queue, budgets),
                "illicit_coverage": illicit_coverage_at_budget(queue, labels, budgets),
            }
        )

    report = {
        "kind": "alert_sensitivity",
        "dataset": dataset,
        "created_at": datetime.now(UTC).isoformat(),
        "alerts": str(cfg["alerts"]),
        "budgets": raw_budgets,
        "grid": {
            "jaccard_thresholds": jaccard_thresholds,
            "min_fractions": min_fractions,
        },
        "results": rows,
    }
    out_dir = Path(cfg.get("output_dir", f"eval_outputs/{dataset}/sensitivity"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sensitivity.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
