"""NEW alert_tools (§4.6 disposition: add) — thin readers over the serving
index and explanation-bundle JSONs, so the loop can fetch a whole alert or
bundle without composing SQL."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .sql_tools import df_to_markdown
from .store import get_connection, serving_index, stress_test_index

# Friendly, plain names for the injected cartel shapes (mirrors the Stress Test
# tab so the Copilot and the UI speak the same language).
_SHAPE_NAME = {
    "coordinated_cluster": "bid-together ring",
    "common_control": "hidden common owner",
    "partition": "market carve-up",
    "rotation": "take-turns",
    "cover_bid": "cover bidding",
}


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


def _best_recall(payload: dict) -> tuple[list[int], dict[str, dict], dict[str, int]]:
    """Normalise either injection artifact shape → per-shape best recall.

    Returns (budgets, {motif: {budget: (recall, std, arm)}}, {motif: n_members})
    — "best" is the top detector at each budget, the same reading the report
    headlines."""
    budgets: set[int] = set()
    best: dict[str, dict[int, tuple[float, float, str]]] = {}
    members: dict[str, int] = {}

    def offer(motif: str, budget: int, recall: float, std: float, arm: str) -> None:
        budgets.add(budget)
        cur = best.setdefault(motif, {}).get(budget)
        if cur is None or recall > cur[0]:
            best[motif][budget] = (recall, std, arm)

    multi = payload.get("recovery_multiseed")
    single = payload.get("recovery")
    if isinstance(multi, dict):
        for arm, motifs in multi.items():
            for motif, entry in motifs.items():
                if "n_members" in entry:
                    members[motif] = int(entry["n_members"])
                for k, v in entry.items():
                    if k.startswith("recall@") and isinstance(v, dict) and "mean" in v:
                        offer(motif, int(k[7:]), float(v["mean"]), float(v.get("std", 0.0)), arm)
    elif isinstance(single, dict):
        for arm, rows in single.items():
            for row in rows:
                motif = str(row.get("motif_type"))
                if "n_members" in row:
                    members[motif] = int(row["n_members"])
                for k, v in row.items():
                    if k.startswith("recall@") and isinstance(v, int | float):
                        offer(motif, int(k[7:]), float(v), 0.0, arm)
    return sorted(budgets), best, members


def get_stress_test() -> str:
    """The injection-recovery ("stress test") result: fake cartels of known
    shapes planted into the real UNLABELED OCDS Georgia network, and how many
    each detector clawed back. This is how the system is evaluated where there
    is NO answer key — hide answers you DO know and count how many come back."""
    studies = stress_test_index()
    if not studies:
        return (
            "No stress-test (injection-recovery) study is served on this machine. "
            "Run: uv run collusiongraph train -c "
            "configs/experiment/injection_recovery_ocds_georgia_multiseed.yaml"
        )
    out: list[str] = []
    for study in studies.values():
        path = Path(study["recovery"])
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        budgets, best, members = _best_recall(payload)
        top = budgets[-1] if budgets else 0
        n_seeds = len(payload.get("seeds", [1]))
        n_firms = payload.get("n_injected_members") or sum(members.values()) or "?"
        out.append(f"### Stress test — {study['title']}")
        out.append(
            f"{study.get('note', '')}\n\n"
            f"Planted {payload.get('n_injected_instances', '?')} fake cartels "
            f"({n_firms} firms) into a population of "
            f"{payload.get('population', '?')}; {n_seeds} run(s). "
            f"Recall = fraction of a shape's planted firms found in the review budget "
            f"(top {top} = the headline; also measured at {', '.join(map(str, budgets))})."
        )
        rows = []
        for motif in sorted(best, key=lambda m: -best[m].get(top, (0,))[0]):
            recall, std, arm = best[motif][top]
            name = _SHAPE_NAME.get(motif, motif)
            verdict = (
                "caught" if recall >= 0.6 else "partly caught" if recall >= 0.25 else "escapes"
            )
            std_s = f" ± {std:.3f}" if std else ""
            rows.append(
                {
                    "shape": f"{name} ({motif})",
                    f"recall@{top}": f"{recall:.3f}{std_s}",
                    "best detector": arm,
                    "verdict": verdict,
                }
            )
        out.append(df_to_markdown(pd.DataFrame(rows)))
        out.append(
            "Headline: the detector reliably catches cartels whose firms physically "
            "bid together (the ring), and is blind to take-turns cartels that never "
            "appear side by side. On this data there is no answer key, so the tree "
            f"model cannot take part — only the unsupervised detectors can. Reproduce: "
            f"{study.get('reproduce', '')}"
        )
    return "\n\n".join(out) or "The stress-test artifact is declared but absent on this machine."


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
    {
        "type": "function",
        "function": {
            "name": "get_stress_test",
            "description": (
                "The injection-recovery / 'stress test' result: how many planted "
                "fake cartels of each shape (bid-together ring, hidden common owner, "
                "market carve-up, take-turns, cover bidding) the detector recovered "
                "in the real UNLABELED contract network. Use for ANY question about "
                "the stress test, the playground, injection, planting fake cartels, "
                "or evaluating with no answer key / no labels."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

ALERT_TOOL_DISPATCH = {
    "get_alert": lambda args: get_alert(args["alert_id"]),
    "list_alerts": lambda args: list_alerts(args["dataset"], k=args.get("k", 10)),
    "get_explanation": lambda args: get_explanation(args["alert_id"]),
    "get_metrics": lambda args: get_metrics(args["dataset"]),
    "get_stress_test": lambda args: get_stress_test(),
}
