"""Score-fusion ensemble (§4.4, §7 step 15).

Two fusion modes over the members (supervised GNN, unsupervised anomaly,
statistical screens/floor):

* **Calibrated fusion (primary, §4.4)** — each member is isotonic-calibrated
  on the VALIDATION pool, and the fused score is the (weighted) mean of
  calibrated probabilities. This is why the plan calibrates before fusing: a
  near-random member calibrates to a nearly flat ~prevalence output and stops
  outvoting strong members — measured on Elliptic++, where equal-weight rank
  fusion dragged AUC-PR 0.69 → 0.06 (decision log).
* **Rank fusion (scale-free alternative)** — mean of rank percentiles; kept
  for ablation. Monotone member transforms cannot change it (pinned by test),
  so it cannot benefit from calibration by construction.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from .rollup import isotonic_calibrator


def calibrated_fusion(
    members_test: dict[str, pl.DataFrame],
    members_val: dict[str, pl.DataFrame],
    val_labels: pl.DataFrame,
    weights: dict[str, float] | None = None,
) -> pl.DataFrame:
    """§4.4 primary fusion: isotonic-calibrate each member on the validation
    pool (scores + binary ``y``), then fuse test scores as the weighted mean of
    calibrated probabilities over the members that scored each node.

    ``val_labels`` carries node_id + y (1 illicit / 0 licit, confirmed only).
    Members missing from ``members_val`` cannot be calibrated — hard error, not
    a silent uncalibrated passthrough.
    """
    missing = set(members_test) - set(members_val)
    if missing:
        raise ValueError(f"members lack validation scores for calibration: {sorted(missing)}")
    weights = weights or {}
    unknown = set(weights) - set(members_test)
    if unknown:
        raise ValueError(f"weights reference unknown members: {sorted(unknown)}")

    calibrated: dict[str, pl.DataFrame] = {}
    for name, test_frame in members_test.items():
        val = members_val[name].join(val_labels, on="node_id", how="inner")
        if val.height == 0 or val["y"].n_unique() < 2:
            raise ValueError(f"member {name!r}: validation pool lacks both classes")
        iso = isotonic_calibrator(val["score"].to_numpy(), val["y"].to_numpy())
        calibrated[name] = test_frame.select(
            "node_id",
            pl.Series("score", iso.predict(test_frame["score"].to_numpy()).astype(np.float64)),
        )

    fused: pl.DataFrame | None = None
    for name, frame in calibrated.items():
        part = frame.rename({"score": f"_cal_{name}"})
        fused = part if fused is None else fused.join(part, on="node_id", how="full", coalesce=True)
    assert fused is not None
    weighted = [
        (pl.col(f"_cal_{name}") * weights.get(name, 1.0)).alias(f"_w_{name}") for name in calibrated
    ]
    present = [
        pl.when(pl.col(f"_cal_{name}").is_not_null())
        .then(pl.lit(weights.get(name, 1.0)))
        .otherwise(0.0)
        .alias(f"_m_{name}")
        for name in calibrated
    ]
    return (
        fused.with_columns(weighted + present)
        .with_columns(
            (
                pl.sum_horizontal([pl.col(f"_w_{n}") for n in calibrated])
                / pl.sum_horizontal([pl.col(f"_m_{n}") for n in calibrated])
            ).alias("score")
        )
        .select("node_id", "score")
        .sort("score", descending=True)
    )


def rank_percentiles(scores: pl.DataFrame, score_col: str = "score") -> pl.DataFrame:
    """Average-tie rank percentiles ∈ (0, 1]; highest score → 1.0."""
    return scores.select(
        "node_id",
        (pl.col(score_col).rank(method="average") / pl.len()).alias("rank_pct"),
    )


def rank_fusion(
    members: dict[str, pl.DataFrame],
    weights: dict[str, float] | None = None,
) -> pl.DataFrame:
    """Fuse member score frames (node_id + score) into one ranked score.

    Nodes missing from a member are fused over the members that DID score them
    (never imputed); a node no member scored does not appear.
    """
    if not members:
        raise ValueError("rank fusion needs at least one member")
    weights = weights or {}
    unknown = set(weights) - set(members)
    if unknown:
        raise ValueError(f"weights reference unknown members: {sorted(unknown)}")

    fused: pl.DataFrame | None = None
    for name, frame in members.items():
        pct = rank_percentiles(frame).rename({"rank_pct": f"_pct_{name}"})
        fused = pct if fused is None else fused.join(pct, on="node_id", how="full", coalesce=True)
    assert fused is not None

    weighted = [
        (pl.col(f"_pct_{name}") * weights.get(name, 1.0)).alias(f"_w_{name}") for name in members
    ]
    weight_present = [
        pl.when(pl.col(f"_pct_{name}").is_not_null())
        .then(pl.lit(weights.get(name, 1.0)))
        .otherwise(0.0)
        .alias(f"_m_{name}")
        for name in members
    ]
    return (
        fused.with_columns(weighted + weight_present)
        .with_columns(
            (
                pl.sum_horizontal([pl.col(f"_w_{n}") for n in members])
                / pl.sum_horizontal([pl.col(f"_m_{n}") for n in members])
            ).alias("score")
        )
        .select("node_id", "score")
        .sort("score", descending=True)
    )
