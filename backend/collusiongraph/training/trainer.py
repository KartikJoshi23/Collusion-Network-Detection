"""Config-driven GNN training (§7 steps 11–12): one YAML = one training run.

Leakage discipline (§4.3 D1, §9.1): the TRAINING graph is the subgraph induced
by nodes/edges at or before ``train_end`` (strict-inductive — message passing
never touches test-period adjacency); the loss pool is confirmed nodes at or
before ``loss_end``; validation (early stopping on AUC-PR) is the confirmed
tail of the train period (``loss_end < t ≤ train_end``) — temporal, never
random. Scoring runs on the full inference graph (the model may see the graph
as it exists at test time). Unknown nodes carry structure, never gradient.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import torch
from sklearn.metrics import average_precision_score

from collusiongraph.eval import load_config, run_eval
from collusiongraph.features import restrict_as_of, structural_features, zscore_per_graph
from collusiongraph.models.gnn import make_model
from collusiongraph.schema import GraphStore

from .baseline_run import raw_feature_frame
from .graph_build import build_graph, confirmed_mask_for
from .losses import make_loss

_TIME = "time_first_seen"


def _feature_frame(
    kind: str, nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None, n_raw: int
) -> pl.DataFrame:
    # Inputs are z-scored per graph in BOTH kinds: tree baselines are scale-
    # invariant but gradient training is not — Elliptic's raw feature columns
    # span wildly different scales and stall optimization unstandardized.
    # Train-graph stats normalize training; inference-graph stats normalize
    # scoring (the model may see the graph as it exists then — §4.3 D1).
    if kind == "raw":
        return zscore_per_graph(raw_feature_frame(nodes, n_raw))
    if kind == "structural":
        return zscore_per_graph(structural_features(nodes, edges, as_of=as_of))
    raise ValueError(f"unknown feature kind {kind!r} (expected raw/structural)")


def _forward(model: torch.nn.Module, data: Any) -> torch.Tensor:
    return model(
        x=data.x,
        edge_index=data.edge_index,
        edge_direction=data.edge_direction,
        edge_rel=data.edge_rel,
    )


def train_gnn(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    seed: int = cfg.get("seed", 0)
    torch.manual_seed(seed)
    np.random.seed(seed)

    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    out_dir = Path(cfg.get("output_dir", f"eval_outputs/{dataset}/gnn"))
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")
    meta = store.read_meta(dataset)

    split = cfg["split"]
    train_end: int = split["train_end"]
    loss_end: int = split["loss_end"]
    if not loss_end < train_end:
        raise ValueError("loss_end must precede train_end (temporal validation tail)")
    fence = split.get("fence_after")
    if fence is not None:
        nodes, edges = restrict_as_of(nodes, edges, fence)

    n_raw = meta.get("n_features", 0)
    feature_kind: str = cfg.get("features", "raw")

    t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
    train_data = build_graph(
        t_nodes, t_edges, labels, _feature_frame(feature_kind, t_nodes, t_edges, train_end, n_raw)
    )
    infer_data = build_graph(
        nodes, edges, labels, _feature_frame(feature_kind, nodes, edges, None, n_raw)
    )

    prefix = f"{cfg['node_type']}:" if cfg.get("node_type") else ""
    placed = t_nodes.filter(pl.col(_TIME).is_not_null())
    loss_ids = set(placed.filter(pl.col(_TIME) <= loss_end)["node_id"].to_list())
    val_ids = set(
        placed.filter((pl.col(_TIME) > loss_end) & (pl.col(_TIME) <= train_end))[
            "node_id"
        ].to_list()
    )
    loss_mask = confirmed_mask_for(train_data, loss_ids, prefix)
    val_mask = confirmed_mask_for(train_data, val_ids, prefix)
    for name, mask in (("loss", loss_mask), ("val", val_mask)):
        pool = train_data.y[mask]
        if pool.numel() == 0 or pool.min() == pool.max():
            raise ValueError(f"{name} pool lacks both classes — adjust loss_end/train_end")

    model_cfg = dict(cfg.get("model", {}))
    model_name = model_cfg.pop("name", "graphsage")
    model = make_model(
        model_name,
        in_dim=train_data.x.shape[1],
        num_relations=int(train_data.num_relations),
        **model_cfg,
    )
    loss_cfg = dict(cfg.get("loss", {}))
    loss_fn = make_loss(loss_cfg.pop("name", "focal"), **loss_cfg)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=cfg.get("lr", 0.01), weight_decay=cfg.get("weight_decay", 5e-4)
    )

    epochs: int = cfg.get("epochs", 200)
    patience: int = cfg.get("patience", 20)
    best_val, best_state, best_epoch = -1.0, None, -1
    val_y = train_data.y[val_mask].numpy()
    t0 = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        logits = _forward(model, train_data)
        loss = loss_fn(logits[loss_mask], train_data.y[loss_mask])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_scores = torch.sigmoid(_forward(model, train_data)[val_mask]).numpy()
        val_ap = float(average_precision_score(val_y, val_scores))
        if val_ap > best_val:
            best_val, best_epoch = val_ap, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= patience:
            break
    assert best_state is not None
    model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        infer_scores = torch.sigmoid(_forward(model, infer_data)).numpy()
    scores_all = pl.DataFrame(
        {"node_id": pl.Series(infer_data.node_ids, dtype=pl.Utf8), "score": infer_scores}
    )

    test_start = split.get("test_start", train_end + 1)
    test_ids = nodes.filter(
        pl.col(_TIME).is_not_null()
        & (pl.col(_TIME) >= test_start)
        & pl.col("node_id").str.starts_with(prefix)
    )["node_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    scores_path = out_dir / "scores_test.parquet"
    scores_all.filter(pl.col("node_id").is_in(test_ids.implode())).write_parquet(scores_path)
    # validation-pool scores ride along for downstream calibration (§7 step 13)
    val_path = out_dir / "scores_val.parquet"
    scores_all.filter(pl.col("node_id").is_in(pl.Series(sorted(val_ids)).implode())).write_parquet(
        val_path
    )

    metrics = run_eval(
        {
            "dataset": dataset,
            "store_root": str(store.root),
            "budgets": cfg["budgets"],
            "node_scores": str(scores_path),
            "output_dir": str(out_dir),
        }
    )
    run_record = {
        "dataset": dataset,
        "model": {"name": model_name, **model_cfg},
        "loss": cfg.get("loss", {}),
        "seed": seed,
        "epochs_run": epoch + 1,
        "best_epoch": best_epoch,
        "best_val_auc_pr": best_val,
        "train_seconds": round(time.perf_counter() - t0, 1),
        "node_level": metrics.get("node_level"),
    }
    torch.save(model.state_dict(), out_dir / "model.pt")
    (out_dir / "run.json").write_text(
        json.dumps(run_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return run_record
