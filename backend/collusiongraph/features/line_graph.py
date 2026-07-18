"""Line-graph (edge→node duality) feature channel — §7 step 26a, §4.4 table.

The directed line graph L(G) has one node per directed edge e=(u→v) and an
arc e→f exactly when f=(v→w) continues the walk. Its local statistics are
flow-through quantities, and the small-radius ones are exact closed forms
over G's directed degrees:

- ``in_deg_L(e=(u→v)) = in_deg_G(u)`` and ``out_deg_L(e=(u→v)) = out_deg_G(v)``;
- the number of L(G) arcs THROUGH node v is ``in_deg_G(v) · out_deg_G(v)``
  (the count of directed 2-walks u→v→w).

This channel computes those statistics per node WITHOUT materializing L(G)
(the identities above are exact) and pools incident-edge line-degrees back to
the edge endpoints:

- ``lg_through_count`` / ``lg_through_log1p`` — 2-walk throughput at v (the
  pass-through/flow signal motivating the line-graph view, §4.4);
- ``lg_pass_ratio`` — throughput per unit of endpoint activity,
  ``in·out / (in+out)`` (0 for pure sources/sinks, grows with balanced flow);
- ``lg_upstream_fan_mean`` / ``lg_upstream_fan_max`` — over in-edges (u→v):
  ``in_deg(u)`` — how much flow feeds the flows feeding v;
- ``lg_downstream_fan_mean`` / ``lg_downstream_fan_max`` — over out-edges
  (v→w): ``out_deg(w)`` — how far v's outflow fans out one step later.

Conventions: walk semantics drop self-loops (a self-loop continues no walk);
parallel multi-edges count with multiplicity (each is its own line-node);
aggregates over an empty edge set are null per the 2026-07-15 quorum rule
(undefined, never fabricated), while genuinely-zero counts are 0.

The learned LineMVGNN-style encoder over a materialized L(G) (embeddings
concatenated into the main model) is the recorded Phase-2 follow-up; this
deterministic channel is ablation arm **B-LG v1**.

As-of discipline (§9.1b): identical to the structural template — the graph is
restricted via ``restrict_as_of`` before anything is computed, so a feature
value can never encode the future.
"""

from __future__ import annotations

import polars as pl

from .structural import restrict_as_of

_COLUMNS = [
    "lg_through_count",
    "lg_through_log1p",
    "lg_pass_ratio",
    "lg_upstream_fan_mean",
    "lg_upstream_fan_max",
    "lg_downstream_fan_mean",
    "lg_downstream_fan_max",
]


def line_graph_features(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    as_of: int | None = None,
) -> pl.DataFrame:
    """Per-node line-graph flow statistics for the graph that exists at ``as_of``."""
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    ids = nodes.select("node_id")
    walk_edges = edges.filter(pl.col("src") != pl.col("dst")).select("src", "dst")
    if walk_edges.is_empty():
        return ids.with_columns(
            pl.lit(0.0).alias("lg_through_count"),
            pl.lit(0.0).alias("lg_through_log1p"),
            pl.lit(0.0).alias("lg_pass_ratio"),
            *[pl.lit(None, dtype=pl.Float64).alias(c) for c in _COLUMNS[3:]],
        )

    in_deg = walk_edges.group_by("dst").len().rename({"dst": "node_id", "len": "in_deg"})
    out_deg = walk_edges.group_by("src").len().rename({"src": "node_id", "len": "out_deg"})
    deg = (
        ids.join(in_deg, on="node_id", how="left")
        .join(out_deg, on="node_id", how="left")
        .with_columns(
            pl.col("in_deg").fill_null(0).cast(pl.Float64),
            pl.col("out_deg").fill_null(0).cast(pl.Float64),
        )
    )

    base = deg.with_columns(
        (pl.col("in_deg") * pl.col("out_deg")).alias("lg_through_count")
    ).with_columns(
        pl.col("lg_through_count").log1p().alias("lg_through_log1p"),
        # 0/0 for isolated nodes is a genuine "no flow", not unknown → 0.0
        pl.when(pl.col("in_deg") + pl.col("out_deg") > 0)
        .then(pl.col("lg_through_count") / (pl.col("in_deg") + pl.col("out_deg")))
        .otherwise(0.0)
        .alias("lg_pass_ratio"),
    )

    # upstream fan at v: in_deg_L of each in-edge (u→v) is in_deg(u)
    upstream = (
        walk_edges.join(
            deg.select(pl.col("node_id").alias("src"), pl.col("in_deg").alias("src_in_deg")),
            on="src",
            how="left",
        )
        .group_by("dst")
        .agg(
            pl.col("src_in_deg").mean().alias("lg_upstream_fan_mean"),
            pl.col("src_in_deg").max().alias("lg_upstream_fan_max"),
        )
        .rename({"dst": "node_id"})
    )
    # downstream fan at v: out_deg_L of each out-edge (v→w) is out_deg(w)
    downstream = (
        walk_edges.join(
            deg.select(pl.col("node_id").alias("dst"), pl.col("out_deg").alias("dst_out_deg")),
            on="dst",
            how="left",
        )
        .group_by("src")
        .agg(
            pl.col("dst_out_deg").mean().alias("lg_downstream_fan_mean"),
            pl.col("dst_out_deg").max().alias("lg_downstream_fan_max"),
        )
        .rename({"src": "node_id"})
    )

    return (
        base.drop("in_deg", "out_deg")
        .join(upstream, on="node_id", how="left")
        .join(downstream, on="node_id", how="left")
        .with_columns(pl.col(c).cast(pl.Float64) for c in _COLUMNS)
    )
