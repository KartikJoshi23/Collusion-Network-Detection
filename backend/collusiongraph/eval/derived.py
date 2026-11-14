"""Derived numbers the paper quotes, computed from stored artifacts.

Revision rule: every number in the paper comes from a committed config, and
nothing is computed by hand. This module covers the few derived quantities:
a Wilson score interval for a proportion (the copilot's grounding rate),
differences and ratios of stored values (for example, a difference of
multi-seed means or a lift over prevalence), and AUC-PR over a window of time
steps pooled from stored score files (the pre/post-step-43 table, item B1).

An input is either a literal number or a reference ``{file, key}``. ``key``
is a dotted path into the JSON file; integer segments index lists.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import polars as pl

from collusiongraph.schema import GraphStore

from .metrics import auc_pr, confirmed_node_vectors
from .report import load_config


def window_auc_pr(spec: dict[str, Any]) -> dict[str, Any]:
    """AUC-PR over the confirmed nodes whose time step lies in ``[lo, hi]``,
    one value per seed's score file, with mean ± std (ddof=1) over seeds."""
    store = GraphStore(spec.get("store_root", "data/interim"))
    nodes = store.read(spec["dataset"], "nodes").select("node_id", "time_first_seen")
    labels = store.read(spec["dataset"], "labels")
    lo, hi = int(spec["steps"][0]), int(spec["steps"][1])
    in_window = nodes.filter(pl.col("time_first_seen").is_between(lo, hi))["node_id"]
    seeds = spec.get("seeds")
    templates = (
        [str(spec["scores"])]
        if seeds is None
        else [str(spec["scores"]).format(seed=s) for s in seeds]
    )
    values: list[float] = []
    prevalence = float("nan")
    n_confirmed = 0
    for path in templates:
        frame = pl.read_parquet(path).filter(pl.col("node_id").is_in(in_window.implode()))
        y, s = confirmed_node_vectors(frame, labels)
        point = auc_pr(y, s)
        values.append(point["auc_pr"])
        prevalence, n_confirmed = point["prevalence_baseline"], int(y.size)
    return {
        "op": "window_auc_pr",
        "steps": [lo, hi],
        "auc_pr_per_seed": values,
        "auc_pr_mean": float(np.mean(values)),
        "auc_pr_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "prevalence": prevalence,
        "n_confirmed": n_confirmed,
    }


def lookup(ref: Any) -> float:
    """Resolve a literal or a ``{file, key}`` reference to a float."""
    if isinstance(ref, (int, float)):
        return float(ref)
    node: Any = json.loads(Path(ref["file"]).read_text(encoding="utf-8"))
    for part in str(ref["key"]).split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return float(node)


def wilson_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError(f"need 0 <= successes <= n and n > 0 (got {successes}/{n})")
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return centre - half, centre + half


def compute_item(spec: dict[str, Any]) -> dict[str, Any]:
    op = spec["op"]
    if op == "wilson":
        n = round(lookup(spec["n"]))
        if "successes" in spec:
            k = round(lookup(spec["successes"]))
        else:
            k = round(lookup(spec["rate"]) * n)
        alpha = float(spec.get("alpha", 0.05))
        lo, hi = wilson_interval(k, n, alpha)
        return {"op": op, "successes": k, "n": n, "proportion": k / n, "ci_low": lo, "ci_high": hi}
    if op in ("difference", "ratio"):
        a, b = lookup(spec["a"]), lookup(spec["b"])
        value = a - b if op == "difference" else a / b
        return {"op": op, "a": a, "b": b, "value": value}
    if op == "window_auc_pr":
        return window_auc_pr(spec)
    raise ValueError(f"unknown op {op!r} (expected wilson, difference, ratio or window_auc_pr)")


def run_derived_numbers(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    if not cfg.get("derived_numbers"):
        raise ValueError("run_derived_numbers expects a config with derived_numbers: true")
    report = {
        "kind": "derived_numbers",
        "items": {name: compute_item(spec) for name, spec in cfg["items"].items()},
    }
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "derived_numbers.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
