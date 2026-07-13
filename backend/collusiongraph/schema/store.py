"""GraphStore — versioned Parquet tables + DuckDB catalog per IR dataset (§3.2).

One dataset = one directory (default root ``data/interim/<dataset>/``) holding
``nodes.parquet``, ``edges.parquet``, ``labels.parquet`` (+ optional
``communities.parquet``, ``alerts.parquet``) and a ``meta.json`` with
provenance (source dataset, adapter version, time unit, feature names, stats).

Every write validates and casts against the §4.2 pyarrow schemas — an adapter
cannot silently emit a malformed table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from .tables import TABLE_SCHEMAS


class SchemaError(ValueError):
    """A table does not conform to the CollusionGraph IR."""


def conform(table_name: str, df: pl.DataFrame) -> pa.Table:
    """Validate ``df`` against the IR schema for ``table_name`` and cast to it.

    Missing nullable columns are added as nulls; missing non-nullable columns,
    unknown extra columns, or uncastable types raise :class:`SchemaError`.
    """
    if table_name not in TABLE_SCHEMAS:
        raise SchemaError(f"unknown IR table {table_name!r}; expected one of {list(TABLE_SCHEMAS)}")
    schema = TABLE_SCHEMAS[table_name]

    extra = set(df.columns) - set(schema.names)
    if extra:
        raise SchemaError(f"{table_name}: unknown columns {sorted(extra)}")

    missing = [f.name for f in schema if f.name not in df.columns]
    hard_missing = [name for name in missing if not schema.field(name).nullable]
    if hard_missing:
        raise SchemaError(f"{table_name}: missing required columns {hard_missing}")

    arrow = df.to_arrow()
    columns: list[pa.Array | pa.ChunkedArray] = []
    for f in schema:
        if f.name in df.columns:
            try:
                columns.append(arrow.column(f.name).cast(f.type))
            except pa.ArrowInvalid as exc:
                raise SchemaError(f"{table_name}.{f.name}: cannot cast to {f.type}: {exc}") from exc
        else:
            columns.append(pa.nulls(len(df), type=f.type))
    result = pa.table(dict(zip(schema.names, columns, strict=True)), schema=schema)

    for f in schema:
        if not f.nullable and result.column(f.name).null_count > 0:
            raise SchemaError(f"{table_name}.{f.name}: nulls in non-nullable column")
    return result


class GraphStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def dataset_dir(self, dataset: str) -> Path:
        return self.root / dataset

    def write(self, dataset: str, table_name: str, df: pl.DataFrame) -> Path:
        arrow = conform(table_name, df)
        out = self.dataset_dir(dataset)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{table_name}.parquet"
        pq.write_table(arrow, path)
        return path

    def read(self, dataset: str, table_name: str) -> pl.DataFrame:
        path = self.dataset_dir(dataset) / f"{table_name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"{path} — run the adapter first (poe ingest)")
        return pl.read_parquet(path)

    def write_meta(self, dataset: str, meta: dict[str, Any]) -> Path:
        out = self.dataset_dir(dataset)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "meta.json"
        path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def read_meta(self, dataset: str) -> dict[str, Any]:
        return json.loads((self.dataset_dir(dataset) / "meta.json").read_text(encoding="utf-8"))

    def connect(self, dataset: str) -> duckdb.DuckDBPyConnection:
        """In-memory DuckDB with one view per existing IR table (zero-server SQL)."""
        con = duckdb.connect()
        for table_name in TABLE_SCHEMAS:
            path = self.dataset_dir(dataset) / f"{table_name}.parquet"
            if path.is_file():
                con.execute(
                    f"CREATE VIEW {table_name} AS "
                    f"SELECT * FROM read_parquet('{path.as_posix()}')"
                )
        return con
