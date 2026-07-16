"""Procurement screens as features (§4.4), in two tiers per §4.2 rule 1.

**Award tier — always available** (derivable from ``awarded``/``buys_from``
edges alone): per-firm award counts, within-market share, buyer-concentration
HHI; per-buyer supplier-concentration HHI and winner-rotation entropy. Markets
come from the node-id group segment (``firm:<market>:<id>``), matching the
LOCO grouping convention.

**Bid tier — enrichment** (activates only where ``bids_on`` price edges exist):
per-tender bid-distribution screens (CV, spread, DIFFP, RD, kurtosis, skew —
the García Rodríguez screen family) and per-firm co-bidding statistics. On an
award-only graph (Mendeley; §4.3 D4) these functions return empty frames — the
degradation path §9.1 requires — never a crash and never fabricated values.

Same as-of discipline as ``structural.py`` (§9.1b).
"""

from __future__ import annotations

import polars as pl

from collusiongraph.schema import EdgeType

from .structural import restrict_as_of


def _market_of(col: str) -> pl.Expr:
    """Group segment of the node id in ``col`` (LOCO convention: ``type:group:id``,
    same rule as ``splits.GROUP_FROM_NODE_ID``)."""
    return pl.col(col).str.split(":").list.get(1).alias("_market")


def _hhi(share_expr: pl.Expr) -> pl.Expr:
    """Herfindahl–Hirschman index of a share column, ∈ (0, 1]."""
    return (share_expr**2).sum()


def award_screens(
    nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None = None
) -> pl.DataFrame:
    """Award-tier screens: one row per firm and per buyer that exists at ``as_of``."""
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    awarded = edges.filter(pl.col("edge_type") == EdgeType.AWARDED.value).select(
        pl.col("src").alias("_tender"), pl.col("dst").alias("_firm")
    )
    buys = edges.filter(pl.col("edge_type") == EdgeType.BUYS_FROM.value).select(
        pl.col("src").alias("_buyer"), pl.col("dst").alias("_tender")
    )
    # buyer of each award, where buyer identity exists (~19.5% of Mendeley rows lack it)
    awards_with_buyer = awarded.join(buys, on="_tender", how="left")

    market_awards = awarded.with_columns(_market_of("_firm"))
    firm = (
        market_awards.group_by("_firm")
        .agg(pl.len().alias("n_awards"), pl.col("_market").first())
        .with_columns(
            (pl.col("n_awards") / pl.col("n_awards").sum().over("_market")).alias("market_share")
        )
        .drop("_market")
    )
    firm_buyer_hhi = (
        awards_with_buyer.drop_nulls("_buyer")
        .group_by("_firm", "_buyer")
        .len()
        .with_columns((pl.col("len") / pl.col("len").sum().over("_firm")).alias("_share"))
        .group_by("_firm")
        .agg(_hhi(pl.col("_share")).alias("buyer_hhi"))
    )
    firm_frame = (
        firm.join(firm_buyer_hhi, on="_firm", how="left")
        .rename({"_firm": "node_id"})
        .select("node_id", "n_awards", "market_share", "buyer_hhi")
    )

    buyer_winner = awards_with_buyer.drop_nulls("_buyer").group_by("_buyer", "_firm").len()
    buyer_frame = (
        buyer_winner.with_columns(
            (pl.col("len") / pl.col("len").sum().over("_buyer")).alias("_share")
        )
        .group_by("_buyer")
        .agg(
            pl.col("len").sum().alias("n_awards_made"),
            pl.len().alias("n_distinct_winners"),
            _hhi(pl.col("_share")).alias("supplier_hhi"),
            # normalized Shannon entropy of winner shares ∈ [0, 1]; null for a
            # single-winner buyer (rotation is undefined, not zero)
            pl.when(pl.len() > 1)
            .then((-(pl.col("_share") * pl.col("_share").log()).sum()) / pl.len().log())
            .alias("winner_rotation_entropy"),
        )
        .rename({"_buyer": "node_id"})
    )
    return pl.concat([firm_frame, buyer_frame], how="diagonal").sort("node_id")


