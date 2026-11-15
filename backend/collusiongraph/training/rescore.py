"""Journal revision item D24: re-score stored GNN checkpoints under two normalisations.

The ``normalisation: per_graph`` switch in ``train_gnn`` reaches only the
inference graph. Validation is scored on the train graph with the frozen train
statistics, so a per-graph run trains exactly the weights of the frozen run.
This runner therefore loads the stored checkpoints of a finished frozen
campaign and scores the inference graph twice: once with the frozen train
statistics and once with the inference graph's own statistics. Both passes use
the same weights by construction, so their difference isolates the
normalisation.

Two guards check the rebuild before anything is reported. Each checkpoint must
reproduce its run's best validation AUC-PR on the train graph, and the frozen
pass must reproduce its run's stored test AUC-PR. A mismatch means the rebuilt
graph or model differs from the one that was trained, and the runner stops.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import torch
from sklearn.metrics import average_precision_score

from collusiongraph.eval import compare_score_files, load_config, run_eval
from collusiongraph.features import apply_zscore, fit_zscore, restrict_as_of
from collusiongraph.models.gnn import make_model
from collusiongraph.schema import GraphStore

from .graph_build import build_graph, confirmed_mask_for
from .labels import load_label_history, resolve_train_labels
from .trainer import _TIME, _feature_frame, _forward, train_graph_restrict

VARIANTS = ("frozen", "per_graph")
_UNSUPPORTED = ("label_noise", "exclude_features")


def _check_source(src: dict[str, Any]) -> None:
    if src.get("normalisation", "frozen") != "frozen":
        raise ValueError("the source campaign must use frozen normalisation")
    for key in _UNSUPPORTED:
        if src.get(key):
            raise ValueError(f"the source config sets {key!r}, which this rebuild does not support")
    if src.get("model", {}).get("fusion", "concat") == "gated":
        raise ValueError("gated fusion is not supported by this rebuild")


def _mean_sd(values: list[float]) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
    }


def run_normalisation_rescore(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    if not cfg.get("normalisation_rescore"):
        raise ValueError("run_normalisation_rescore expects normalisation_rescore: true")
    src = load_config(cfg["source_config"])
    _check_source(src)
    seeds = [int(s) for s in cfg["seeds"]]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be a non-empty list without duplicates")
    src_root = Path(src["output_dir"])
    out_root = Path(cfg["output_dir"])
    tol = float(cfg.get("tolerance", 1e-9))
    n_boot = int(cfg.get("n_boot", 2000))
    boot_seed = int(cfg.get("bootstrap_seed", 0))

    # rebuild the graphs exactly as train_gnn builds them for this config
    store = GraphStore(src.get("store_root", "data/interim"))
    dataset: str = src["dataset"]
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")
    meta = store.read_meta(dataset)
    split = src["split"]
    train_end: int = split["train_end"]
    loss_end: int = split["loss_end"]
    fence = split.get("fence_after")
    if fence is not None:
        nodes, edges = restrict_as_of(nodes, edges, fence)
    n_raw = meta.get("n_features", 0)
    feature_kind = src.get("features", "raw")
    t_nodes, t_edges = train_graph_restrict(nodes, edges, train_end)
    label_policy = src.get("train_label_policy", "static")
    history = load_label_history(store, dataset, label_policy)
    train_labels = resolve_train_labels(label_policy, labels, t_edges, train_end, history)
    train_raw, _ = _feature_frame(feature_kind, t_nodes, t_edges, train_end, n_raw)
    stats = fit_zscore(train_raw)
    bidirectional = bool(src.get("bidirectional", True))
    train_data = build_graph(
        t_nodes, t_edges, train_labels, apply_zscore(train_raw, stats), bidirectional=bidirectional
    )
    infer_raw, _ = _feature_frame(feature_kind, nodes, edges, None, n_raw)
    variant_stats = {"frozen": stats, "per_graph": fit_zscore(infer_raw)}
    infer_data = {
        name: build_graph(
            nodes, edges, labels, apply_zscore(infer_raw, s), bidirectional=bidirectional
        )
        for name, s in variant_stats.items()
    }

    prefix = f"{src['node_type']}:" if src.get("node_type") else ""
    placed = t_nodes.filter(pl.col(_TIME).is_not_null())
    val_ids = set(
        placed.filter((pl.col(_TIME) > loss_end) & (pl.col(_TIME) <= train_end))[
            "node_id"
        ].to_list()
    )
    val_mask = confirmed_mask_for(train_data, val_ids, prefix)
    val_y = train_data.y[val_mask].numpy()
    test_start = split.get("test_start", train_end + 1)
    test_ids = nodes.filter(
        pl.col(_TIME).is_not_null()
        & (pl.col(_TIME) >= test_start)
        & pl.col("node_id").str.starts_with(prefix)
    )["node_id"]

    model_cfg = dict(src.get("model", {}))
    model_name = model_cfg.pop("name", "graphsage")
    fusion: str = model_cfg.pop("fusion", "concat")

    per_seed: list[dict[str, Any]] = []
    for seed in seeds:
        src_dir = src_root / f"seed_{seed}"
        record = json.loads((src_dir / "run.json").read_text(encoding="utf-8"))
        if record.get("seed") != seed or record.get("dataset") != dataset:
            raise ValueError(f"{src_dir}/run.json does not belong to seed {seed} of {dataset}")
        model = make_model(
            model_name,
            in_dim=train_data.x.shape[1],
            num_relations=int(train_data.num_relations),
            fusion=fusion,
            **model_cfg,
        )
        model.load_state_dict(torch.load(src_dir / "model.pt", map_location="cpu"))
        model.eval()
        with torch.no_grad():
            val_scores = torch.sigmoid(_forward(model, train_data)[val_mask]).numpy()
        val_ap = float(average_precision_score(val_y, val_scores))
        val_diff = abs(val_ap - float(record["best_val_auc_pr"]))
        if val_diff > tol:
            raise RuntimeError(
                f"seed {seed}: the checkpoint gives validation AUC-PR {val_ap!r}, but its run "
                f"recorded {record['best_val_auc_pr']!r}; the rebuild differs from training"
            )

        paths: dict[str, Path] = {}
        node_level: dict[str, dict[str, Any]] = {}
        for name in VARIANTS:
            data = infer_data[name]
            with torch.no_grad():
                scores = torch.sigmoid(_forward(model, data)).numpy()
            frame = pl.DataFrame(
                {"node_id": pl.Series(data.node_ids, dtype=pl.Utf8), "score": scores}
            ).filter(pl.col("node_id").is_in(test_ids.implode()))
            vdir = out_root / f"seed_{seed}" / name
            vdir.mkdir(parents=True, exist_ok=True)
            paths[name] = vdir / "scores_test.parquet"
            frame.write_parquet(paths[name])
            metrics = run_eval(
                {
                    "dataset": dataset,
                    "store_root": str(store.root),
                    "budgets": src["budgets"],
                    "node_scores": str(paths[name]),
                    "per_time_step": src.get("per_time_step", False),
                    "output_dir": str(vdir),
                }
            )
            node_level[name] = metrics["node_level"]

        test_diff = abs(node_level["frozen"]["auc_pr"] - float(record["node_level"]["auc_pr"]))
        if test_diff > tol:
            raise RuntimeError(
                f"seed {seed}: the frozen pass gives test AUC-PR "
                f"{node_level['frozen']['auc_pr']!r}, but its run recorded "
                f"{record['node_level']['auc_pr']!r}; the rebuild differs from training"
            )
        paired = compare_score_files(
            store.root,
            dataset,
            paths["per_graph"],
            paths["frozen"],
            n_boot=n_boot,
            seed=boot_seed,
        )
        per_seed.append(
            {
                "seed": seed,
                "checkpoint": str(src_dir / "model.pt"),
                "val_auc_pr": val_ap,
                "val_abs_diff": val_diff,
                "test_abs_diff_frozen": test_diff,
                "auc_pr": {name: node_level[name]["auc_pr"] for name in VARIANTS},
                "node_level": node_level,
                "paired_per_graph_minus_frozen": paired,
            }
        )

    report = {
        "kind": "normalisation_rescore",
        "dataset": dataset,
        "source_config": str(cfg["source_config"]),
        "source_dir": str(src_root),
        "seeds": seeds,
        "tolerance": tol,
        "n_confirmed": per_seed[0]["node_level"]["frozen"]["n_confirmed"],
        "prevalence_baseline": per_seed[0]["node_level"]["frozen"]["prevalence_baseline"],
        "per_seed": per_seed,
        "aggregate": {
            **{name: _mean_sd([r["auc_pr"][name] for r in per_seed]) for name in VARIANTS},
            "delta_per_graph_minus_frozen": _mean_sd(
                [r["auc_pr"]["per_graph"] - r["auc_pr"]["frozen"] for r in per_seed]
            ),
            "max_p_value": max(r["paired_per_graph_minus_frozen"]["p_value"] for r in per_seed),
        },
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "normalisation_rescore.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    return report
