"""Shared structural feature template (§4.2 rule 2) — the cross-domain transfer channel.

One template for both domains: degrees, motif participation (triangles, mutual
dyads), clustering coefficient, k-core index, temporal burstiness, and
community-relative statistics — z-scored **within each graph** so cross-graph
and cross-domain comparisons are not dominated by trivial scale differences.

As-of discipline (§9.1b): every public function takes ``as_of``. When set, the
graph is restricted to edges timestamped ``<= as_of`` and nodes first seen
``<= as_of`` before anything is computed — a feature value can never encode
future information. Undated edges are EXCLUDED under as-of (they cannot be
proven to lie in the past; the temporal splitter can afford to keep them only
because it additionally gates on endpoint membership). ``as_of=None`` means "no
temporal restriction" and is only appropriate for entity-disjoint evaluation
(LOCO/LOMO), where time is not the split axis — e.g. the undated García Italy
market.

Features land in a separate artifact (``GraphStore.write_features``), never in
``nodes.parquet`` (decision log 2026-07-14).
"""

from __future__ import annotations

import igraph as ig
import polars as pl

_TIME_COL = "time_first_seen"


def restrict_as_of(
    nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """The graph as it existed at ``as_of``: no future nodes, no future or undated edges.

    Nodes with null ``time_first_seen`` are kept — they cannot be placed on the
    timeline, and their features come only from the edges that survive the cut.
    """
    if as_of is None:
        return nodes, edges
    nodes = nodes.filter(pl.col(_TIME_COL).is_null() | (pl.col(_TIME_COL) <= as_of))
    kept = nodes["node_id"].implode()
    edges = edges.filter(
        (pl.col("timestamp") <= as_of) & pl.col("src").is_in(kept) & pl.col("dst").is_in(kept)
    )
    return nodes, edges


def burstiness(nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None = None) -> pl.DataFrame:
    """Goh–Barabási burstiness B = (σ−μ)/(σ+μ) of a node's inter-event times.

    Events are the timestamps of a node's incident edges (either direction).
    Null for nodes with fewer than three dated events (< 2 gaps); B ∈ [−1, 1),
    with B → 1 for bursty activity and B < 0 for regular spacing.
    """
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    dated = edges.filter(pl.col("timestamp").is_not_null())
    events = pl.concat(
        [
            dated.select(pl.col("src").alias("node_id"), "timestamp"),
            dated.select(pl.col("dst").alias("node_id"), "timestamp"),
        ]
    )
    gaps = (
        events.sort("node_id", "timestamp")
        .with_columns(pl.col("timestamp").diff().over("node_id").alias("_gap"))
        .drop_nulls("_gap")
    )
    stats = gaps.group_by("node_id").agg(
        pl.col("_gap").mean().alias("_mu"),
        pl.col("_gap").std().alias("_sigma"),  # null when only one gap
    )
    b = stats.select(
        "node_id",
        # all-simultaneous events give sigma+mu = 0: burstiness is undefined
        # (null), never 0/0 = NaN — NaN would poison per-graph z-scoring
        pl.when((pl.col("_sigma") + pl.col("_mu")) > 0)
        .then((pl.col("_sigma") - pl.col("_mu")) / (pl.col("_sigma") + pl.col("_mu")))
        .alias("burstiness"),
    )
    return nodes.select("node_id").join(b, on="node_id", how="left")


def _degree_frame(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    """Multi-edge in/out/total degrees (repeated interactions count — they are signal)."""
    out_deg = edges.group_by(pl.col("src").alias("node_id")).len(name="degree_out")
    in_deg = edges.group_by(pl.col("dst").alias("node_id")).len(name="degree_in")
    return (
        nodes.select("node_id")
        .join(in_deg, on="node_id", how="left")
        .join(out_deg, on="node_id", how="left")
        .with_columns(
            pl.col("degree_in").fill_null(0).cast(pl.Int64),
            pl.col("degree_out").fill_null(0).cast(pl.Int64),
        )
        .with_columns((pl.col("degree_in") + pl.col("degree_out")).alias("degree_total"))
    )


def _mutual_degree(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    """Per node: distinct neighbors j with both i→j and j→i (directed-dyad motif)."""
    directed = edges.filter(pl.col("directed")).select("src", "dst").unique()
    mutual = directed.join(
        directed.select(pl.col("dst").alias("src"), pl.col("src").alias("dst")),
        on=["src", "dst"],
    )
    counts = mutual.group_by(pl.col("src").alias("node_id")).len(name="mutual_degree")
    return (
        nodes.select("node_id")
        .join(counts, on="node_id", how="left")
        .with_columns(pl.col("mutual_degree").fill_null(0).cast(pl.Int64))
    )


def _igraph_metrics(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    """Clustering coefficient, k-core index, triangle participation, component id
    on the simple undirected projection."""
    node_ids = nodes["node_id"].to_list()
    index = {nid: i for i, nid in enumerate(node_ids)}
    pairs = [(index[s], index[d]) for s, d in edges.select("src", "dst").iter_rows()]
    g = ig.Graph(n=len(node_ids), edges=pairs, directed=False)
    g.simplify(multiple=True, loops=True)

    clustering = g.transitivity_local_undirected(mode="zero")
    coreness = g.coreness()
    simple_degree = g.degree()
    triangles = [round(c * d * (d - 1) / 2) for c, d in zip(clustering, simple_degree, strict=True)]
    component = g.connected_components(mode="weak").membership
    return pl.DataFrame(
        {
            # explicit dtype: an empty node set must not degrade node_id to Null
            "node_id": pl.Series(node_ids, dtype=pl.Utf8),
            "clustering": pl.Series(clustering, dtype=pl.Float64),
            "kcore": pl.Series(coreness, dtype=pl.Int64),
            "triangles": pl.Series(triangles, dtype=pl.Int64),
            "_component": pl.Series(component, dtype=pl.Int64),
        }
    )


def _community_stats(features: pl.DataFrame, communities: pl.DataFrame | None) -> pl.DataFrame:
    """Community size and degree relative to the community mean.

    ``communities`` is an IR communities frame (§4.2); when None, weakly
    connected components (already on ``features`` as ``_component``) stand in
    until Leiden communities exist (§7 step 13).
    """
    if communities is None:
        membership = features.select("node_id", pl.col("_component").alias("_community"))
    else:
        membership = communities.select(
            pl.col("member_node_ids").alias("node_id"), pl.col("community_id").alias("_community")
        ).explode("node_id", empty_as_null=False)
    stats = (
        features.join(membership, on="node_id", how="left")
        .with_columns(
            pl.len().over("_community").alias("community_size"),
            pl.col("degree_total").mean().over("_community").alias("_comm_mean_degree"),
        )
        .with_columns(
            pl.when(pl.col("_comm_mean_degree") > 0)
            .then(pl.col("degree_total") / pl.col("_comm_mean_degree"))
            .otherwise(pl.lit(1.0))
            .alias("degree_rel_community")
        )
    )
    return stats.drop("_community", "_comm_mean_degree", "_component")


def structural_features(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    as_of: int | None = None,
    communities: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """The full §4.2 rule-2 template, raw (un-z-scored) values, one row per node
    that exists at ``as_of``."""
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    features = (
        _degree_frame(nodes, edges)
        .join(_mutual_degree(nodes, edges), on="node_id")
        .join(_igraph_metrics(nodes, edges), on="node_id")
        .join(burstiness(nodes, edges), on="node_id", how="left")
    )
    return _community_stats(features, communities).sort("node_id")


def fit_zscore(features: pl.DataFrame, id_col: str = "node_id") -> dict[str, tuple[float, float]]:
    """Column means/stds to FREEZE from one graph (the training graph) and
    re-apply elsewhere (audit F3): training under one normalization and scoring
    under another is a train/serve skew — the trainer fits stats on the train
    graph and applies them to the inference graph. ``zscore_per_graph`` remains
    the §4.2 rule-2 transfer-channel transform (each graph normalized to
    itself); this pair is the model-input transform."""
    stats: dict[str, tuple[float, float]] = {}
    for name, dtype in features.schema.items():
        if name == id_col or not dtype.is_numeric():
            continue
        col = features[name].cast(pl.Float64)
        mean, std = col.mean(), col.std()
        stats[name] = (
            float(mean) if isinstance(mean, float) else 0.0,
            float(std) if isinstance(std, float) and std > 0 else 0.0,
        )
    return stats


def apply_zscore(
    features: pl.DataFrame,
    stats: dict[str, tuple[float, float]],
    id_col: str = "node_id",
    fill_null: bool = True,
) -> pl.DataFrame:
    """Apply frozen z-scoring stats. Columns unseen at fit time are dropped
    (the model has no weights for them); zero-variance columns become 0.0."""
    exprs: list[pl.Expr] = [pl.col(id_col)]
    for name, (mean, std) in stats.items():
        if name not in features.columns:
            raise ValueError(f"column {name!r} missing from features at apply time")
        col = pl.col(name).cast(pl.Float64)
        z = ((col - mean) / std) if std > 0 else pl.lit(0.0)
        if fill_null:
            z = z.fill_null(0.0)
        exprs.append(z.alias(name))
    return features.select(exprs)


def zscore_per_graph(
    features: pl.DataFrame, id_col: str = "node_id", fill_null: bool = True
) -> pl.DataFrame:
    """Z-score every numeric column within this graph (§4.2 rule 2).

    Zero-variance columns become 0.0 (no information, no NaN poison). Nulls
    (e.g. burstiness on inactive nodes) become 0.0 — the graph mean — unless
    ``fill_null=False``.
    """
    exprs: list[pl.Expr] = []
    for name, dtype in features.schema.items():
        if name == id_col:
            exprs.append(pl.col(name))
            continue
        if not dtype.is_numeric():
            exprs.append(pl.col(name))
            continue
        col = pl.col(name).cast(pl.Float64)
        z = (
            pl.when(col.std().fill_null(0.0) > 0)
            .then((col - col.mean()) / col.std())
            .otherwise(pl.lit(0.0))
        )
        if fill_null:
            z = z.fill_null(0.0)
        exprs.append(z.alias(name))
    return features.select(exprs)