def bid_screens(nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None = None) -> pl.DataFrame:
    """Bid-tier screens per tender, from ``bids_on`` amounts. Empty on award-only graphs.

    The winner is taken as the lowest bid (first-price sealed-bid convention —
    the García markets' setting). Screens follow the screen literature: CV,
    price spread, DIFFP (relative winner–runner-up gap), RD (gap in units of
    losing-bid dispersion), kurtosis, skewness.
    """
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    bids = edges.filter(
        (pl.col("edge_type") == EdgeType.BIDS_ON.value) & pl.col("amount").is_not_null()
    ).select(pl.col("dst").alias("node_id"), pl.col("amount"))
    if bids.is_empty():
        return _EMPTY_BID_SCREENS.clone()

    # amounts arrive sorted ascending within each tender: first() is the winning
    # (lowest) bid, slice(1) are the losing bids
    sorted_bids = bids.sort("node_id", "amount")
    lowest = pl.col("amount").first()
    second = pl.col("amount").slice(1, 1).first()
    enough = pl.len() >= 2  # screens are undefined (null), never fabricated, below quorum
    per_tender = sorted_bids.group_by("node_id", maintain_order=True).agg(
        pl.len().alias("n_bids"),
        pl.when(enough).then(pl.col("amount").std() / pl.col("amount").mean()).alias("bid_cv"),
        pl.when(enough)
        .then((pl.col("amount").max() - pl.col("amount").min()) / pl.col("amount").min())
        .alias("bid_spread"),
        pl.when(enough).then((second - lowest) / lowest).alias("diffp"),
        pl.when(pl.len() >= 3)
        .then((second - lowest) / pl.col("amount").slice(1).std())
        .alias("rd"),
        pl.when(pl.len() >= 4).then(pl.col("amount").kurtosis()).alias("bid_kurtosis"),
        pl.when(pl.len() >= 3).then(pl.col("amount").skew()).alias("bid_skew"),
    )
    return per_tender.sort("node_id")


_EMPTY_BID_SCREENS = pl.DataFrame(
    schema={
        "node_id": pl.Utf8,
        "n_bids": pl.UInt32,
        "bid_cv": pl.Float64,
        "bid_spread": pl.Float64,
        "diffp": pl.Float64,
        "rd": pl.Float64,
        "bid_kurtosis": pl.Float64,
        "bid_skew": pl.Float64,
    }
)


def co_bid_stats(
    nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None = None
) -> pl.DataFrame:
    """Per-firm co-bidding statistics where firm-identified ``bids_on`` edges exist
    (García 4/6 markets): distinct co-bidders and the maximum repeat-pairing count
    with any single partner — the co-bid-clique screen inputs. Empty otherwise."""
    nodes, edges = restrict_as_of(nodes, edges, as_of)
    firm_bids = (
        edges.filter(
            (pl.col("edge_type") == EdgeType.BIDS_ON.value) & pl.col("src").str.starts_with("firm:")
        )
        .select(pl.col("src").alias("_firm"), pl.col("dst").alias("_tender"))
        .unique()
    )
    if firm_bids.is_empty():
        return _EMPTY_CO_BID.clone()

    pairs = (
        firm_bids.join(firm_bids.rename({"_firm": "_other"}), on="_tender")
        .filter(pl.col("_firm") != pl.col("_other"))
        .group_by("_firm", "_other")
        .len(name="_n_shared_tenders")
    )
    return (
        pairs.group_by(pl.col("_firm").alias("node_id"))
        .agg(
            pl.len().alias("n_co_bidders"),
            pl.col("_n_shared_tenders").max().alias("co_bid_repeat_max"),
        )
        .sort("node_id")
    )


_EMPTY_CO_BID = pl.DataFrame(
    schema={"node_id": pl.Utf8, "n_co_bidders": pl.UInt32, "co_bid_repeat_max": pl.UInt32}
)
