"""Below-chance diagnostics (revision brief item B4).

A scorer whose AUC-PR sits below its prevalence baseline has ranked the
positives worse than random. The brief names three possible causes: a label
inversion, a score inversion, or a train–test shift. For each case this
module reads stored score files and the IR store, and reports:

* score checks: AUC-PR of the score and of its inversion (``-score``, which
  ranks exactly like ``1 - score``), against prevalence, plus the size of the
  largest block of tied scores;
* label encoding: how the stored labels map to y (y = 1 only for "illicit"),
  with counts over the scored nodes;
* split facts: node and edge counts on each side of the cut, and how many fall
  after a dataset's primary window when it records one;
* distribution shift: per-feature Kolmogorov–Smirnov statistics and
  standardised mean differences between training-period and test-period
  nodes. Each side is featurised the way the models saw it: the training side
  as of ``train_end``, the test side on the full graph.

It never trains anything. Its output is ``diagnostics.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scipy.stats import ks_2samp

from collusiongraph.features import restrict_as_of, structural_features
from collusiongraph.schema import GraphStore, Label

from .metrics import auc_pr, confirmed_node_vectors
from .report import load_config

_TIME = "time_first_seen"


def score_checks(y: np.ndarray, s: np.ndarray) -> dict[str, Any]:
    """AUC-PR of a scorer and of its inversion, against prevalence."""
    point = auc_pr(y, s)
    inverted = auc_pr(y, -s)
    _, counts = np.unique(s, return_counts=True)
    prevalence = point["prevalence_baseline"]
    return {
        "n_confirmed": int(y.size),
        "prevalence": prevalence,
        "auc_pr": point["auc_pr"],
        "auc_pr_inverted": inverted["auc_pr"],
        "below_prevalence": point["auc_pr"] < prevalence,
        "inverted_above_prevalence": inverted["auc_pr"] > prevalence,
        "n_unique_scores": int(counts.size),
        "largest_tie_share": float(counts.max() / s.size),
    }


def label_encoding(labels: pl.DataFrame, node_ids: list[str]) -> dict[str, Any]:
    """Label counts over the scored nodes and the y mapping the harness uses."""
    scored = labels.filter(pl.col("node_id").is_in(node_ids))
    counts = dict(scored.group_by("label").len().sort("label").iter_rows())
    return {
        "y_equals_1_for": Label.ILLICIT.value,
        "y_equals_0_for": Label.LICIT.value,
        "excluded_from_metrics": [Label.UNKNOWN.value],
        "label_counts_over_scored_nodes": {str(k): int(v) for k, v in counts.items()},
    }


def _degree_frame(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    out_deg = edges.group_by(pl.col("src").alias("node_id")).len(name="degree_out")
    in_deg = edges.group_by(pl.col("dst").alias("node_id")).len(name="degree_in")
    return (
        nodes.select("node_id")
        .join(out_deg, on="node_id", how="left")
        .join(in_deg, on="node_id", how="left")
        .with_columns(pl.col("degree_out").fill_null(0), pl.col("degree_in").fill_null(0))
        .with_columns((pl.col("degree_out") + pl.col("degree_in")).alias("degree"))
    )


def split_facts(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    prefix: str,
    train_end: int,
    test_start: int,
    window_end: int | None,
) -> dict[str, Any]:
    typed = nodes.filter(pl.col("node_id").str.starts_with(prefix)) if prefix else nodes
    t = typed[_TIME]
    facts: dict[str, Any] = {
        "node_time_min": int(t.min()),  # type: ignore[arg-type]
        "node_time_max": int(t.max()),  # type: ignore[arg-type]
        "train_end": train_end,
        "test_start": test_start,
        "n_nodes_train": int((t <= train_end).sum()),
        "n_nodes_test": int((t >= test_start).sum()),
        "n_edges_up_to_train_end": int((edges["timestamp"] <= train_end).sum()),
        "n_edges_after_train_end": int((edges["timestamp"] > train_end).sum()),
    }
    if window_end is not None:
        facts["primary_window_end"] = window_end
        facts["n_nodes_after_window"] = int((t > window_end).sum())
        facts["n_edges_after_window"] = int((edges["timestamp"] > window_end).sum())
    return facts


def distribution_shift(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    prefix: str,
    train_end: int,
    test_start: int,
    kind: str,
    top_k: int = 8,
) -> dict[str, Any]:
    """Train-period vs test-period feature distributions, featurised as the
    baselines and GNNs saw them (train side as of train_end, test side on the
    full graph)."""
    if kind == "structural":
        train_feats = structural_features(nodes, edges, as_of=train_end)
        test_feats = structural_features(nodes, edges, as_of=None)
    elif kind == "degree":
        t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
        train_feats = _degree_frame(t_nodes, t_edges)
        test_feats = _degree_frame(nodes, edges)
    else:
        raise ValueError(f"unknown feature kind {kind!r} (expected 'structural' or 'degree')")

    typed = nodes.filter(pl.col("node_id").str.starts_with(prefix)) if prefix else nodes
    train_ids = typed.filter(pl.col(_TIME) <= train_end)["node_id"].implode()
    test_ids = typed.filter(pl.col(_TIME) >= test_start)["node_id"].implode()
    train_rows = train_feats.filter(pl.col("node_id").is_in(train_ids))
    test_rows = test_feats.filter(pl.col("node_id").is_in(test_ids))

    columns = [c for c, dt in train_rows.schema.items() if c != "node_id" and dt.is_numeric()]
    per_feature: list[dict[str, Any]] = []
    for col in columns:
        a = train_rows[col].drop_nulls().cast(pl.Float64).to_numpy()
        b = test_rows[col].drop_nulls().cast(pl.Float64).to_numpy()
        if a.size < 2 or b.size < 2:
            continue
        pooled = float(np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0))
        per_feature.append(
            {
                "feature": col,
                "ks_statistic": float(ks_2samp(a, b).statistic),
                "smd": float((b.mean() - a.mean()) / pooled) if pooled > 0 else 0.0,
                "median_train": float(np.median(a)),
                "median_test": float(np.median(b)),
            }
        )
    per_feature.sort(key=lambda r: r["ks_statistic"], reverse=True)
    return {
        "kind": kind,
        "n_train_nodes": train_rows.height,
        "n_test_nodes": test_rows.height,
        "top_shifted": per_feature[:top_k],
        "median_ks": (
            float(np.median([r["ks_statistic"] for r in per_feature])) if per_feature else None
        ),
    }


def _score_paths(spec: dict[str, Any]) -> dict[str, Path]:
    """name -> score file, expanding ``{seed}`` templates over ``seeds``."""
    scores = spec["scores"]
    named = scores if isinstance(scores, dict) else {"scores": scores}
    seeds = spec.get("seeds")
    paths: dict[str, Path] = {}
    for name, template in named.items():
        if seeds is None:
            paths[name] = Path(str(template))
        else:
            for s in seeds:
                paths[f"{name}_seed{s}"] = Path(str(template).format(seed=s))
    return paths


def run_below_chance_diagnostics(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    if not cfg.get("diagnostics"):
        raise ValueError("run_below_chance_diagnostics expects a config with diagnostics: true")
    out_dir = Path(cfg["output_dir"])
    report: dict[str, Any] = {"kind": "below_chance_diagnostics", "cases": {}}
    for case_name, spec in cfg["cases"].items():
        store = GraphStore(spec.get("store_root", cfg.get("store_root", "data/interim")))
        dataset: str = spec["dataset"]
        prefix = f"{spec['node_type']}:" if spec.get("node_type") else ""
        labels = store.read(dataset, "labels")

        checks: dict[str, Any] = {}
        scored_ids: set[str] = set()
        for name, path in _score_paths(spec).items():
            frame = pl.read_parquet(path)
            if prefix:
                frame = frame.filter(pl.col("node_id").str.starts_with(prefix))
            scored_ids |= set(frame["node_id"].to_list())
            y, s = confirmed_node_vectors(frame, labels)
            checks[name] = {"path": str(path), **score_checks(y, s.astype(np.float64))}
        case: dict[str, Any] = {
            "dataset": dataset,
            "score_checks": checks,
            "label_encoding": label_encoding(labels, sorted(scored_ids)),
        }

        shift_cfg = spec.get("shift")
        if shift_cfg:
            nodes = store.read(dataset, "nodes")
            edges = store.read(dataset, "edges")
            window_end = store.read_meta(dataset).get("primary_window_end")
            train_end, test_start = int(shift_cfg["train_end"]), int(shift_cfg["test_start"])
            case["split_facts"] = split_facts(
                nodes, edges, prefix, train_end, test_start, window_end
            )
            case["distribution_shift"] = distribution_shift(
                nodes, edges, prefix, train_end, test_start, shift_cfg.get("features", "degree")
            )
        report["cases"][case_name] = case

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diagnostics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
