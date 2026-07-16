"""Budget-first metrics (§4.5): Precision@k, AUC-PR, FPR/Recall@budget.

Two levels, reported side by side (arXiv:2604.23494 shows they disagree):

* **Node level** — scores + binary truth on confirmed nodes only (unknowns are
  excluded before these functions; §4.3 D1).
* **Alert level** — the deduplicated ranked queue under the §4.5 hit rule
  (``alert_unit.py``); the operational view the paper leads with.

Threshold-free reporting rules: AUC-PR is always contextualized against the
prevalence baseline (a random ranker's AUC-PR equals prevalence); global
accuracy never appears (meaningless at ~2% prevalence).
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.metrics import average_precision_score

from collusiongraph.schema import Label


def _validate_binary(y_true: np.ndarray) -> None:
    uniques = set(np.unique(y_true).tolist())
    if not uniques <= {0, 1}:
        raise ValueError(f"y_true must be binary 0/1 (confirmed nodes only), got {sorted(uniques)}")


def precision_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Precision within the top-k nodes by score (descending, stable order)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    if not 0 < k <= len(scores):
        raise ValueError(f"k={k} out of range for {len(scores)} scored nodes")
    top = np.argsort(-scores, kind="stable")[:k]
    return float(y_true[top].mean())


def recall_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Share of all positives captured in the top-k (captured illicit mass)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    n_pos = int(y_true.sum())
    if n_pos == 0:
        raise ValueError("recall undefined: no positives in y_true")
    top = np.argsort(-scores, kind="stable")[:k]
    return float(y_true[top].sum() / n_pos)


def fpr_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Share of all negatives falsely flagged in the top-k (FP / total negatives)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    n_neg = int((1 - y_true).sum())
    if n_neg == 0:
        raise ValueError("FPR undefined: no negatives in y_true")
    top = np.argsort(-scores, kind="stable")[:k]
    return float((1 - y_true[top]).sum() / n_neg)


def auc_pr(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    """AUC-PR with its prevalence baseline (the random-ranker reference §4.4.5)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    if y_true.sum() == 0:
        raise ValueError("AUC-PR undefined: no positives in y_true")
    return {
        "auc_pr": float(average_precision_score(y_true, scores)),
        "prevalence_baseline": float(y_true.mean()),
    }


def confirmed_node_vectors(
    scores: pl.DataFrame, labels: pl.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Join node scores to labels and return (y_true, scores) over CONFIRMED
    nodes only — unknowns participate in message passing, never in metrics."""
    joined = scores.join(labels.select("node_id", "label"), on="node_id", how="inner").filter(
        pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])
    )
    y = (joined["label"] == Label.ILLICIT.value).cast(pl.Int8).to_numpy()
    return y, joined["score"].to_numpy()


def alert_queue_metrics(labeled_queue: pl.DataFrame, budgets: list[int]) -> dict[str, dict]:
    """Budget metrics over a deduplicated, hit-labeled queue (rank-sorted).

    ``precision``: hits among the top-k alerts / k (k truncated to queue length,
    reported as ``k_effective``). ``false_alert_rate`` = 1 − precision — the
    alert-level operational analogue of FPR (alert-level TN is ill-defined).
    """
    queue = labeled_queue.sort("rank")
    hits = queue["is_hit"].to_numpy()
    out: dict[str, dict] = {}
    for k in budgets:
        k_eff = min(k, len(hits))
        if k_eff == 0:
            raise ValueError("empty alert queue")
        p = float(hits[:k_eff].mean())
        out[f"@{k}"] = {
            "k_requested": k,
            "k_effective": k_eff,
            "precision": p,
            "false_alert_rate": 1.0 - p,
            "n_hits": int(hits[:k_eff].sum()),
        }
    return out


def illicit_coverage_at_budget(
    labeled_queue: pl.DataFrame, labels: pl.DataFrame, budgets: list[int]
) -> dict[str, float]:
    """Alert-level recall: share of ALL confirmed illicit nodes that appear as
    members of the top-k deduplicated alerts (captured illicit mass, §4.5)."""
    illicit = set(labels.filter(pl.col("label") == Label.ILLICIT.value)["node_id"].to_list())
    if not illicit:
        raise ValueError("coverage undefined: no confirmed illicit nodes in labels")
    queue = labeled_queue.sort("rank")
    out: dict[str, float] = {}
    for k in budgets:
        members = queue.head(k)["member_node_ids"].explode(empty_as_null=False).to_list()
        out[f"@{k}"] = len(set(members) & illicit) / len(illicit)
    return out
