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
* OCDS (§4.3 D5, §7 step 30): compiled-release JSONL from an OCP Data Registry
  publisher — firm/tender/buyer nodes; ``awarded`` + ``buys_from`` core;
  ``bids_on`` enrichment wherever the publisher populates ``bids.details`` with
  identified tenderers (the D5 selection criterion — Georgia OpenTender does,
  losing bidders included). **No ground-truth labels exist**: every firm/tender
  is emitted ``unknown`` — this is the unsupervised-regime / synthetic-injection
  substrate, never a supervised anchor.

Timestamps use the year as the time unit (Mendeley has only ``tender_year``;
García dates are reduced to year for cross-market comparability; OCDS release
dates are reduced to year to match; full dates where present are preserved in
``raw_attrs``).
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
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


def mendeley_firm_labels_as_of(edges: pl.DataFrame, as_of: int) -> pl.DataFrame:
    """Firm labels reconstructed from award-level ground truth AT ``as_of``.

    The stored ``labels`` table rolls ``is_cartel`` up over a firm's ENTIRE
    history — training on it under a temporal split leaks future cartel
    activity into train-period targets (audit F1). This derives the label a
    supervisor could have known at ``as_of``: illicit iff any award timestamped
    ≤ as_of carries ``is_cartel=1``; licit otherwise. Firms with no awards by
    ``as_of`` are simply absent (unknowable then). Evaluation of TEST
    predictions still uses the stored full-knowledge labels — ground truth is
    assessed after the fact; training targets must not be.
    """
    awarded = edges.filter(
        (pl.col("edge_type") == EdgeType.AWARDED.value)
        & pl.col("timestamp").is_not_null()
        & (pl.col("timestamp") <= as_of)
    )
    per_firm = (
        awarded.with_columns(
            pl.col("raw_attrs")
            .str.json_path_match("$.is_cartel")
            .cast(pl.Int64, strict=False)
            .fill_null(0)
            .alias("_cartel")
        )
        .group_by(pl.col("dst").alias("node_id"))
        .agg(pl.col("_cartel").max())
    )
    return per_firm.select(
        "node_id",
        pl.when(pl.col("_cartel") == 1)
        .then(pl.lit(Label.ILLICIT.value))
        .otherwise(pl.lit(Label.LICIT.value))
        .alias("label"),
        pl.lit(f"mendeley_is_cartel_asof_{as_of}").alias("label_source"),
        pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
    )


def _release_year(release: dict[str, Any]) -> int | None:
    """Year of a compiled release: release date first, tenderPeriod.endDate fallback."""
    for candidate in (
        release.get("date"),
        ((release.get("tender") or {}).get("tenderPeriod") or {}).get("endDate"),
    ):
        if isinstance(candidate, str) and len(candidate) >= 4 and candidate[:4].isdigit():
            return int(candidate[:4])
    return None


def _ocds_lines(raw_dir: Path) -> Iterator[str]:
    """Stream lines from every ``*.jsonl.gz`` / ``*.jsonl`` under ``raw_dir``."""
    paths = sorted(p for p in raw_dir.iterdir() if p.name.endswith((".jsonl", ".jsonl.gz")))
    if not paths:
        raise FileNotFoundError(f"no *.jsonl[.gz] release files in {raw_dir} — run poe data first")
    for path in paths:
        if path.name.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                yield from fh
        else:
            yield from path.open(encoding="utf-8")


