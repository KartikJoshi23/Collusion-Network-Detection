"""RQ1 baselines B1–B4 (§4.5) — the yardsticks the GNN stack must beat.

* **B1 rules engine** — classic threshold heuristics: each rule triggers when a
  feature crosses a percentile threshold **fit on the training distribution
  only**; the score is the fraction of triggered rules. Transparent and
  auditable — the operational status quo the problem statement critiques.
* **B2 XGBoost tabular** — gradient boosting on per-node features alone.
* **B3 XGB-Graph** — B2 plus simple neighborhood mean-aggregated features, per
  the GADBench protocol (arXiv:2306.12251): tree ensembles with neighborhood
  aggregation often beat specialized GNNs (+12.9 AUPRC average), so this is
  the honest reference point.
* **B4 screens-only** — a transparent composite of statistical screens
  (mean of direction-adjusted z-scores), the procurement screen tradition.

All graph-derived inputs obey the §9.1b as-of discipline via the features
layer; neighborhood aggregation here takes ``as_of`` for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import polars as pl
import scipy.sparse as sp

from collusiongraph.features import restrict_as_of, zscore_per_graph


@dataclass(frozen=True)
class Rule:
    """One red-flag heuristic: ``column`` crossing its train-set percentile."""

    column: str
    direction: Literal["high", "low"]
    percentile: float  # e.g. 99.0 -> threshold at the train P99


class RulesEngine:
    """B1: count-of-triggered-rules scorer with train-only thresholds (§9.1b)."""

    def __init__(self, rules: list[Rule]) -> None:
        if not rules:
            raise ValueError("a rules engine needs at least one rule")
        self.rules = rules
        self._thresholds: dict[str, float] | None = None

    def fit(self, train_features: pl.DataFrame) -> RulesEngine:
        self._thresholds = {}
        for rule in self.rules:
            q = rule.percentile / 100.0
            value = train_features[rule.column].drop_nulls().quantile(q, interpolation="linear")
            if value is None:
                raise ValueError(f"rule column {rule.column!r} is all-null on the training set")
            self._thresholds[rule.column] = float(value)
        return self

    def score(self, features: pl.DataFrame) -> pl.DataFrame:
        """Fraction of rules triggered per node; null features never trigger."""
        if self._thresholds is None:
            raise RuntimeError("fit() must run (on TRAIN data only) before score()")
        triggers = [
            (
                pl.col(r.column) >= self._thresholds[r.column]
                if r.direction == "high"
                else pl.col(r.column) <= self._thresholds[r.column]
            )
            .fill_null(False)
            .cast(pl.Int8)
            for r in self.rules
        ]
        return features.select(
            "node_id", (pl.sum_horizontal(triggers) / len(self.rules)).alias("score")
        )


def xgb_scores(
    train_x: np.ndarray,
    train_y: np.ndarray,
    x: np.ndarray,
    seed: int = 0,
    **params: object,
) -> np.ndarray:
    """B2/B3 scorer: XGBoost probability of the illicit class.

    Imbalance handled via ``scale_pos_weight`` = negatives/positives (the
    tree-ensemble analogue of class weighting); NaNs pass through natively.
    """
    from xgboost import XGBClassifier

    n_pos = int(train_y.sum())
    if n_pos == 0 or n_pos == len(train_y):
        raise ValueError("training labels must contain both classes")
    defaults: dict[str, object] = {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.1,
        "tree_method": "hist",
        "eval_metric": "aucpr",
        "n_jobs": -1,
    }
    model = XGBClassifier(
        **{**defaults, **params},
        random_state=seed,
        scale_pos_weight=(len(train_y) - n_pos) / n_pos,
    )
    model.fit(train_x, train_y)
    return model.predict_proba(x)[:, 1].astype(np.float64)


def neighbor_mean_features(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    features: pl.DataFrame,
    as_of: int | None = None,
    suffix: str = "_nbr_mean",
) -> pl.DataFrame:
    """GADBench-style neighborhood aggregation: per node, the mean of each
    numeric feature over its distinct undirected neighbors at ``as_of``.
    Isolated nodes get NaN (no neighborhood — unknown, not zero)."""
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    node_ids = nodes["node_id"].to_list()
    index = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)

    pairs = edges.select("src", "dst").unique()
    src = np.fromiter(
        (index[s] for s in pairs["src"].to_list()), dtype=np.int64, count=pairs.height
    )
    dst = np.fromiter(
        (index[d] for d in pairs["dst"].to_list()), dtype=np.int64, count=pairs.height
    )
    rows = np.concatenate([src, dst])
    cols = np.concatenate([dst, src])
    adj = sp.csr_matrix((np.ones(len(rows), dtype=np.float64), (rows, cols)), shape=(n, n))
    adj.data = np.minimum(adj.data, 1.0)  # mutual pairs collapse to simple adjacency

    # explicit dtype: an empty node set must not degrade node_id to Null
    id_frame = pl.DataFrame({"node_id": pl.Series(node_ids, dtype=pl.Utf8)})
    numeric_cols = [c for c, dt in features.schema.items() if c != "node_id" and dt.is_numeric()]
    aligned = id_frame.join(
        features.select(["node_id", *numeric_cols]), on="node_id", how="left"
    ).select(numeric_cols)
    matrix = aligned.to_numpy().astype(np.float64).reshape(n, len(numeric_cols))
    matrix_zeroed = np.nan_to_num(matrix, nan=0.0)
    known = adj @ (~np.isnan(matrix)).astype(np.float64)  # neighbors with a known value
    sums = adj @ matrix_zeroed
    with np.errstate(invalid="ignore", divide="ignore"):
        means = sums / known  # 0 known neighbors -> NaN
    return id_frame.with_columns(
        [pl.Series(f"{c}{suffix}", means[:, j]) for j, c in enumerate(numeric_cols)]
    )


def screens_composite_scores(
    features: pl.DataFrame,
    columns: list[str],
    low_risk_columns: list[str] | None = None,
) -> pl.DataFrame:
    """B4: transparent screen composite — the mean of direction-adjusted
    z-scores over the available screens (nulls skipped, not imputed).

    ``low_risk_columns`` are screens where LOW values are the red flag
    (e.g. rotation entropy); their z-scores are negated before averaging.
    """
    missing = [c for c in columns if c not in features.columns]
    if missing:
        raise ValueError(f"screen columns absent from features: {missing}")
    low = set(low_risk_columns or [])
    if not low <= set(columns):
        raise ValueError("low_risk_columns must be a subset of columns")
    z = zscore_per_graph(features.select(["node_id", *columns]), fill_null=False)
    adjusted = z.with_columns([(-pl.col(c)).alias(c) for c in low])
    return adjusted.select(
        "node_id", pl.mean_horizontal([pl.col(c) for c in columns]).alias("score")
    )
