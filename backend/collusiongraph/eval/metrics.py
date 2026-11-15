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


def _expected_positives_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Expected number of positives in a top-k selection under UNIFORM RANDOM
    tie-breaking at the k-th score.

    Tie-heavy scorers (rules engines, structural floors) make argsort-order
    top-k arbitrary: with thousands of nodes tied at the cutoff, P@k would
    depend on row order. The expected value is order-free and reproducible:
    positives strictly above the cutoff count fully; the remaining slots take
    the tie group's positive rate.
    """
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    threshold = np.sort(scores)[::-1][k - 1]
    above = scores > threshold
    pos_above = float(y_true[above].sum())
    tie = scores == threshold
    slots = k - int(above.sum())
    return pos_above + slots * float(y_true[tie].sum()) / float(tie.sum())


def _effective_k(k: int, n: int) -> int:
    """Budgets larger than the scored population truncate honestly (mirrors the
    alert-level k_effective policy) — never silently dropped, never padded."""
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    if n == 0:
        raise ValueError("no scored nodes")
    return min(k, n)


def precision_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Expected precision within the top-k nodes (tie-aware, order-free)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    k_eff = _effective_k(k, len(scores))
    return _expected_positives_at_k(y_true, scores, k_eff) / k_eff


def recall_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Expected share of all positives captured in the top-k (tie-aware)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    n_pos = int(y_true.sum())
    if n_pos == 0:
        raise ValueError("recall undefined: no positives in y_true")
    k_eff = _effective_k(k, len(scores))
    return _expected_positives_at_k(y_true, scores, k_eff) / n_pos


def fpr_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Expected share of all negatives falsely flagged in the top-k (tie-aware)."""
    y_true, scores = np.asarray(y_true), np.asarray(scores)
    _validate_binary(y_true)
    n_neg = int((1 - y_true).sum())
    if n_neg == 0:
        raise ValueError("FPR undefined: no negatives in y_true")
    k_eff = _effective_k(k, len(scores))
    return (k_eff - _expected_positives_at_k(y_true, scores, k_eff)) / n_neg


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


def _split_at_budget(queue: pl.DataFrame, k: int) -> tuple[pl.DataFrame, pl.DataFrame, int]:
    """Split a queue at budget ``k`` into the alerts strictly above the k-th
    risk score, the tie group at that score, and the number of tie-group
    alerts the budget admits.

    Alert risk scores tie when calibrated scores saturate (isotonic plateaus),
    and ``rank`` then breaks the tie by community id, which carries no model
    information. Budget metrics therefore take the expectation over a uniform
    random order within the tie group, the rule the node-level metrics use.
    A frame without ``risk_score`` has unique ranks and so no ties.
    """
    if "risk_score" not in queue.columns:
        ranked = queue.sort("rank")
        return ranked.head(k), ranked.head(0), 0
    scores = queue["risk_score"].to_numpy()
    threshold = np.sort(scores)[::-1][k - 1]
    above = queue.filter(pl.Series(scores > threshold))
    tie = queue.filter(pl.Series(scores == threshold))
    return above, tie, k - above.height


def _p_none_drawn(n_group: int, n_drawn: int, n_marked: int) -> float:
    """Probability that ``n_drawn`` alerts drawn uniformly without replacement
    from ``n_group`` include none of ``n_marked`` marked alerts."""
    p = 1.0
    for i in range(n_marked):
        if n_group - n_drawn - i <= 0:
            return 0.0
        p *= (n_group - n_drawn - i) / (n_group - i)
    return p


def alert_queue_metrics(labeled_queue: pl.DataFrame, budgets: list[int]) -> dict[str, dict]:
    """Budget metrics over a deduplicated, hit-labeled queue (tie-aware).

    ``precision``: expected hits among the top-k alerts / k (k truncated to
    queue length, reported as ``k_effective``), with a uniform random order
    within tied risk scores (``_split_at_budget``). ``n_hits`` is that
    expectation, so it can be fractional. ``false_alert_rate`` = 1 −
    precision — the alert-level operational analogue of FPR (alert-level TN
    is ill-defined).
    """
    out: dict[str, dict] = {}
    for k in budgets:
        k_eff = min(k, labeled_queue.height)
        if k_eff == 0:
            raise ValueError("empty alert queue")
        above, tie, slots = _split_at_budget(labeled_queue, k_eff)
        expected = float(above["is_hit"].sum())
        if slots:
            expected += slots * float(tie["is_hit"].sum()) / tie.height
        p = expected / k_eff
        out[f"@{k}"] = {
            "k_requested": k,
            "k_effective": k_eff,
            "precision": p,
            "false_alert_rate": 1.0 - p,
            "n_hits": expected,
        }
    return out


def illicit_coverage_at_budget(
    labeled_queue: pl.DataFrame, labels: pl.DataFrame, budgets: list[int]
) -> dict[str, float]:
    """Alert-level recall: expected share of ALL confirmed illicit nodes that
    appear as members of the top-k deduplicated alerts (captured illicit mass,
    §4.5). Tie-aware like ``alert_queue_metrics``; the expectation is exact
    even when alerts in the tie group share members."""
    illicit = set(labels.filter(pl.col("label") == Label.ILLICIT.value)["node_id"].to_list())
    if not illicit:
        raise ValueError("coverage undefined: no confirmed illicit nodes in labels")
    out: dict[str, float] = {}
    for k in budgets:
        k_eff = min(k, labeled_queue.height)
        if k_eff == 0:
            out[f"@{k}"] = 0.0
            continue
        above, tie, slots = _split_at_budget(labeled_queue, k_eff)
        covered = set(above["member_node_ids"].explode(empty_as_null=False).to_list()) & illicit
        expected = float(len(covered))
        if slots:
            open_illicit = illicit - covered
            marked: dict[str, int] = {}  # tie-group alerts holding each open illicit node
            for members in tie["member_node_ids"].to_list():
                for node in set(members) & open_illicit:
                    marked[node] = marked.get(node, 0) + 1
            expected += sum(1.0 - _p_none_drawn(tie.height, slots, m) for m in marked.values())
        out[f"@{k}"] = expected / len(illicit)
    return out
