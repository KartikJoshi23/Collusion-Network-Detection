"""Config-driven M3 runs (§7 steps 14–16): ensemble evaluation and
injection-recovery, both on the operational test window.

* ``run_ensemble`` — score the test window with the unsupervised members
  (DOMINANT/GAE on the z-scored raw-feature projection, structural floor),
  rank-fuse them with the supervised GNN's scores (§4.4 ensemble), and report
  every member AND the fusion through the §4.5 harness — members stay
  individually reportable for the ablations.
* ``run_injection_recovery`` — plant all five financial motif rows into the
  test window (§4.4 item 4), rescore the augmented graph with each arm, and
  report recall of injected members at budget (RQ2's controlled measurement).
  AMLworld ground-truth calibration is deferred to a machine with Kaggle
  credentials (ledger).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl
import torch

from collusiongraph.eval import load_config, run_eval
from collusiongraph.features import restrict_as_of, zscore_per_graph
from collusiongraph.injection import inject, recovery_at_budget
from collusiongraph.models import rank_fusion, structural_floor, unsupervised_scores
from collusiongraph.models.ensemble import calibrated_fusion
from collusiongraph.models.gnn import make_model
from collusiongraph.schema import GraphStore, Label

from .baseline_run import raw_feature_frame
from .graph_build import build_graph
from .trainer import _forward

_TIME = "time_first_seen"


def _test_window(
    store: GraphStore, dataset: str, test_start: int
) -> tuple[pl.DataFrame, pl.DataFrame]:
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    test_nodes = nodes.filter(pl.col(_TIME).is_not_null() & (pl.col(_TIME) >= test_start))
    kept = test_nodes["node_id"].implode()
    return test_nodes, edges.filter(pl.col("src").is_in(kept) & pl.col("dst").is_in(kept))


def _member_scores(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    n_raw: int,
    cfg: dict[str, Any],
) -> dict[str, pl.DataFrame]:
    """The in-house members: unsupervised detectors + the transparent floor."""
    pays = edges.filter(pl.col("edge_type") == "pays")  # homogeneous projection
    features = zscore_per_graph(raw_feature_frame(nodes, n_raw))
    unsup_cfg = cfg.get("unsupervised", {})
    members = {
        name: unsupervised_scores(
            nodes,
            pays,
            features,
            method=name,
            hid_dim=unsup_cfg.get("hid_dim", 32),
            epochs=unsup_cfg.get("epochs", 50),
            seed=cfg.get("seed", 0),
        )
        for name in ("dominant", "gae")
    }
    members["floor"] = structural_floor(nodes, edges)
    return members


def run_ensemble(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    out_dir = Path(cfg["output_dir"])
    split = cfg["split"]
    test_start: int = split["test_start"]
    n_raw = store.read_meta(dataset).get("n_features", 0)

    test_nodes, test_edges = _test_window(store, dataset, test_start)
    members = _member_scores(test_nodes, test_edges, n_raw, cfg)
    members["supervised"] = pl.read_parquet(
        Path(cfg["supervised_scores_dir"]) / "scores_test.parquet"
    )

    # Validation-pool member scores for calibration (§4.4): unsupervised
    # members refit on the TRAIN-window graph (never test), floor as-of
    # train_end, supervised from the trainer's saved validation scores.
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")
    t_nodes, t_edges = restrict_as_of(nodes, edges, split["train_end"])
    val_ids = t_nodes.filter(pl.col(_TIME).is_not_null() & (pl.col(_TIME) > split["loss_end"]))[
        "node_id"
    ]
    train_members = _member_scores(t_nodes, t_edges, n_raw, cfg)
    members_val = {
        name: frame.filter(pl.col("node_id").is_in(val_ids.implode()))
        for name, frame in train_members.items()
    }
    members_val["supervised"] = pl.read_parquet(
        Path(cfg["supervised_scores_dir"]) / "scores_val.parquet"
    )
    val_labels = labels.filter(
        pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])
    ).select("node_id", (pl.col("label") == Label.ILLICIT.value).cast(pl.Int8).alias("y"))

    fused_cal = calibrated_fusion(members, members_val, val_labels, weights=cfg.get("weights"))
    fused_rank = rank_fusion(members, weights=cfg.get("weights"))
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"dataset": dataset, "members": {}, "seed": cfg.get("seed", 0)}
    for name, frame in {
        **members,
        "ensemble_calibrated": fused_cal,
        "ensemble_rank": fused_rank,
    }.items():
        path = out_dir / f"scores_{name}.parquet"
        frame.write_parquet(path)
        metrics = run_eval(
            {
                "dataset": dataset,
                "store_root": str(store.root),
                "budgets": cfg["budgets"],
                "node_scores": str(path),
                "output_dir": str(out_dir / name),
            }
        )
        report["members"][name] = metrics["node_level"]

    (out_dir / "ensemble_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def run_injection_recovery(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    out_dir = Path(cfg["output_dir"])
    test_start: int = cfg["split"]["test_start"]
    window = (test_start, int(cfg["split"]["window_end"]))
    n_raw = store.read_meta(dataset).get("n_features", 0)

    test_nodes, test_edges = _test_window(store, dataset, test_start)
    result = inject(
        test_nodes,
        test_edges,
        domain=cfg["domain"],
        motifs=cfg["motifs"],
        window=window,
        seed=cfg.get("seed", 0),
        n_bridge_edges=cfg.get("n_bridge_edges", 2),
    )

    scorers = _member_scores(result.nodes, result.edges, n_raw, cfg)
    if "supervised_model" in cfg:
        scorers["supervised"] = _supervised_scores_on(
            result.nodes, result.edges, store.read(dataset, "labels"), n_raw, cfg
        )
    scorers["ensemble"] = rank_fusion(dict(scorers))

    budgets: list[int] = cfg["budgets"]
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "dataset": dataset,
        "seed": cfg.get("seed", 0),
        "n_injected_instances": result.ground_truth.height,
        "n_injected_members": result.ground_truth["member_node_ids"]
        .explode(empty_as_null=False)
        .n_unique(),
        "population": result.nodes.height,
        "recovery": {},
    }
    for name, frame in scorers.items():
        rec = recovery_at_budget(frame, result.ground_truth, budgets)
        report["recovery"][name] = rec.to_dicts()
    (out_dir / "injection_recovery_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def _supervised_scores_on(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    labels: pl.DataFrame,
    n_raw: int,
    cfg: dict[str, Any],
) -> pl.DataFrame:
    """Score an (augmented) graph with a trained checkpoint. Injected nodes
    carry no raw features (zeros after z-scoring) — the supervised arm sees
    them through structure only, reported as such."""
    model_cfg = dict(cfg["supervised_model"])
    checkpoint = model_cfg.pop("checkpoint")
    name = model_cfg.pop("name")
    fence = cfg["split"].get("fence_after")
    if fence is not None:
        nodes, edges = restrict_as_of(nodes, edges, fence)
    data = build_graph(nodes, edges, labels, zscore_per_graph(raw_feature_frame(nodes, n_raw)))
    model = make_model(
        name, in_dim=data.x.shape[1], num_relations=int(data.num_relations), **model_cfg
    )
    model.load_state_dict(torch.load(checkpoint, weights_only=True))
    model.eval()
    with torch.no_grad():
        scores = torch.sigmoid(_forward(model, data)).numpy()
    return pl.DataFrame(
        {"node_id": pl.Series(data.node_ids, dtype=pl.Utf8), "score": scores.astype("float64")}
    )
