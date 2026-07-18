"""NEW alert_tools (§4.6 disposition: add) — thin readers over the serving
index and explanation-bundle JSONs, so the loop can fetch a whole alert or
bundle without composing SQL."""

from __future__ import annotations

import json
from pathlib import Path

from .sql_tools import df_to_markdown
from .store import get_connection, serving_index


def get_alert(alert_id: str) -> str:
    df = get_connection().execute("SELECT * FROM alerts WHERE alert_id = ?", [alert_id]).df()
    if df.empty:
        return f"No alert with id '{alert_id}'."
    return df_to_markdown(df.T.reset_index().rename(columns={"index": "field", 0: "value"}), 40)


def list_alerts(dataset: str, k: int = 10) -> str:
    df = (
        get_connection()
        .execute(
            "SELECT rank, alert_id, risk_score, n_members FROM alerts "
            "WHERE dataset = ? ORDER BY rank LIMIT ?",
            [dataset, max(1, min(int(k), 50))],
        )
        .df()
    )
    if df.empty:
        known = ", ".join(sorted(serving_index()))
        return f"No alerts for dataset '{dataset}'. Served datasets: {known}."
    return df_to_markdown(df)


def get_explanation(alert_id: str) -> str:
    dataset = alert_id.split(":", 1)[0]
    entry = serving_index().get(dataset)
    if not entry or not entry.get("explanations"):
        return f"No explanation bundles are served for dataset '{dataset}'."
    path = Path(entry["explanations"]) / f"{alert_id.replace(':', '_')}.json"
    if not path.is_file():
        return f"No bundle for alert '{alert_id}' (bundles cover the top-k alerts only)."
    bundle = json.loads(path.read_text(encoding="utf-8"))
    bundle.pop("minimal_subgraph", None)  # too large for chat context; cite it instead
    return json.dumps(bundle, indent=2, ensure_ascii=False)


def get_metrics(dataset: str) -> str:
    entry = serving_index().get(dataset)
    if not entry:
        return f"Unknown dataset '{dataset}'. Served: {', '.join(sorted(serving_index()))}."
    out = []
    for m in entry.get("metrics", []):
        p = Path(m)
        if p.is_file():
            payload = json.loads(p.read_text(encoding="utf-8"))
            payload.pop("config", None)
            payload.get("node_level", {}).pop("per_time_step", None)
            out.append(f"### {p.as_posix()}\n{json.dumps(payload, indent=2)}")
    return "\n\n".join(out) or f"No metrics files served for '{dataset}'."


ALERT_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_alert",
            "description": "Fetch one alert's full record by alert_id.",
            "parameters": {
                "type": "object",
                "properties": {"alert_id": {"type": "string"}},
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_alerts",
            "description": "Top-k ranked alerts for a dataset (rank, id, risk, members).",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "k": {"type": "integer", "default": 10},
                },
                "required": ["dataset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_explanation",
            "description": (
                "Fetch an alert's explanation bundle "
                "(motif, red flags, fidelity, evidence sources)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"alert_id": {"type": "string"}},
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_metrics",
            "description": "Published evaluation metrics for a dataset's served runs.",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string"}},
                "required": ["dataset"],
            },
        },
    },
]

ALERT_TOOL_DISPATCH = {
    "get_alert": lambda args: get_alert(args["alert_id"]),
    "list_alerts": lambda args: list_alerts(args["dataset"], k=args.get("k", 10)),
    "get_explanation": lambda args: get_explanation(args["alert_id"]),
    "get_metrics": lambda args: get_metrics(args["dataset"]),
}
