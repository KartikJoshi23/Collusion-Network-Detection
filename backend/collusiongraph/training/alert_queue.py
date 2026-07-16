"""End-to-end alert queue (§7 step 13 → M2): scores → calibration → Leiden →
roll-up → alerts → alert-level metrics.

Operational framing: the queue covers the TEST window (the batch an
investigator would triage) — communities are detected on the test-period
subgraph, member scores are isotonic-calibrated on the validation pool, and
the harness evaluates the deduplicated queue against test-window labels only
(coverage denominators match the queue's scope; train-period history is not
this queue's job).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from collusiongraph.artifacts.alert_store import build_alerts
from collusiongraph.eval import load_config, run_eval
from collusiongraph.models.rollup import community_scores, isotonic_calibrator, leiden_communities
from collusiongraph.schema import GraphStore, Label

_TIME = "time_first_seen"


def build_alert_queue(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    run_dir = Path(cfg["scores_dir"])  # a train_gnn output dir
    out_dir = Path(cfg.get("output_dir", str(run_dir / "alerts")))
    test_start: int = cfg["split"]["test_start"]
    seed: int = cfg.get("seed", 0)

    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")

    test_nodes = nodes.filter(pl.col(_TIME).is_not_null() & (pl.col(_TIME) >= test_start))
    kept = test_nodes["node_id"].implode()
    test_edges = edges.filter(pl.col("src").is_in(kept) & pl.col("dst").is_in(kept))

    if cfg.get("precalibrated", False):
        # e.g. the calibrated-fusion ensemble: scores are already probabilities
        calibrated = pl.read_parquet(run_dir / cfg["scores_file"])
    else:
        # calibrate on the validation pool (never test), apply to test scores
        val_scores = pl.read_parquet(run_dir / "scores_val.parquet").join(
            labels.filter(pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])).select(
                "node_id", (pl.col("label") == Label.ILLICIT.value).cast(pl.Int8).alias("y")
            ),
            on="node_id",
            how="inner",
        )
        calibrator = isotonic_calibrator(val_scores["score"].to_numpy(), val_scores["y"].to_numpy())
        test_scores = pl.read_parquet(run_dir / "scores_test.parquet")
        calibrated = test_scores.with_columns(
            pl.Series("score", calibrator.predict(test_scores["score"].to_numpy()))
        )

    communities = leiden_communities(
        test_nodes,
        test_edges,
        seed=seed,
        resolution=cfg.get("resolution", 1.0),
        min_size=cfg.get("min_community_size", 2),
    )
    scored = community_scores(communities, calibrated, top_p=cfg.get("top_p", 0.25))
    alerts = build_alerts(
        scored,
        test_nodes,
        dataset=dataset,
        domain=cfg["domain"],
        model_run_id=cfg.get("model_run_id", "gnn"),
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    alerts_path = out_dir / "alerts.parquet"
    alerts.write_parquet(alerts_path)
    test_labels_path = out_dir / "labels_test_window.parquet"
    labels.filter(pl.col("node_id").is_in(kept)).write_parquet(test_labels_path)

    metrics = run_eval(
        {
            "dataset": dataset,
            "store_root": str(store.root),
            "budgets": cfg["budgets"],
            "alerts": str(alerts_path),
            "labels": str(test_labels_path),
            "alert_unit": cfg.get("alert_unit", {}),
            "hit_rule": cfg.get("hit_rule", {}),
            "output_dir": str(out_dir),
        }
    )
    summary = {
        "dataset": dataset,
        "n_test_nodes": test_nodes.height,
        "n_test_edges": test_edges.height,
        "n_communities": communities.height,
        "n_alerts": alerts.height,
        "dedup": metrics.get("dedup"),
        "alert_level": metrics.get("alert_level"),
    }
    (out_dir / "queue_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary
