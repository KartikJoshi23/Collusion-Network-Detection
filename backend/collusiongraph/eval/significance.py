"""Bootstrap uncertainty for headline comparisons (§7 step 29).

Stratified percentile bootstrap — positives and negatives resampled
separately, so every resample keeps both classes and the observed
prevalence — for a single scorer's AUC-PR, and a PAIRED bootstrap for two
scorers over the SAME confirmed test nodes (identical resample indices per
draw, so the delta distribution is the one the significance claim needs).

No protocol changes: this consumes stored ``scores_test.parquet`` artifacts
and the §4.5 label semantics (confirmed nodes only; unknowns are never
metric participants). The p-value uses the add-one-smoothed two-sided
convention (p is never exactly 0 from a finite bootstrap).
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

METHOD = "stratified paired bootstrap, add-one-smoothed two-sided p (eval/significance.py)"


def _stratified_indices(rng: np.random.Generator, y: np.ndarray) -> np.ndarray:
    pos = np.flatnonzero(y == 1)
    neg = np.flatnonzero(y == 0)
    return np.concatenate(
        [
            rng.choice(pos, size=pos.size, replace=True),
            rng.choice(neg, size=neg.size, replace=True),
        ]
    )


def bootstrap_auc_pr_ci(
    y_true: np.ndarray,
    scores: np.ndarray,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, float | int]:
    """Point AUC-PR (with prevalence baseline) plus a stratified percentile
    bootstrap CI over the confirmed test nodes."""
    y = np.asarray(y_true)
    s = np.asarray(scores)
    point = auc_pr(y, s)  # validates labels and positive presence
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = _stratified_indices(rng, y)
        stats[b] = auc_pr(y[idx], s[idx])["auc_pr"]
    lo, hi = np.quantile(stats, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {
        **point,
        "n": int(y.size),
        "n_boot": n_boot,
        "alpha": alpha,
        "ci_low": float(lo),
        "ci_high": float(hi),
    }


def paired_bootstrap_auc_pr(
    y_true: np.ndarray,
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, float | int]:
    """Paired comparison of two scorers on the SAME nodes: identical resample
    indices feed both, giving the bootstrap distribution of
    delta = AUC-PR(a) − AUC-PR(b) and an add-one-smoothed two-sided p-value."""
    y = np.asarray(y_true)
    a = np.asarray(scores_a)
    b = np.asarray(scores_b)
    if not (y.size == a.size == b.size):
        raise ValueError("paired bootstrap needs equal-length aligned vectors")
    point_a = auc_pr(y, a)["auc_pr"]
    point_b = auc_pr(y, b)["auc_pr"]
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        idx = _stratified_indices(rng, y)
        deltas[i] = auc_pr(y[idx], a[idx])["auc_pr"] - auc_pr(y[idx], b[idx])["auc_pr"]
    lo, hi = np.quantile(deltas, [alpha / 2.0, 1.0 - alpha / 2.0])
    p_low = (1 + int((deltas <= 0.0).sum())) / (n_boot + 1)
    p_high = (1 + int((deltas >= 0.0).sum())) / (n_boot + 1)
    return {
        "auc_pr_a": point_a,
        "auc_pr_b": point_b,
        "delta": point_a - point_b,
        "delta_ci_low": float(lo),
        "delta_ci_high": float(hi),
        "p_value": min(1.0, 2.0 * min(p_low, p_high)),
        "n": int(y.size),
        "n_boot": n_boot,
        "alpha": alpha,
    }


def compare_score_files(
    store_root: str | Path,
    dataset: str,
    scores_a: str | Path,
    scores_b: str | Path,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, object]:
    """Paired bootstrap over two stored score artifacts: inner-join on
    node_id, restrict to confirmed labels, and report how many scored nodes
    each side lost to the intersection (never silently)."""
    labels = GraphStore(store_root).read(dataset, "labels")
    frame_a = pl.read_parquet(scores_a).rename({"score": "score_a"})
    frame_b = pl.read_parquet(scores_b).rename({"score": "score_b"})
    merged = frame_a.join(frame_b.select("node_id", "score_b"), on="node_id", how="inner")
    confirmed = merged.join(labels.select("node_id", "label"), on="node_id", how="inner").filter(
        pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])
    )
    if confirmed.height == 0:
        raise ValueError("no confirmed nodes in the intersection of the two score files")
    y = (confirmed["label"] == Label.ILLICIT.value).cast(pl.Int8).to_numpy()
    result = paired_bootstrap_auc_pr(
        y,
        confirmed["score_a"].to_numpy(),
        confirmed["score_b"].to_numpy(),
        n_boot=n_boot,
        alpha=alpha,
        seed=seed,
    )
    return {
        **result,
        "dataset": dataset,
        "scores_a": str(scores_a),
        "scores_b": str(scores_b),
        "n_only_a": frame_a.height - merged.height,
        "n_only_b": frame_b.height - merged.height,
    }


def _seed_averaged_scores(paths: list[Path]) -> pl.DataFrame:
    """Per-node mean score over several seed runs (nodes scored by every run)."""
    merged: pl.DataFrame | None = None
    for i, path in enumerate(paths):
        frame = pl.read_parquet(path).select("node_id", pl.col("score").alias(f"_s{i}"))
        merged = frame if merged is None else merged.join(frame, on="node_id", how="inner")
    if merged is None:
        raise ValueError("seed averaging needs at least one score file")
    cols = [c for c in merged.columns if c != "node_id"]
    return merged.select("node_id", pl.mean_horizontal(cols).alias("score"))


def run_significance(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Config-driven paired bootstrap (revision brief item B2; Table III).

    ``comparisons`` maps a name to ``{label_a, label_b, scores_a, scores_b}``.
    Without ``seeds`` each comparison is one ``compare_score_files`` call, and
    the output keeps the published ``significance.json`` schema. With
    ``seeds``, the score paths are templates containing ``{seed}``. Every
    seed pair is then bootstrapped, the range of deltas is reported, and
    ``seed_averaged: true`` adds one comparison on per-node mean scores.
    Every comparison uses the same bootstrap ``seed`` for comparability.
    """
    cfg = load_config(config)
    store_root = cfg.get("store_root", "data/interim")
    dataset: str = cfg["dataset"]
    n_boot = int(cfg.get("n_boot", 2000))
    alpha = float(cfg.get("alpha", 0.05))
    boot_seed = int(cfg.get("seed", 0))
    out_dir = Path(cfg["output_dir"])
    seeds = cfg.get("seeds")
    comparisons: dict[str, dict[str, Any]] = cfg["comparisons"]

    results: dict[str, Any] = {}
    for name, spec in comparisons.items():
        labels = {"label_a": spec.get("label_a", "a"), "label_b": spec.get("label_b", "b")}
        if seeds is None:
            res = compare_score_files(
                store_root, dataset, spec["scores_a"], spec["scores_b"], n_boot, alpha, boot_seed
            )
            results[name] = {**labels, **res}
            continue
        seed_list = [int(s) for s in seeds]
        paths_a = [Path(str(spec["scores_a"]).format(seed=s)) for s in seed_list]
        paths_b = [Path(str(spec["scores_b"]).format(seed=s)) for s in seed_list]
        per_seed: list[dict[str, Any]] = [
            {"seed": s, **compare_score_files(store_root, dataset, a, b, n_boot, alpha, boot_seed)}
            for s, a, b in zip(seed_list, paths_a, paths_b, strict=True)
        ]
        deltas = [r["delta"] for r in per_seed]
        mean_a = float(np.mean([r["auc_pr_a"] for r in per_seed]))
        mean_b = float(np.mean([r["auc_pr_b"] for r in per_seed]))
        entry: dict[str, Any] = {
            **labels,
            "per_seed": per_seed,
            "delta_min": float(min(deltas)),
            "delta_max": float(max(deltas)),
            "ci_low_min": float(min(r["delta_ci_low"] for r in per_seed)),
            "ci_high_max": float(max(r["delta_ci_high"] for r in per_seed)),
            "p_value_max": float(max(r["p_value"] for r in per_seed)),
            "mean_auc_pr_a": mean_a,
            "mean_auc_pr_b": mean_b,
            "difference_of_means": mean_a - mean_b,
        }
        if cfg.get("seed_averaged"):
            out_dir.mkdir(parents=True, exist_ok=True)
            avg_a = out_dir / f"{name}_a_seed_mean.parquet"
            avg_b = out_dir / f"{name}_b_seed_mean.parquet"
            _seed_averaged_scores(paths_a).write_parquet(avg_a)
            _seed_averaged_scores(paths_b).write_parquet(avg_b)
            entry["seed_averaged"] = compare_score_files(
                store_root, dataset, avg_a, avg_b, n_boot, alpha, boot_seed
            )
        results[name] = entry

    report: dict[str, Any] = {
        "kind": "paired_significance" if seeds is None else "paired_significance_multiseed",
        "dataset": dataset,
        "n_boot": n_boot,
        "seed": boot_seed,
        "method": METHOD,
        **({"seeds": [int(s) for s in seeds]} if seeds is not None else {}),
        "comparisons": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = cfg.get("output_file", "significance.json")
    (out_dir / out_file).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
