"""Procurement adapters → CollusionGraph IR (§4.3 D3/D4, §4.2).

Award-network-first (§4.2 rule 1): every output functions on the award-derived
core graph alone; enrichment tiers activate only where the data carries them.

* Mendeley EU cartel: award-level — firm/tender/buyer nodes; ``awarded`` and
  ``buys_from`` core edges; **no losing-bidder identities exist** (verified in
  Week-1 EDA), so no ``bids_on``/``co_bid`` edges are emitted. Cartel labels
  (``is_cartel``) attach to firms and tenders.
* García Rodríguez: bid-level per market — tender + bid nodes with ``bids_on``
  price edges everywhere; **firm identities exist in 4 of 6 markets**
  (Japan, Italy, Brazil, America carry ``Competitors``; the two Swiss markets
  do not), so firm nodes, ``awarded`` and ``co_bid`` edges are emitted only
  there. Collusion labels attach to bids (and firms where identified).

Timestamps use the year as the time unit (Mendeley has only ``tender_year``;
García dates are reduced to year for cross-market comparability; full dates
where present are preserved in ``raw_attrs``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from collusiongraph.schema import Domain, EdgeType, GraphStore, Label, NodeType

ADAPTER_VERSION = "0.1.0"

_SCREEN_COLS = ["CV", "SPD", "DIFFP", "RD", "KURT", "SKEW", "KSTEST"]

# Markets in the García supplement: file stem -> whether bidder identities
# (the ``Competitors`` company-ID column) exist. Verified against README.txt
# and the actual headers, 2026-07-13.
GARCIA_MARKETS: dict[str, bool] = {
    "Japan": True,
    "Italy": True,
    "Brazil": True,
    "America": True,
    "Switzerland_Ticino": False,
    "Switzerland_GR_and_See-Gaster": False,
}


def _node_frame(
    ids: pl.Series, node_type: NodeType, times: pl.Series | None = None
) -> pl.DataFrame:
    df = pl.DataFrame({"node_id": ids})
    time_col = (
        pl.lit(None, dtype=pl.Int64)
        if times is None
        else pl.Series("time_first_seen", times).cast(pl.Int64)
    )
    return df.with_columns(
        pl.lit(node_type.value).alias("node_type"),
        pl.lit(Domain.PROCUREMENT.value).alias("domain"),
        time_col.alias("time_first_seen") if times is None else time_col,
        pl.lit(None, dtype=pl.List(pl.Float32)).alias("raw_features"),
        pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
    ).select("node_id", "node_type", "domain", "time_first_seen", "raw_features", "raw_attrs")


def mendeley_to_ir(
    raw_dir: Path | str,
    store: GraphStore,
    dataset: str = "mendeley_eu",
    csv_name: str = "GTI_labelled_cartel_data_NOV2023.csv",
) -> dict[str, Any]:
    """Mendeley EU cartel CSV → IR award-first graph. Returns summary stats."""
    raw = Path(raw_dir)
    df = pl.read_csv(raw / csv_name, infer_schema_length=20_000, ignore_errors=True)

    df = df.with_columns(
        pl.format("firm:{}:{}", pl.col("country"), pl.col("bidder_id")).alias("_firm"),
        pl.format("tender:{}:{}", pl.col("country"), pl.col("tender_id")).alias("_tender"),
        # ~19.5% of rows have no buyer_id (measured 2026-07-13); those buyers are
        # unidentifiable — no buyer node, no buys_from edge (award core unaffected).
        pl.format("buyer:{}:{}", pl.col("country"), pl.col("buyer_id")).alias("_buyer"),
        pl.col("tender_year").cast(pl.Int64).alias("_year"),
    )

    firms = df.group_by("_firm").agg(pl.col("_year").min())
    tenders = df.group_by("_tender").agg(pl.col("_year").min())
    buyers = df.filter(pl.col("_buyer").is_not_null()).group_by("_buyer").agg(pl.col("_year").min())
    nodes = pl.concat(
        [
            _node_frame(firms["_firm"], NodeType.FIRM, firms["_year"]),
            _node_frame(tenders["_tender"], NodeType.TENDER, tenders["_year"]),
            _node_frame(buyers["_buyer"], NodeType.BUYER, buyers["_year"]),
        ]
    ).sort("node_id")

    awarded = df.select(
        pl.col("_tender").alias("src"),
        pl.col("_firm").alias("dst"),
        pl.lit(EdgeType.AWARDED.value).alias("edge_type"),
        pl.col("_year").alias("timestamp"),
        pl.lit(None, dtype=pl.Float64).alias("amount"),
        pl.lit(True).alias("directed"),
        pl.struct(
            lot_id=pl.col("lot_id"),
            is_cartel=pl.col("is_cartel"),
            cartel_id=pl.col("cartel_id"),
            lot_bidscount=pl.col("lot_bidscount"),
            relative_value=pl.col("relative_value"),
        )
        .struct.json_encode()
        .alias("raw_attrs"),
    )
    buys_from = (
        df.filter(pl.col("_buyer").is_not_null())
        .unique(subset=["_buyer", "_tender"])
        .select(
            pl.col("_buyer").alias("src"),
            pl.col("_tender").alias("dst"),
            pl.lit(EdgeType.BUYS_FROM.value).alias("edge_type"),
            pl.col("_year").alias("timestamp"),
            pl.lit(None, dtype=pl.Float64).alias("amount"),
            pl.lit(True).alias("directed"),
            pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
        )
    )
    edges = pl.concat([awarded, buys_from])

    firm_labels = (
        df.group_by("_firm")
        .agg(pl.col("is_cartel").max().alias("_cartel"))
        .rename({"_firm": "node_id"})
    )
    tender_labels = (
        df.group_by("_tender")
        .agg(pl.col("is_cartel").max().alias("_cartel"))
        .rename({"_tender": "node_id"})
    )
    labels = pl.concat([firm_labels, tender_labels]).select(
        pl.col("node_id"),
        pl.when(pl.col("_cartel") == 1)
        .then(pl.lit(Label.ILLICIT.value))
        .otherwise(pl.lit(Label.LICIT.value))
        .alias("label"),
        pl.lit("mendeley_is_cartel").alias("label_source"),
        pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
    )

    store.write(dataset, "nodes", nodes)
    store.write(dataset, "edges", edges)
    store.write(dataset, "labels", labels)
    stats = {
        "dataset": dataset,
        "adapter_version": ADAPTER_VERSION,
        "time_unit": "year",
        "n_nodes": nodes.height,
        "n_edges": edges.height,
        "countries": sorted(df["country"].unique().to_list()),
        "label_counts": dict(labels.group_by("label").len().sort("label").iter_rows()),
        "note": "award-network core only — no losing-bidder identities in this dataset "
        "(§4.2 rule 1; Week-1 EDA); co-bid tier lives on García Rodríguez markets",
    }
    store.write_meta(dataset, stats)
    return stats


def _garcia_market_frame(path: Path, market: str) -> pl.DataFrame:
    df = pl.read_csv(path, infer_schema_length=20_000, ignore_errors=True)
    if "Date" not in df.columns:  # Italy ships no Date column
        year = pl.lit(None, dtype=pl.Int64)
    elif df["Date"].dtype.is_integer():  # epoch seconds (e.g. Japan)
        year = pl.from_epoch(pl.col("Date"), time_unit="s").dt.year().cast(pl.Int64)
    else:
        year = pl.col("Date").str.to_datetime(strict=False).dt.year().cast(pl.Int64)
    return df.with_columns(
        pl.lit(market).alias("_market"),
        year.alias("_year"),
        pl.format("tender:{}:{}", pl.lit(market), pl.col("Tender")).alias("_tender"),
        pl.int_range(pl.len()).alias("_bid_seq"),
    )


def garcia_to_ir(
    raw_dir: Path | str,
    store: GraphStore,
    dataset: str = "garcia_rodriguez",
    markets: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """García Rodríguez per-market CSVs → IR bid graph. Returns summary stats."""
    raw = Path(raw_dir)
    markets = GARCIA_MARKETS if markets is None else markets

    all_nodes, all_edges, all_labels = [], [], []
    per_market: dict[str, dict[str, int | bool]] = {}

    for market, has_firm_ids in markets.items():
        df = _garcia_market_frame(raw / f"DB_Collusion_{market}_processed.csv", market)
        df = df.with_columns(
            pl.format("bid:{}:{}", pl.lit(market), pl.col("_bid_seq")).alias("_bid")
        )

        tenders = df.group_by("_tender").agg(pl.col("_year").min())
        all_nodes.append(_node_frame(tenders["_tender"], NodeType.TENDER, tenders["_year"]))
        all_nodes.append(_node_frame(df["_bid"], NodeType.BID, df["_year"]))

        screen_struct = pl.struct(
            [pl.col("Winner").alias("winner"), pl.col("Number_bids").alias("number_bids")]
            + [pl.col(s).alias(s.lower()) for s in _SCREEN_COLS if s in df.columns]
        )
        all_edges.append(
            df.select(
                pl.col("_bid").alias("src"),
                pl.col("_tender").alias("dst"),
                pl.lit(EdgeType.BIDS_ON.value).alias("edge_type"),
                pl.col("_year").alias("timestamp"),
                pl.col("Bid_value").cast(pl.Float64).alias("amount"),
                pl.lit(True).alias("directed"),
                screen_struct.struct.json_encode().alias("raw_attrs"),
            )
        )
        all_labels.append(
            df.select(
                pl.col("_bid").alias("node_id"),
                pl.when(pl.col("Collusive_competitor") == 1)
                .then(pl.lit(Label.ILLICIT.value))
                .otherwise(pl.lit(Label.LICIT.value))
                .alias("label"),
                pl.lit("garcia_collusive_competitor").alias("label_source"),
                pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
            )
        )

        if has_firm_ids:
            df = df.with_columns(
                pl.format("firm:{}:{}", pl.lit(market), pl.col("Competitors")).alias("_firm")
            )
            firms = df.group_by("_firm").agg(pl.col("_year").min())
            all_nodes.append(_node_frame(firms["_firm"], NodeType.FIRM, firms["_year"]))
            # firm -> tender bid participation (identity-attributed enrichment)
            all_edges.append(
                df.select(
                    pl.col("_firm").alias("src"),
                    pl.col("_tender").alias("dst"),
                    pl.lit(EdgeType.BIDS_ON.value).alias("edge_type"),
                    pl.col("_year").alias("timestamp"),
                    pl.col("Bid_value").cast(pl.Float64).alias("amount"),
                    pl.lit(True).alias("directed"),
                    pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
                )
            )
            all_edges.append(
                df.filter(pl.col("Winner") == 1).select(
                    pl.col("_tender").alias("src"),
                    pl.col("_firm").alias("dst"),
                    pl.lit(EdgeType.AWARDED.value).alias("edge_type"),
                    pl.col("_year").alias("timestamp"),
                    pl.col("Bid_value").cast(pl.Float64).alias("amount"),
                    pl.lit(True).alias("directed"),
                    pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
                )
            )
            firm_labels = (
                df.group_by("_firm")
                .agg(pl.col("Collusive_competitor").max().alias("_coll"))
                .select(
                    pl.col("_firm").alias("node_id"),
                    pl.when(pl.col("_coll") == 1)
                    .then(pl.lit(Label.ILLICIT.value))
                    .otherwise(pl.lit(Label.LICIT.value))
                    .alias("label"),
                    pl.lit("garcia_collusive_competitor").alias("label_source"),
                    pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
                )
            )
            all_labels.append(firm_labels)

        per_market[market] = {
            "rows": df.height,
            "tenders": tenders.height,
            "firm_identities": has_firm_ids,
        }

    nodes = pl.concat(all_nodes).unique(subset=["node_id"], keep="first").sort("node_id")
    edges = pl.concat(all_edges)
    labels = pl.concat(all_labels).unique(subset=["node_id"], keep="first")

    store.write(dataset, "nodes", nodes)
    store.write(dataset, "edges", edges)
    store.write(dataset, "labels", labels)
    stats = {
        "dataset": dataset,
        "adapter_version": ADAPTER_VERSION,
        "time_unit": "year",
        "n_nodes": nodes.height,
        "n_edges": edges.height,
        "markets": per_market,
        "label_counts": dict(labels.group_by("label").len().sort("label").iter_rows()),
        "note": "bid-price tier on all markets; firm identities (awarded edges, firm "
        "labels) on 4/6 markets only — co_bid projection is derived downstream "
        "from shared-tender participation, not materialized here",
    }
    store.write_meta(dataset, stats)
    return stats


def _json_attrs(**kwargs: Any) -> str:  # small helper for tests/fixtures
    return json.dumps(kwargs, ensure_ascii=False)
