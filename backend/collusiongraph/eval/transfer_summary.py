"""Pooled and size-weighted transfer lift with per-fold CIs (revision brief item B5).

The transfer matrices report a macro lift: the unweighted mean of per-fold
lifts. Small folds can carry it. This module adds three summaries computed
from the stored per-fold, per-seed score files. Nothing is retrained.

* Pooled lift: for each seed, all held-out firms from every fold are ranked
  together. AUC-PR over that pool is divided by the pooled prevalence, and the
  mean ± std (ddof=1) over seeds is reported. Scores from different fold
  models are ranked against each other here, which the paper must state.
* Size-weighted lift: per-fold mean lifts weighted by each fold's number of
  confirmed test firms.
* Per-fold 95% CI: a stratified bootstrap over the fold's test firms. Each
  resample draws the same firms for every seed and records the mean AUC-PR
  over seeds, so the interval matches the statistic the table reports. The
  CI on lift is the CI on AUC-PR divided by the fold's fixed prevalence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from collusiongraph.schema import GraphStore, Label

from .metrics import auc_pr
from .report import load_config
from .significance import _stratified_indices


def _fold_vectors(
    matrix_dir: Path, group: str, seeds: list[int], labels: pl.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """(y, scores[seed, firm]) over the fold's confirmed test firms, aligned
    across seeds by node_id."""
    merged: pl.DataFrame | None = None
    for s in seeds:
        frame = pl.read_parquet(matrix_dir / f"fold_{group}_s{s}" / "scores_test.parquet").select(
            "node_id", pl.col("score").alias(f"s{s}")
        )
        merged = frame if merged is None else merged.join(frame, on="node_id", how="inner")
    assert merged is not None
    joined = merged.join(labels.select("node_id", "label"), on="node_id", how="inner").filter(
        pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])
    )
    y = (joined["label"] == Label.ILLICIT.value).cast(pl.Int8).to_numpy()
    scores = np.vstack([joined[f"s{s}"].to_numpy() for s in seeds])
    return y, scores


def summarise_matrix(
    matrix_dir: Path,
    labels: pl.DataFrame,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, Any]:
    doc = json.loads((matrix_dir / "matrix.json").read_text(encoding="utf-8"))
    seeds = [int(s) for s in doc["seeds"]]
    folds = [f for f in doc["folds"] if f.get("status") == "completed"]
    if not folds:
        raise ValueError(f"{matrix_dir}: no completed folds")

    fold_rows: list[dict[str, Any]] = []
    pooled_y: list[np.ndarray] = []
    pooled_s: list[np.ndarray] = []
    rng = np.random.default_rng(seed)
    for fold in folds:
        group = str(fold["test_group"])
        y, scores = _fold_vectors(matrix_dir, group, seeds, labels)
        prevalence = float(y.mean())
        boot = np.empty(n_boot)
        for b in range(n_boot):
            idx = _stratified_indices(rng, y)
            boot[b] = np.mean([auc_pr(y[idx], row[idx])["auc_pr"] for row in scores])
        lo, hi = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
        fold_rows.append(
            {
                "test_group": group,
                "n_confirmed_test": int(y.size),
                "prevalence": prevalence,
                "auc_pr_mean": float(fold["auc_pr_mean"]),
                "lift_mean": float(fold["lift_mean"]),
                "auc_pr_ci_low": float(lo),
                "auc_pr_ci_high": float(hi),
                "lift_ci_low": float(lo / prevalence),
                "lift_ci_high": float(hi / prevalence),
            }
        )
        pooled_y.append(y)
        pooled_s.append(scores)

    y_all = np.concatenate(pooled_y)
    pooled_prev = float(y_all.mean())
    pooled_per_seed = []
    for i, s in enumerate(seeds):
        s_all = np.concatenate([sc[i] for sc in pooled_s])
        ap = auc_pr(y_all, s_all)["auc_pr"]
        pooled_per_seed.append({"seed": s, "auc_pr": ap, "lift": ap / pooled_prev})
    lifts = [p["lift"] for p in pooled_per_seed]
    sizes = np.array([r["n_confirmed_test"] for r in fold_rows], dtype=float)
    fold_lifts = np.array([r["lift_mean"] for r in fold_rows])
    return {
        "dataset": doc.get("dataset"),
        "seeds": seeds,
        "n_folds": len(fold_rows),
        "n_confirmed_pooled": int(y_all.size),
        "pooled_prevalence": pooled_prev,
        "pooled_per_seed": pooled_per_seed,
        "pooled_lift_mean": float(np.mean(lifts)),
        "pooled_lift_std": float(np.std(lifts, ddof=1)) if len(lifts) > 1 else 0.0,
        "size_weighted_lift": float(np.sum(sizes * fold_lifts) / np.sum(sizes)),
        "macro_lift": float(doc["summary"]["macro_lift_mean"]),
        "folds": fold_rows,
    }


def run_transfer_pooled(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    if not cfg.get("transfer_pooled"):
        raise ValueError("run_transfer_pooled expects a config with transfer_pooled: true")
    n_boot = int(cfg.get("n_boot", 2000))
    alpha = float(cfg.get("alpha", 0.05))
    seed = int(cfg.get("seed", 0))
    report: dict[str, Any] = {
        "kind": "transfer_pooled",
        "n_boot": n_boot,
        "alpha": alpha,
        "seed": seed,
        "matrices": {},
    }
    for name, spec in cfg["matrices"].items():
        store = GraphStore(spec.get("store_root", cfg.get("store_root", "data/interim")))
        labels = store.read(spec["dataset"], "labels")
        report["matrices"][name] = summarise_matrix(
            Path(spec["matrix_dir"]), labels, n_boot=n_boot, alpha=alpha, seed=seed
        )
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "transfer_pooled.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
