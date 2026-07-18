"""Read-only DuckDB surface over the serving artifacts (§4.6: the SQL agent
points at the alert store with zero engine change).

The connection is in-memory with VIEWS over the serving index's parquet
files — nothing the agent runs can touch the artifacts on disk, and
``sql_tools.run_sql`` additionally enforces the SELECT-only allowlist."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import duckdb

from .config import get_settings


@lru_cache(maxsize=1)
def serving_index() -> dict[str, Any]:
    path = Path(get_settings().serving_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"serving index not found at {path} — run `poe demo-artifacts` first"
        )
    return json.loads(path.read_text(encoding="utf-8"))["datasets"]


def build_connection() -> duckdb.DuckDBPyConnection:
    """One in-memory connection with an `alerts` view spanning every served
    dataset (the parquet already carries dataset/domain columns)."""
    con = duckdb.connect(":memory:")
    parquets = [
        str(Path(entry["alerts"]).as_posix())
        for entry in serving_index().values()
        if entry.get("alerts") and Path(entry["alerts"]).is_file()
    ]
    if not parquets:
        raise FileNotFoundError("no alert queues in the serving index")
    files = ", ".join(f"'{p}'" for p in parquets)
    con.execute(f"CREATE VIEW alerts AS SELECT * FROM read_parquet([{files}])")
    return con


@lru_cache(maxsize=1)
def get_connection() -> duckdb.DuckDBPyConnection:
    return build_connection()
