"""Config-driven evaluation runs (§4.5, §3.2): one YAML = one reproducible run.

``run_eval`` takes a config (path or dict), evaluates an alert queue (and
optionally node scores) against a dataset's labels, and writes ``metrics.json``
into the run's output directory. The eval harness is the single source of
truth for every number in the paper — nothing else computes headline metrics.

W&B logging is optional and off by default; with ``WANDB_MODE=offline`` (the
``.env.example`` default) an enabled run stays local.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from collusiongraph.schema import GraphStore

from .alert_unit import (
    DEFAULT_JACCARD_THRESHOLD,
    DEFAULT_MAX_MEMBERS,
    apply_hit_rule,
    nms_dedup,
)
from .metrics import (
    alert_queue_metrics,
    auc_pr,
    confirmed_node_vectors,
    fpr_at_k,
    illicit_coverage_at_budget,
    precision_at_k,
    recall_at_k,
)

DEFAULT_BUDGETS = [50, 100, 200]


def load_config(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(config, (str, Path)):
        return yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    return config


def run_eval(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    budgets: list[int] = cfg.get("budgets", DEFAULT_BUDGETS)
    # optional override, e.g. labels restricted to the test window so coverage
    # denominators match the queue's operational scope
    labels = pl.read_parquet(cfg["labels"]) if "labels" in cfg else store.read(dataset, "labels")

    metrics: dict[str, Any] = {
        "dataset": dataset,
        "created_at": datetime.now(UTC).isoformat(),
        "config": cfg,
    }

    # Alert-level evaluation is skipped (not faked) when no alert queue exists
    # yet — node-score-only runs are the M1 baseline regime; alerts arrive with
    # the community roll-up (§7 step 13).
    alerts: pl.DataFrame | None
    if "alerts" in cfg:
        alerts = pl.read_parquet(cfg["alerts"])
    else:
        try:
            alerts = store.read(dataset, "alerts")
        except FileNotFoundError:
            alerts = None
    if alerts is not None:
        alert_cfg = cfg.get("alert_unit", {})
        hit_cfg = cfg.get("hit_rule", {})
        dedup = nms_dedup(
            alerts,
            jaccard_threshold=alert_cfg.get("jaccard_threshold", DEFAULT_JACCARD_THRESHOLD),
            max_members=alert_cfg.get("max_members", DEFAULT_MAX_MEMBERS),
        )
        queue = apply_hit_rule(
            dedup.kept,
            labels,
            min_confirmed=hit_cfg.get("min_confirmed", 1),
            min_fraction=hit_cfg.get("min_fraction"),
        )
        metrics["dedup"] = dedup.report
        metrics["alert_level"] = {
            "queue": alert_queue_metrics(queue, budgets),
            "illicit_coverage": illicit_coverage_at_budget(queue, labels, budgets),
        }

    if "node_scores" in cfg:
        scores = pl.read_parquet(cfg["node_scores"])
        y, s = confirmed_node_vectors(scores, labels)
        node_budgets = [k for k in budgets if k <= len(s)]
        metrics["node_level"] = {
            **auc_pr(y, s),
            "n_confirmed": len(y),
            **{f"precision@{k}": precision_at_k(y, s, k) for k in node_budgets},
            **{f"recall@{k}": recall_at_k(y, s, k) for k in node_budgets},
            **{f"fpr@{k}": fpr_at_k(y, s, k) for k in node_budgets},
        }

    out_dir = Path(cfg.get("output_dir", f"eval_outputs/{dataset}"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _maybe_log_wandb(metrics, cfg)
    return metrics


def _maybe_log_wandb(metrics: dict[str, Any], cfg: dict[str, Any]) -> None:
    wandb_cfg = cfg.get("wandb", {})
    if not wandb_cfg.get("enabled", False):
        return
    import wandb  # deferred: optional dependency path, offline-safe via WANDB_MODE

    run = wandb.init(
        project=wandb_cfg.get("project", "collusiongraph"),
        name=wandb_cfg.get("run_name", f"eval-{metrics['dataset']}"),
        config=cfg,
    )
    flat = {
        f"alert/{budget}/{name}": value
        for budget, entry in metrics.get("alert_level", {}).get("queue", {}).items()
        for name, value in entry.items()
    }
    if "node_level" in metrics:
        flat.update({f"node/{k}": v for k, v in metrics["node_level"].items()})
    run.log(flat)
    run.finish()
