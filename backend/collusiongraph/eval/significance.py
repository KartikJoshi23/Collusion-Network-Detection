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

from pathlib import Path

import numpy as np
import polars as pl

from collusiongraph.schema import GraphStore, Label

from .metrics import auc_pr


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
