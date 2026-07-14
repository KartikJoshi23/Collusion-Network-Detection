"""Financial adapters → CollusionGraph IR (§4.3 D1/D2, §4.2).

* Elliptic++ transactions: tx–tx graph — transaction nodes carry the 183 raw
  features (time step included, matching the dataset's own feature count);
  ``pays`` edges are timestamped with the source transaction's time step.
* AMLworld HI-Small: account graph — account nodes, one ``pays`` edge per
  transaction with true amount; edge-level laundering ground truth rides in
  ``raw_attrs`` and is rolled up to node labels (full ground truth, §4.3 D2).

Adapters are faithful: they do not filter or fence anything. The AMLworld
post-window tail (59.1% laundering after the primary window — Week-1 EDA) is
recorded in dataset meta as ``primary_window_end`` for the splitters to fence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from collusiongraph.schema import Domain, EdgeType, GraphStore, Label, NodeType

ADAPTER_VERSION = "0.1.0"

_ELLIPTIC_CLASS_MAP = {"1": Label.ILLICIT, "2": Label.LICIT, "3": Label.UNKNOWN}


def elliptic_pp_to_ir(
    raw_dir: Path | str, store: GraphStore, dataset: str = "elliptic_pp"
) -> dict[str, Any]:
    """Elliptic++ transactions CSVs → IR tables. Returns summary stats."""
    raw = Path(raw_dir)
    features = pl.read_csv(raw / "txs_features.csv", infer_schema_length=10_000)
    classes = pl.read_csv(raw / "txs_classes.csv", infer_schema_length=10_000)
    edgelist = pl.read_csv(raw / "txs_edgelist.csv", infer_schema_length=10_000)

    id_col, ts_col = features.columns[0], features.columns[1]
    feature_cols = features.columns[1:]  # 183 features, time step included

    nodes = features.select(
        (pl.lit("tx:") + pl.col(id_col).cast(pl.Utf8)).alias("node_id"),
        pl.lit(NodeType.TRANSACTION.value).alias("node_type"),
        pl.lit(Domain.FINANCIAL.value).alias("domain"),
        pl.col(ts_col).cast(pl.Int64).alias("time_first_seen"),
        pl.concat_list([pl.col(c).cast(pl.Float32) for c in feature_cols]).alias("raw_features"),
        pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
    )

    node_times = features.select(
        pl.col(id_col).alias("_id"), pl.col(ts_col).cast(pl.Int64).alias("_ts")
    )
    src_col, dst_col = edgelist.columns[0], edgelist.columns[1]
    edges = edgelist.join(node_times, left_on=src_col, right_on="_id", how="left").select(
        (pl.lit("tx:") + pl.col(src_col).cast(pl.Utf8)).alias("src"),
        (pl.lit("tx:") + pl.col(dst_col).cast(pl.Utf8)).alias("dst"),
        pl.lit(EdgeType.PAYS.value).alias("edge_type"),
        pl.col("_ts").alias("timestamp"),
        pl.lit(None, dtype=pl.Float64).alias("amount"),
        pl.lit(True).alias("directed"),
        pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
    )

    class_col = classes.columns[-1]
    labels = classes.select(
        (pl.lit("tx:") + pl.col(classes.columns[0]).cast(pl.Utf8)).alias("node_id"),
        pl.col(class_col)
        .cast(pl.Utf8)
        .replace_strict(
            {k: v.value for k, v in _ELLIPTIC_CLASS_MAP.items()},
            default=Label.UNKNOWN.value,
        )
        .alias("label"),
        pl.lit("elliptic_pp").alias("label_source"),
        pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
    )

    store.write(dataset, "nodes", nodes)
    store.write(dataset, "edges", edges)
    store.write(dataset, "labels", labels)
    stats = {
        "dataset": dataset,
        "adapter_version": ADAPTER_VERSION,
        "time_unit": "elliptic_time_step",
        "n_nodes": nodes.height,
        "n_edges": edges.height,
        "n_features": len(feature_cols),
        "feature_names": feature_cols,
        "label_counts": dict(labels.group_by("label").len().sort("label").iter_rows()),
    }
    store.write_meta(dataset, stats)
    return stats


# AMLworld's primary activity window for HI-Small ends 2022-09-10 (Kaggle
# discussion #427517); measured in Week-1 EDA: the tail after it is 59.1%
# laundering. Splitters fence on this value.
_AMLWORLD_HI_SMALL_WINDOW_END = int(datetime(2022, 9, 10, 23, 59, tzinfo=UTC).timestamp() // 60)


def amlworld_to_ir(
    raw_dir: Path | str,
    store: GraphStore,
    dataset: str = "amlworld_hi_small",
    trans_file: str = "HI-Small_Trans.csv",
) -> dict[str, Any]:
    """AMLworld transactions CSV → IR account graph. Returns summary stats."""
    raw = Path(raw_dir)
    df = pl.read_csv(raw / trans_file, infer_schema_length=10_000)

    from_acct = pl.format("acct:{}:{}", pl.col("From Bank"), pl.col("Account"))
    to_acct = pl.format("acct:{}:{}", pl.col("To Bank"), pl.col("Account_duplicated_0"))
    ts_minutes = (
        pl.col("Timestamp")
        .str.to_datetime("%Y/%m/%d %H:%M", time_zone="UTC")
        .dt.epoch(time_unit="s")
        .floordiv(60)
        .cast(pl.Int64)
    )

    df = df.with_columns(from_acct.alias("_src"), to_acct.alias("_dst"), ts_minutes.alias("_ts"))

    edges = df.select(
        pl.col("_src").alias("src"),
        pl.col("_dst").alias("dst"),
        pl.lit(EdgeType.PAYS.value).alias("edge_type"),
        pl.col("_ts").alias("timestamp"),
        pl.col("Amount Paid").cast(pl.Float64).alias("amount"),
        pl.lit(True).alias("directed"),
        pl.struct(
            fmt=pl.col("Payment Format"),
            cur_paid=pl.col("Payment Currency"),
            cur_recv=pl.col("Receiving Currency"),
            amount_received=pl.col("Amount Received"),
            is_laundering=pl.col("Is Laundering"),
        )
        .struct.json_encode()
        .alias("raw_attrs"),
    )

    endpoints = pl.concat(
        [
            df.select(pl.col("_src").alias("node_id"), pl.col("_ts")),
            df.select(pl.col("_dst").alias("node_id"), pl.col("_ts")),
        ]
    )
    nodes = (
        endpoints.group_by("node_id")
        .agg(pl.col("_ts").min().alias("time_first_seen"))
        .select(
            pl.col("node_id"),
            pl.lit(NodeType.ACCOUNT.value).alias("node_type"),
            pl.lit(Domain.FINANCIAL.value).alias("domain"),
            pl.col("time_first_seen"),
            pl.lit(None, dtype=pl.List(pl.Float32)).alias("raw_features"),
            pl.lit(None, dtype=pl.Utf8).alias("raw_attrs"),
        )
        .sort("node_id")
    )

    laundering = df.filter(pl.col("Is Laundering") == 1)
    illicit_nodes = (
        pl.concat(
            [
                laundering.select(pl.col("_src").alias("node_id")),
                laundering.select(pl.col("_dst").alias("node_id")),
            ]
        )
        .unique()
        .with_columns(pl.lit(Label.ILLICIT.value).alias("label"))
    )
    labels = (
        nodes.select("node_id")
        .join(illicit_nodes, on="node_id", how="left")
        .select(
            pl.col("node_id"),
            pl.col("label").fill_null(Label.LICIT.value),
            pl.lit("amlworld_edge_rollup").alias("label_source"),
            pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
        )
    )

    store.write(dataset, "nodes", nodes)
    store.write(dataset, "edges", edges)
    store.write(dataset, "labels", labels)
    stats = {
        "dataset": dataset,
        "adapter_version": ADAPTER_VERSION,
        "time_unit": "epoch_minutes",
        "primary_window_end": _AMLWORLD_HI_SMALL_WINDOW_END,
        "n_nodes": nodes.height,
        "n_edges": edges.height,
        "n_laundering_edges": laundering.height,
        "label_counts": dict(labels.group_by("label").len().sort("label").iter_rows()),
        "note": "edge-level ground truth in edges.raw_attrs.is_laundering; "
        "node labels are the laundering-edge roll-up",
    }
    store.write_meta(dataset, stats)
    return stats
