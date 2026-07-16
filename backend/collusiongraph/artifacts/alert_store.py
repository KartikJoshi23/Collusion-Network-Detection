"""Alert construction (§3.2 — the alert is the system's central artifact).

Scored communities become schema-conformant alert rows: ranked by calibrated
community score, time-windowed from member activity, carrying the immutable
screening-only caveat. Motif types and explanation refs join in Week 6; the
NMS dedup and hit rule live in the evaluation harness, which consumes this
frame as-is.
"""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from collusiongraph import SCREENING_CAVEAT

_TIME = "time_first_seen"


def build_alerts(
    scored_communities: pl.DataFrame,
    nodes: pl.DataFrame,
    dataset: str,
    domain: str,
    model_run_id: str,
) -> pl.DataFrame:
    """Ranked alerts frame (ALERTS_SCHEMA-conformant via ``GraphStore.write``)."""
    ranked = scored_communities.sort("score", descending=True).with_row_index("_rank", offset=1)

    windows = (
        ranked.select("community_id", "member_node_ids")
        .explode("member_node_ids", empty_as_null=False)
        .rename({"member_node_ids": "node_id"})
        .join(nodes.select("node_id", _TIME), on="node_id", how="left")
        .group_by("community_id")
        .agg(
            pl.col(_TIME).min().alias("time_window_start"),
            pl.col(_TIME).max().alias("time_window_end"),
        )
    )
    return (
        ranked.join(windows, on="community_id", how="left")
        .select(
            pl.format("{}:{}:{}", pl.lit(dataset), pl.lit(model_run_id), pl.col("_rank")).alias(
                "alert_id"
            ),
            pl.lit(domain).alias("domain"),
            pl.lit(dataset).alias("dataset"),
            pl.lit(model_run_id).alias("model_run_id"),
            pl.col("_rank").cast(pl.Int32).alias("rank"),
            pl.col("score").alias("risk_score"),
            pl.col("community_id"),
            pl.col("member_node_ids"),
            pl.col("time_window_start"),
            pl.col("time_window_end"),
            pl.col("member_node_ids").list.len().cast(pl.Int32).alias("n_members"),
            pl.lit(datetime.now(UTC)).alias("created_at"),
            pl.lit(SCREENING_CAVEAT).alias("caveats"),
        )
        .sort("rank")
    )
