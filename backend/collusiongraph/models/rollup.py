"""Community roll-up (§4.4, §7 step 13): Leiden → calibrated member scores →
community scores.

The system ranks communities/subgraphs, not bare nodes: Leiden runs on the
undirected weighted projection (edge weight = interaction multiplicity),
member scores are isotonic-calibrated on the validation pool so they are
probabilistically meaningful, and the community score is the §4.4 budget-aware
aggregation — the mean of the calibrated max and the top-p member mean.
Community-level anomaly features join the ensemble in Week 5.
"""

from __future__ import annotations

import igraph as ig
import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression


def leiden_communities(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    seed: int = 0,
    resolution: float = 1.0,
    min_size: int = 2,
) -> pl.DataFrame:
    """IR communities frame from Leiden on the undirected weighted projection.

    Singletons (< ``min_size``) are dropped — a one-node community is a node
    ranking in disguise, and node-level queues are reported separately.
    """
    import leidenalg

    node_ids = nodes["node_id"].to_list()
    index = {nid: i for i, nid in enumerate(node_ids)}
    weights = edges.select("src", "dst").group_by("src", "dst").len(name="_w")
    pairs = [(index[s], index[d]) for s, d in weights.select("src", "dst").iter_rows()]
    g = ig.Graph(n=len(node_ids), edges=pairs, directed=False)
    g.es["weight"] = weights["_w"].to_list()
    g.simplify(multiple=True, loops=True, combine_edges={"weight": "sum"})

    partition = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights="weight",
        resolution_parameter=resolution,
        seed=seed,
    )
    rows = [
        {
            "community_id": f"leiden:{k}",
            "member_node_ids": [node_ids[i] for i in members],
            "method": f"leiden(resolution={resolution},seed={seed})",
        }
        for k, members in enumerate(partition)
        if len(members) >= min_size
    ]
    return pl.DataFrame(
        rows,
        schema={
            "community_id": pl.Utf8,
            "member_node_ids": pl.List(pl.Utf8),
            "method": pl.Utf8,
        },
    )


def isotonic_calibrator(val_scores: np.ndarray, val_y: np.ndarray) -> IsotonicRegression:
    """Fit isotonic calibration on the VALIDATION pool (§4.4 — members are
    calibrated before fusion/roll-up so scores are comparable and meaningful).
    Monotonicity — score ordering preserved — is pinned by the §9.1 test."""
    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(val_scores, val_y)
    return calibrator


def community_scores(
    communities: pl.DataFrame,
    node_scores: pl.DataFrame,
    top_p: float = 0.25,
) -> pl.DataFrame:
    """§4.4 budget-aware aggregation over calibrated member scores:
    score = (max + mean(top ⌈p·n⌉ members)) / 2. Members without a score
    (e.g. never scored node types) contribute nothing."""
    member_scores = (
        communities.select("community_id", "member_node_ids")
        .explode("member_node_ids", empty_as_null=False)
        .rename({"member_node_ids": "node_id"})
        .join(node_scores, on="node_id", how="inner")
        .sort("community_id", "score", descending=[False, True])
    )
    agg = member_scores.group_by("community_id").agg(
        pl.col("score").max().alias("_max"),
        pl.col("score")
        .head(
            pl.max_horizontal(pl.lit(1), (pl.len().cast(pl.Float64) * top_p).ceil().cast(pl.Int64))
        )
        .mean()
        .alias("_top_p_mean"),
    )
    return (
        communities.join(agg, on="community_id", how="inner")
        .with_columns(((pl.col("_max") + pl.col("_top_p_mean")) / 2).alias("score"))
        .drop("_max", "_top_p_mean")
        .sort("score", descending=True)
    )
