"""
Tools the SQL Agent calls via OpenAI function-calling.

Each tool returns a plain string (serialisable, safe to put in a chat message).
Errors are caught and returned as strings too so the agent can observe and
self-correct rather than crashing the graph.

Security posture:
  * `run_sql` executes arbitrary SQL on a READ-ONLY DuckDB connection, so no
    INSERT/UPDATE/DELETE/DROP can land. DuckDB enforces this at the driver level.
  * Result rows are truncated to `MAX_ROWS` to avoid flooding the LLM context.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from app.config import get_settings
from app.data.duckdb_loader import get_connection

logger = logging.getLogger(__name__)

MAX_ROWS = 50
MAX_CELL_CHARS = 300


def _truncate_cell(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
        return value[:MAX_CELL_CHARS] + "…"
    return value


def _df_to_markdown(df: pd.DataFrame, max_rows: int = MAX_ROWS) -> str:
    if df.empty:
        return "(no rows)"
    truncated = df.head(max_rows).map(_truncate_cell)
    md = truncated.to_markdown(index=False)
    if len(df) > max_rows:
        md += f"\n\n_… {len(df) - max_rows} more row(s) truncated._"
    return md


def list_tables() -> str:
    """List every table in the TechNova DuckDB database with its row count."""
    con = get_connection(read_only=True)
    try:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()
        out: list[str] = ["| table | rows |", "|---|---|"]
        for (t,) in rows:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            out.append(f"| {t} | {n} |")
        return "\n".join(out)
    finally:
        con.close()


def describe_table(table_name: str) -> str:
    """Return the columns and (where documented) FK notes for a table.

    Pulls structure from DuckDB's information_schema AND enriches with the
    curated schema.yaml notes so the agent sees natural-language descriptions
    alongside types.
    """
    settings = get_settings()
    con = get_connection(read_only=True)
    try:
        cols_df = con.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema='main' AND table_name=?
            ORDER BY ordinal_position
            """,
            [table_name],
        ).df()
    finally:
        con.close()

    if cols_df.empty:
        return f"No table named '{table_name}' exists. Use list_tables() to see the available tables."

    schema_path = Path(settings.schema_yaml_path)
    notes_by_col: dict[str, str] = {}
    fks: list[dict] = []
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = yaml.safe_load(f)
        tbl = schema.get("tables", {}).get(table_name, {})
        for col_name, col_def in (tbl.get("columns") or {}).items():
            note_parts: list[str] = []
            if isinstance(col_def, dict):
                if col_def.get("type"):
                    note_parts.append(str(col_def["type"]))
                if col_def.get("notes"):
                    note_parts.append(str(col_def["notes"]))
            if note_parts:
                notes_by_col[col_name] = " — ".join(note_parts)
        fks = [
            fk for fk in (schema.get("foreign_keys") or [])
            if fk.get("from_table") == table_name
        ]

    lines: list[str] = [f"### Table `{table_name}`"]
    desc = schema.get("tables", {}).get(table_name, {}).get("description") if schema_path.exists() else None
    if desc:
        lines.append(desc)
    lines.append("")
    lines.append("| column | type | nullable | notes |")
    lines.append("|---|---|---|---|")
    for _, row in cols_df.iterrows():
        note = notes_by_col.get(row["column_name"], "")
        lines.append(
            f"| {row['column_name']} | {row['data_type']} | {row['is_nullable']} | {note} |"
        )

    if fks:
        lines.append("")
        lines.append("**Foreign keys (pick the one whose `purpose` matches your question):**")
        for fk in fks:
            nullable = " (nullable)" if fk.get("nullable") else ""
            purpose = fk.get("purpose")
            note = fk.get("note")
            parts = [f"`{fk['from_column']}` → `{fk['to_table']}.{fk['to_column']}`{nullable}"]
            if purpose:
                parts.append(f"_purpose:_ {purpose}")
            if note:
                parts.append(f"_note:_ {note}")
            lines.append("- " + " — ".join(parts))

    return "\n".join(lines)


def sample_rows(table_name: str, where: str | None = None, n: int = 5) -> str:
    """Return the first n rows of a table, optionally filtered by a SQL WHERE clause.

    Example: sample_rows("customers", where="tier = 'Tier 1'", n=3)
    """
    con = get_connection(read_only=True)
    try:
        sql = f'SELECT * FROM "{table_name}"'
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {int(n)}"
        df = con.execute(sql).df()
        return _df_to_markdown(df, max_rows=n)
    except duckdb.Error as e:
        return f"SQL error: {e}"
    finally:
        con.close()


def count_rows(table_name: str, where: str | None = None) -> str:
    """Return the number of rows in a table, optionally filtered by a WHERE clause."""
    con = get_connection(read_only=True)
    try:
        sql = f'SELECT COUNT(*) FROM "{table_name}"'
        if where:
            sql += f" WHERE {where}"
        (count,) = con.execute(sql).fetchone()
        return f"{count}"
    except duckdb.Error as e:
        return f"SQL error: {e}"
    finally:
        con.close()


def run_sql(query: str) -> str:
    """Execute an arbitrary SELECT query against the TechNova DB and return results as a Markdown table.

    Read-only: INSERT/UPDATE/DELETE/DROP will fail. Results truncated to MAX_ROWS.
    """
    # Reject non-SELECT statements defensively even though the connection is read-only.
    stripped = query.strip().rstrip(";").strip()
    first_token = stripped.split(None, 1)[0].lower() if stripped else ""
    if first_token not in {"select", "with", "show", "describe", "explain", "pragma"}:
        return (
            f"Refused: only SELECT/WITH queries allowed. Got first token: '{first_token}'."
        )

    con = get_connection(read_only=True)
    try:
        df = con.execute(stripped).df()
        return _df_to_markdown(df)
    except duckdb.Error as e:
        return f"SQL error: {e}"
    finally:
        con.close()


# OpenAI function-calling schemas — consumed by the SQL Agent.
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List every table in the TechNova database with its row count. Use this first if you're unsure what data exists.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Get the columns, types, nullability and foreign keys of a table. Call this to confirm column names before writing SQL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "e.g. 'customers' or 'financial_transactions'"},
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sample_rows",
            "description": "Return up to n rows from a table, optionally filtered by a SQL WHERE clause. Use to inspect actual values (categorical enums, date formats) before filtering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "where": {"type": "string", "description": "Optional SQL WHERE clause (without 'WHERE'). Example: \"tier = 'Tier 1' AND region = 'APAC'\""},
                    "n": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_rows",
            "description": "Return the row count of a table, optionally filtered by a WHERE clause. Cheaper than running a full query when you only need a count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "where": {"type": "string"},
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Execute a SELECT/WITH query against DuckDB and return results as a Markdown table. Read-only. Results truncated to 50 rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A DuckDB-compatible SELECT or WITH ... SELECT query."},
                },
                "required": ["query"],
            },
        },
    },
]


TOOL_DISPATCH = {
    "list_tables": lambda _args: list_tables(),
    "describe_table": lambda args: describe_table(args["table_name"]),
    "sample_rows": lambda args: sample_rows(
        args["table_name"], where=args.get("where"), n=args.get("n", 5)
    ),
    "count_rows": lambda args: count_rows(args["table_name"], where=args.get("where")),
    "run_sql": lambda args: run_sql(args["query"]),
}