def ocds_to_ir(
    raw_dir: Path | str,
    store: GraphStore,
    dataset: str = "ocds_georgia",
    publisher: str = "georgia",
) -> dict[str, Any]:
    """OCDS compiled-release JSONL → IR graph (unlabeled; §4.3 D5). Returns stats.

    Award-network-first (§4.2 rule 1): ``awarded``/``buys_from`` come from
    ``awards[]``/``buyer`` and function alone; ``bids_on`` activates per release
    wherever ``bids.details[]`` carries identified tenderers. Bids without a
    tenderer id are counted (``bids_skipped_no_tenderer``), never guessed at.
    Releases with no derivable year are counted and skipped
    (``releases_skipped_no_date``) — undated edges cannot enter a temporal
    split honestly (§9.1b).
    """
    raw = Path(raw_dir)
    node_first_seen: dict[str, tuple[str, int]] = {}  # node_id -> (node_type, min year)
    edge_rows: list[dict[str, Any]] = []
    n_releases = n_no_date = n_bids_skipped = n_bids_kept = 0
    years: dict[int, int] = {}

    def see(node_id: str, node_type: NodeType, year: int) -> None:
        prev = node_first_seen.get(node_id)
        if prev is None or year < prev[1]:
            node_first_seen[node_id] = (node_type.value, year)

    for line in _ocds_lines(raw):
        if not line.strip():
            continue
        release = json.loads(line)
        n_releases += 1
        year = _release_year(release)
        if year is None:
            n_no_date += 1
            continue
        years[year] = years.get(year, 0) + 1

        ocid = release["ocid"]
        tender_id = f"tender:{publisher}:{ocid}"
        tender = release.get("tender") or {}
        see(tender_id, NodeType.TENDER, year)

        buyer = release.get("buyer") or {}
        if buyer.get("id"):
            buyer_id = f"buyer:{publisher}:{buyer['id']}"
            see(buyer_id, NodeType.BUYER, year)
            edge_rows.append(
                {
                    "src": buyer_id,
                    "dst": tender_id,
                    "edge_type": EdgeType.BUYS_FROM.value,
                    "timestamp": year,
                    "amount": (tender.get("value") or {}).get("amount"),
                    "directed": True,
                    "raw_attrs": None,
                }
            )

        for bid in (release.get("bids") or {}).get("details") or []:
            tenderers = [t for t in bid.get("tenderers") or [] if t.get("id")]
            if not tenderers:
                n_bids_skipped += 1
                continue
            n_bids_kept += 1
            for tenderer in tenderers:
                firm_id = f"firm:{publisher}:{tenderer['id']}"
                see(firm_id, NodeType.FIRM, year)
                edge_rows.append(
                    {
                        "src": firm_id,
                        "dst": tender_id,
                        "edge_type": EdgeType.BIDS_ON.value,
                        "timestamp": year,
                        "amount": (bid.get("value") or {}).get("amount"),
                        "directed": True,
                        "raw_attrs": _json_attrs(
                            bid_id=bid.get("id"),
                            date=release.get("date"),
                            currency=(bid.get("value") or {}).get("currency"),
                            n_tenderers=len(tenderers),
                        ),
                    }
                )

        for award in release.get("awards") or []:
            for supplier in award.get("suppliers") or []:
                if not supplier.get("id"):
                    continue
                firm_id = f"firm:{publisher}:{supplier['id']}"
                see(firm_id, NodeType.FIRM, year)
                edge_rows.append(
                    {
                        "src": tender_id,
                        "dst": firm_id,
                        "edge_type": EdgeType.AWARDED.value,
                        "timestamp": year,
                        "amount": (award.get("value") or {}).get("amount"),
                        "directed": True,
                        "raw_attrs": _json_attrs(
                            award_id=award.get("id"),
                            date=release.get("date"),
                            related_bid=award.get("relatedBid"),
                        ),
                    }
                )

    nodes = (
        pl.DataFrame(
            {
                "node_id": list(node_first_seen),
                "node_type": [t for t, _ in node_first_seen.values()],
                "time_first_seen": [y for _, y in node_first_seen.values()],
            }
        )
        .select(
            "node_id",
            "node_type",
            pl.lit(Domain.PROCUREMENT.value).alias("domain"),
            pl.col("time_first_seen").cast(pl.Int64),
            pl.lit(None, dtype=pl.List(pl.Float32)).alias("raw_features"),
            pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
        )
        .sort("node_id")
    )
    edges = pl.DataFrame(
        edge_rows,
        schema={
            "src": pl.Utf8,
            "dst": pl.Utf8,
            "edge_type": pl.Utf8,
            "timestamp": pl.Int64,
            "amount": pl.Float64,
            "directed": pl.Boolean,
            "raw_attrs": pl.Utf8,
        },
    )
    # No ground truth exists for this publisher (D5): firms and tenders are
    # emitted `unknown` so downstream label handling is explicit, never absent.
    labels = nodes.filter(
        pl.col("node_type").is_in([NodeType.FIRM.value, NodeType.TENDER.value])
    ).select(
        "node_id",
        pl.lit(Label.UNKNOWN.value).alias("label"),
        pl.lit("ocds_unlabeled").alias("label_source"),
        pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
    )

    store.write(dataset, "nodes", nodes)
    store.write(dataset, "edges", edges)
    store.write(dataset, "labels", labels)
    node_counts = dict(nodes.group_by("node_type").len().sort("node_type").iter_rows())
    stats = {
        "dataset": dataset,
        "adapter_version": ADAPTER_VERSION,
        "time_unit": "year",
        "publisher": publisher,
        "n_releases": n_releases,
        "releases_skipped_no_date": n_no_date,
        "n_nodes": nodes.height,
        "n_edges": edges.height,
        "node_counts": node_counts,
        "edge_counts": dict(edges.group_by("edge_type").len().sort("edge_type").iter_rows()),
        "bids_kept": n_bids_kept,
        "bids_skipped_no_tenderer": n_bids_skipped,
        "years": {str(y): years[y] for y in sorted(years)},
        "note": "unlabeled publisher (§4.3 D5) — unsupervised/injection substrate only; "
        "bids_on carries identified losing bidders (co_bid derived downstream)",
    }
    store.write_meta(dataset, stats)
    return stats


def _json_attrs(**kwargs: Any) -> str:  # small helper for tests/fixtures
    return json.dumps(kwargs, ensure_ascii=False)
