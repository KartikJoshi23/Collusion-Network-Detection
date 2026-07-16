"""Financial domain feature pack (§4.4): money-flow behavior per node.

Computed from ``pays`` edges only. Holding time, retention ratio, directional
burstiness, amount round-number bias, and velocity — the AML feature families
named in the plan. Amount-dependent features are null where the dataset carries
no amounts (Elliptic++'s anonymized features; §4.3 D1) and real on AMLworld and
any account-graph with true amounts — the honesty rule that also governs
explanation bundles.

Same as-of discipline as ``structural.py`` (§9.1b).
"""

from __future__ import annotations

import math

import polars as pl

from collusiongraph.schema import EdgeType

from .structural import restrict_as_of

# amounts whose remainder mod this is zero count as "round" (structuring signal)
_ROUND_BASE = 100.0


def _direction_stats(edges: pl.DataFrame, endpoint: str, prefix: str) -> pl.DataFrame:
    gaps = (
        edges.filter(pl.col("timestamp").is_not_null())
        .sort(endpoint, "timestamp")
        .with_columns(pl.col("timestamp").diff().over(endpoint).alias("_gap"))
        .drop_nulls("_gap")
        .group_by(endpoint)
        .agg(pl.col("_gap").mean().alias("_mu"), pl.col("_gap").std().alias("_sigma"))
        .select(
            pl.col(endpoint).alias("node_id"),
            ((pl.col("_sigma") - pl.col("_mu")) / (pl.col("_sigma") + pl.col("_mu"))).alias(
                f"{prefix}_burstiness"
            ),
        )
    )
    # amount features stay NULL (unknown) where the dataset carries no amounts
    # (Elliptic++; §4.3 D1) — a sum of nothing is not 0, and NaN would silently
    # poison per-graph z-scoring downstream
    n_amounts = pl.col("amount").is_not_null().sum()
    stats = edges.group_by(pl.col(endpoint).alias("node_id")).agg(
        pl.len().alias(f"{prefix}_count"),
        pl.when(n_amounts > 0).then(pl.col("amount").sum()).alias(f"{prefix}_amount_sum"),
        pl.col("timestamp").min().alias(f"_{prefix}_t_min"),
        pl.col("timestamp").max().alias(f"_{prefix}_t_max"),
        pl.when(n_amounts > 0)
        .then(((pl.col("amount") % _ROUND_BASE) == 0).sum() / n_amounts)
        .alias(f"{prefix}_round_amount_share"),
    )
    return stats.join(gaps, on="node_id", how="left")


def financial_features(
    nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None = None
) -> pl.DataFrame:
    """Per-node money-flow features from ``pays`` edges, one row per node at ``as_of``."""
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    pays = edges.filter(pl.col("edge_type") == EdgeType.PAYS.value)

    out = _direction_stats(pays, "src", "out")
    inn = _direction_stats(pays, "dst", "in")
    features = (
        nodes.select("node_id")
        .join(inn, on="node_id", how="left")
        .join(out, on="node_id", how="left")
        .with_columns(
            pl.col("in_count").fill_null(0).cast(pl.Int64),
            pl.col("out_count").fill_null(0).cast(pl.Int64),
        )
    )

    span = (
        pl.max_horizontal("_in_t_max", "_out_t_max") - pl.min_horizontal("_in_t_min", "_out_t_min")
    ).alias("_span")
    in_sum = pl.col("in_amount_sum").fill_null(0.0)
    out_sum = pl.col("out_amount_sum").fill_null(0.0)
    features = (
        features.with_columns(span)
        .with_columns(
            # retention ∈ [−1, 1]: +1 pure sink, −1 pure source, 0 balanced
            # pass-through; null (not 0/0) when no amounts are known at all
            pl.when(in_sum + out_sum > 0)
            .then((in_sum - out_sum) / (in_sum + out_sum))
            .alias("retention_ratio"),
            ((pl.col("in_count") + pl.col("out_count")) / (pl.col("_span") + 1)).alias("velocity"),
        )
        .drop("_in_t_min", "_in_t_max", "_out_t_min", "_out_t_max", "_span")
    )
    return features.join(_holding_time(pays), on="node_id", how="left").sort("node_id")


def _holding_time(pays: pl.DataFrame) -> pl.DataFrame:
    """Median time funds sit at a node: for each outgoing payment, the gap to the
    most recent incoming payment at or before it (per-node as-of join)."""
    dated = pays.filter(pl.col("timestamp").is_not_null())
    outs = dated.select(pl.col("src").alias("node_id"), "timestamp").sort("timestamp")
    ins = dated.select(pl.col("dst").alias("node_id"), pl.col("timestamp").alias("_t_in")).sort(
        "_t_in"
    )
    # both frames are pre-sorted on the asof key; per-group sortedness cannot be
    # auto-verified when `by` is used, hence the explicit opt-out
    matched = outs.join_asof(
        ins,
        left_on="timestamp",
        right_on="_t_in",
        by="node_id",
        strategy="backward",
        check_sortedness=False,
    )
    return (
        matched.drop_nulls("_t_in")
        .group_by("node_id")
        .agg((pl.col("timestamp") - pl.col("_t_in")).median().alias("holding_time_median"))
    )


def sinusoidal_time_encoding(
    timestamps: pl.Series, n_frequencies: int = 4, max_period: float = 10_000.0
) -> pl.DataFrame:
    """Transformer-style sin/cos encodings of integer timestamps (§4.4 temporal
    encodings) — edge- or node-level model inputs, not screening features."""
    ts = timestamps.cast(pl.Float64)
    columns: dict[str, pl.Series] = {}
    for k in range(n_frequencies):
        period = max_period ** (k / max(n_frequencies - 1, 1))
        angle = ts * (2.0 * math.pi / period)
        columns[f"time_sin_{k}"] = angle.sin()
        columns[f"time_cos_{k}"] = angle.cos()
    return pl.DataFrame(columns)
