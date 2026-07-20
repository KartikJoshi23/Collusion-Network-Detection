"""Config-driven baseline runs (§7 step 10 → Milestone M1).

One YAML = one reproducible baseline sweep on one dataset: strict-inductive
temporal split → feature assembly under the §9.1b as-of discipline → B1–B4
scores on the test queue → the §4.5 harness per baseline → ``scoreboard.json``.

Split discipline: training-side features (rule thresholds, XGBoost inputs,
neighborhood aggregates) are computed on the graph as of ``train_end`` — the
train-induced subgraph. Test rows are featurized on the full inference graph
(the model may see the graph as it exists at test time; §4.3 D1). Only
confirmed nodes train; unknowns are scored but never evaluated (the harness
drops them).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from collusiongraph.eval import load_config, run_eval
from collusiongraph.features import (
    award_screens,
    financial_features,
    precomputed_screens,
    structural_features,
)
from collusiongraph.models.baselines import (
    Rule,
    RulesEngine,
    neighbor_mean_features,
    screens_composite_scores,
    xgb_scores,
)
from collusiongraph.schema import GraphStore, Label
from collusiongraph.splits import strict_temporal_split

from .labels import resolve_train_labels


def raw_feature_frame(nodes: pl.DataFrame, n_features: int) -> pl.DataFrame:
    """Unpack ``nodes.raw_features`` (list<f32>) into wide columns raw_0..raw_{n-1}."""
    return nodes.select(
        "node_id",
        *[pl.col("raw_features").list.get(i).alias(f"raw_{i}") for i in range(n_features)],
    )


def assemble_features(
    domain: str,
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    as_of: int | None,
    n_raw_features: int = 0,
) -> tuple[pl.DataFrame, dict[str, list[str]]]:
    """Per-node feature table + the column groups the baselines select from.

    ``tabular`` — per-node attributes only (B2's world): raw dataset features
    (financial) / award-tier screens (procurement).
    ``graph`` — structural template + GADBench neighborhood means (B3 adds these).
    ``precomputed`` — the datasets' OWN precomputed screens from edge raw_attrs
    (procurement only; ledger 2026-07-16 deferred item). Deliberately NOT part
    of ``tabular``: B2/B3 inputs stay byte-identical to the published M1 runs —
    B4 configs (and future ablations) opt in by naming ``pc_*`` columns.
    """
    structural = structural_features(nodes, edges, as_of=as_of)
    struct_cols = [c for c in structural.columns if c != "node_id"]

    precomputed = None
    if domain == "financial":
        tabular = raw_feature_frame(nodes, n_raw_features)
        tabular = tabular.join(
            financial_features(nodes, edges, as_of=as_of), on="node_id", how="left"
        )
        neighbor_base = raw_feature_frame(nodes, n_raw_features)
    elif domain == "procurement":
        tabular = nodes.select("node_id").join(
            award_screens(nodes, edges, as_of=as_of), on="node_id", how="left"
        )
        precomputed = precomputed_screens(nodes, edges, as_of=as_of)
        neighbor_base = structural
    else:
        raise ValueError(f"unknown domain {domain!r}")

    neighbors = neighbor_mean_features(nodes, edges, neighbor_base, as_of=as_of)
    features = (
        nodes.select("node_id")
        .join(tabular, on="node_id", how="left")
        .join(structural, on="node_id", how="left")
        .join(neighbors, on="node_id", how="left")
    )
    pc_cols: list[str] = []
    if precomputed is not None:
        features = features.join(precomputed, on="node_id", how="left")
        pc_cols = [c for c in precomputed.columns if c != "node_id"]
    tabular_cols = [c for c in tabular.columns if c != "node_id"]
    nbr_cols = [c for c in neighbors.columns if c != "node_id"]
    return features, {
        "tabular": tabular_cols,
        "graph": struct_cols + nbr_cols,
        "precomputed": pc_cols,
    }


def _binary_labels(labels: pl.DataFrame) -> pl.DataFrame:
    """Confirmed nodes only, illicit=1 / licit=0 (loss on labeled nodes only)."""
    return labels.filter(pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])).select(
        "node_id", (pl.col("label") == Label.ILLICIT.value).cast(pl.Int8).alias("y")
    )


def run_baselines(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    domain: str = cfg["domain"]
    seed: int = cfg.get("seed", 0)
    out_dir = Path(cfg.get("output_dir", f"eval_outputs/{dataset}/baselines"))

    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")
    meta = store.read_meta(dataset)

    split_cfg = cfg["split"]
    split = strict_temporal_split(
        nodes,
        edges,
        train_end=split_cfg["train_end"],
        test_start=split_cfg.get("test_start"),
        fence_after=split_cfg.get("fence_after"),
    )

    n_raw = meta.get("n_features", 0)
    train_view, groups = assemble_features(
        domain, nodes, edges, as_of=split_cfg["train_end"], n_raw_features=n_raw
    )
    test_view, _ = assemble_features(domain, nodes, edges, as_of=None, n_raw_features=n_raw)

    node_type = cfg.get("node_type")
    prefix = f"{node_type}:" if node_type else ""
    train_ids = split.train_nodes.filter(pl.col("node_id").str.starts_with(prefix))["node_id"]
    test_ids = split.test_nodes.filter(pl.col("node_id").str.starts_with(prefix))["node_id"]

    train_features = train_view.filter(pl.col("node_id").is_in(train_ids.implode()))
    test_features = test_view.filter(pl.col("node_id").is_in(test_ids.implode()))
    # training targets: what a supervisor could have known at train_end (F1) —
    # test evaluation (inside run_eval) keeps the stored full-knowledge labels
    train_labels = resolve_train_labels(
        cfg.get("train_label_policy", "static"), labels, edges, split_cfg["train_end"]
    )
    train_labeled = train_features.join(_binary_labels(train_labels), on="node_id", how="inner")
    if train_labeled["y"].n_unique() < 2:
        raise ValueError("training split lacks both classes — check the split boundaries")

    def matrix(frame: pl.DataFrame, cols: list[str]) -> Any:
        return frame.select(cols).cast(pl.Float64).to_numpy()

    scores_dir = out_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    scoreboard: dict[str, Any] = {
        "dataset": dataset,
        "domain": domain,
        "node_type": node_type,
        "seed": seed,
        "split": split.report,
        "n_train_labeled": train_labeled.height,
        "n_test_scored": test_features.height,
        "baselines": {},
    }

    for name in cfg["baselines"]:
        if name == "b1_rules":
            engine = RulesEngine([Rule(**r) for r in cfg["rules"]]).fit(train_features)
            scored = engine.score(test_features)
        elif name == "b2_xgb":
            cols = groups["tabular"]
            preds = xgb_scores(
                matrix(train_labeled, cols),
                train_labeled["y"].to_numpy(),
                matrix(test_features, cols),
                seed=seed,
                **cfg.get("xgb", {}),
            )
            scored = test_features.select("node_id").with_columns(pl.Series("score", preds))
        elif name == "b3_xgb_graph":
            cols = groups["tabular"] + groups["graph"]
            preds = xgb_scores(
                matrix(train_labeled, cols),
                train_labeled["y"].to_numpy(),
                matrix(test_features, cols),
                seed=seed,
                **cfg.get("xgb", {}),
            )
            scored = test_features.select("node_id").with_columns(pl.Series("score", preds))
        elif name == "b4_screens":
            screens_cfg = cfg["screens"]
            scored = screens_composite_scores(
                test_features,
                columns=screens_cfg["columns"],
                low_risk_columns=screens_cfg.get("low_risk_columns"),
            )
        else:
            raise ValueError(f"unknown baseline {name!r}")

        scores_path = scores_dir / f"{name}.parquet"
        scored.write_parquet(scores_path)
        metrics = run_eval(
            {
                "dataset": dataset,
                "store_root": str(store.root),
                "budgets": cfg["budgets"],
                "node_scores": str(scores_path),
                "output_dir": str(out_dir / name),
            }
        )
        scoreboard["baselines"][name] = metrics["node_level"]

    (out_dir / "scoreboard.json").write_text(
        json.dumps(scoreboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return scoreboard
