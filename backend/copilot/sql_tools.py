"""SQL tools for the Copilot's function-calling loop — ported from
`reference/genai-chatbot/backend/app/tools/sql_tools.py` and retargeted at the
artifact-store views (§4.6 disposition: keep, retarget; SELECT-only enforced).

Deltas from the source: markdown rendering is hand-rolled (no tabulate dep);
the read-only guarantee comes from the in-memory view connection PLUS the
allowlist, and multi-statement payloads are rejected outright (the archive
leaned on a read-only file connection we don't have)."""

from __future__ import annotations

from typing import Any

import duckdb
import pandas as pd

from .store import get_connection

MAX_ROWS = 50
MAX_CELL_CHARS = 300

_ALLOWED_FIRST = {"select", "with", "show", "describe", "explain"}


def _fmt(value: Any) -> str:
    text = str(value)
    return text[:MAX_CELL_CHARS] + "…" if len(text) > MAX_CELL_CHARS else text


def df_to_markdown(df: pd.DataFrame, max_rows: int = MAX_ROWS) -> str:
    if df.empty:
        return "(no rows)"
    head = df.head(max_rows)
    lines = [
        "| " + " | ".join(map(str, head.columns)) + " |",
        "|" + "---|" * len(head.columns),
    ]
    for _, row in head.iterrows():
        lines.append("| " + " | ".join(_fmt(v) for v in row) + " |")
    if len(df) > max_rows:
        lines.append(f"\n_… {len(df) - max_rows} more row(s) truncated._")
    return "\n".join(lines)


def guard_query(query: str) -> str | None:
    """Return a refusal message for non-SELECT or multi-statement payloads."""
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return "Refused: empty query."
    if ";" in stripped:
        return "Refused: multi-statement queries are not allowed."
    first = stripped.split(None, 1)[0].lower()
    if first not in _ALLOWED_FIRST:
        return f"Refused: only SELECT/WITH queries are allowed (got '{first}')."
    return None


def list_tables() -> str:
    con = get_connection()
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='main' ORDER BY table_name"
    ).fetchall()
    out = ["| table | rows |", "|---|---|"]
    for (t,) in rows:
        row = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()
        out.append(f"| {t} | {row[0] if row else 0} |")
    return "\n".join(out)


def describe_table(table_name: str) -> str:
    con = get_connection()
    df = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position",
        [table_name],
    ).df()
    if df.empty:
        return f"No table named '{table_name}'. Use list_tables() first."
    return df_to_markdown(df, max_rows=100)


def run_sql(query: str) -> str:
    refusal = guard_query(query)
    if refusal:
        return refusal
    try:
        df = get_connection().execute(query.strip().rstrip(";")).df()
        return df_to_markdown(df)
    except duckdb.Error as e:
        return f"SQL error: {e}"


SQL_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": (
                "List the artifact-store tables with row counts. "
                "Use first if unsure what exists."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Columns and types of a table. Confirm column names before writing SQL.",
            "parameters": {
                "type": "object",
                "properties": {"table_name": {"type": "string"}},
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Execute one read-only SELECT/WITH query against the alert "
                "store; results as a Markdown table (50-row cap)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]

SQL_TOOL_DISPATCH = {
    "list_tables": lambda _args: list_tables(),
    "describe_table": lambda args: describe_table(args["table_name"]),
    "run_sql": lambda args: run_sql(args["query"]),
}
