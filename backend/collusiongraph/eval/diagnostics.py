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
  as of ``train_end``, the test side on the full graph;
* label association (optional): per time window, prevalence and each
  feature's ROC-AUC against the label, so a sign change between the training
  windows and the test window shows up directly.

It never trains anything. Its output is ``diagnostics.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scipy.stats import ks_2samp

from collusiongraph.features import financial_features, restrict_as_of, structural_features
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


def _features_of(kind: str, nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    if kind == "structural":
        return structural_features(nodes, edges, as_of=None)
    if kind == "degree":
        return _degree_frame(nodes, edges)
    if kind == "financial":  # the money-flow pack the financial trees use
        return financial_features(nodes, edges, as_of=None)
    raise ValueError(
        f"unknown feature kind {kind!r} (expected 'structural', 'degree' or 'financial')"
    )


def label_association(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    labels: pl.DataFrame,
    prefix: str,
    kind: str,
    train_end: int,
    windows: dict[str, dict[str, Any]],
    label_policy: str = "static",
    min_effect: float = 0.02,
) -> dict[str, Any]:
    """Per time window: confirmed nodes, prevalence, and the ROC-AUC of each
    feature against the label. 0.5 means no association. Below 0.5 means the
    feature ranks licit nodes above illicit ones. Training-side windows are
    featurised as of ``train_end`` and labelled with the training label
    policy; test-side windows use the full graph and the stored labels, as the
    models saw them. A feature whose ROC-AUC sits on opposite sides of 0.5 in a
    training window and in the test window ranks test nodes backwards for a
    model that learned the training-window direction. Only departures of at
    least ``min_effect`` from 0.5 on both sides count as opposite signs."""
    from sklearn.metrics import roc_auc_score

    from collusiongraph.training.labels import resolve_train_labels

    t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
    sides = {
        "train": (
            _features_of(kind, t_nodes, t_edges),
            resolve_train_labels(label_policy, labels, t_edges, train_end),
        ),
        "test": (_features_of(kind, nodes, edges), labels),
    }
    typed = nodes.filter(pl.col("node_id").str.starts_with(prefix)) if prefix else nodes
    confirmed = [Label.ILLICIT.value, Label.LICIT.value]
    out: dict[str, Any] = {
        "kind": kind,
        "label_policy": label_policy,
        "min_effect": min_effect,
        "windows": {},
    }
    for name, win in windows.items():
        side = win["side"]
        if side not in sides:
            raise ValueError(f"window {name!r}: side must be 'train' or 'test', got {side!r}")
        if side == "train" and win.get("until") is not None and int(win["until"]) > train_end:
            raise ValueError(f"window {name!r} ends after train_end but claims the train side")
        sel = typed
        if win.get("after") is not None:
            sel = sel.filter(pl.col(_TIME) > int(win["after"]))
        if win.get("until") is not None:
            sel = sel.filter(pl.col(_TIME) <= int(win["until"]))
        feats, labs = sides[side]
        rows = (
            feats.join(labs.select("node_id", "label"), on="node_id")
            .filter(pl.col("node_id").is_in(sel["node_id"].implode()))
            .filter(pl.col("label").is_in(confirmed))
        )
        y = (rows["label"] == Label.ILLICIT.value).to_numpy().astype(int)
        roc: dict[str, float | None] = {}
        for col in [c for c, dt in feats.schema.items() if c != "node_id" and dt.is_numeric()]:
            x = rows[col].cast(pl.Float64).fill_null(0.0).to_numpy()
            ok = 0 < y.sum() < y.size and float(np.std(x)) > 0
            roc[col] = float(roc_auc_score(y, x)) if ok else None
        out["windows"][name] = {
            "side": side,
            "n_confirmed": int(y.size),
            "prevalence": float(y.mean()) if y.size else None,
            "roc_auc": roc,
        }
    test_windows = [n for n, w in windows.items() if w["side"] == "test"]
    if test_windows:
        ref = out["windows"][test_windows[0]]["roc_auc"]
        out["opposite_sign_to_test"] = {
            name: sorted(
                c
                for c, v in w["roc_auc"].items()
                if v is not None
                and ref.get(c) is not None
                and (v - 0.5) * (ref[c] - 0.5) < 0
                and min(abs(v - 0.5), abs(ref[c] - 0.5)) >= min_effect
            )
            for name, w in out["windows"].items()
            if w["side"] == "train"
        }
    return out


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
            # the models' own fence, applied after the split facts are counted
            fence = shift_cfg.get("fence_after")
            if fence is not None:
                nodes, edges = restrict_as_of(nodes, edges, int(fence))
                case["split_facts"]["fence_after"] = int(fence)
            case["distribution_shift"] = distribution_shift(
                nodes, edges, prefix, train_end, test_start, shift_cfg.get("features", "degree")
            )
            assoc_cfg = shift_cfg.get("association")
            if assoc_cfg:
                case["label_association"] = label_association(
                    nodes,
                    edges,
                    labels,
                    prefix,
                    assoc_cfg.get("features", shift_cfg.get("features", "degree")),
                    train_end,
                    assoc_cfg["windows"],
                    assoc_cfg.get("label_policy", "static"),
                    float(assoc_cfg.get("min_effect", 0.02)),
                )
        report["cases"][case_name] = case

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diagnostics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
