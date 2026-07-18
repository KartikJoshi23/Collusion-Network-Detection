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
from collusiongraph.features import (
    apply_zscore,
    financial_features,
    fit_zscore,
    line_graph_features,
    restrict_as_of,
    structural_features,
)
from collusiongraph.models.gnn import make_model
from collusiongraph.schema import GraphStore

from .baseline_run import raw_feature_frame
from .graph_build import build_graph, confirmed_mask_for
from .labels import resolve_train_labels
from .losses import make_loss

_TIME = "time_first_seen"


def _one_family(
    kind: str, nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None, n_raw: int
) -> pl.DataFrame:
    if kind == "raw":
        return raw_feature_frame(nodes, n_raw)
    if kind == "structural":
        return structural_features(nodes, edges, as_of=as_of)
    if kind == "financial":
        return financial_features(nodes, edges, as_of=as_of)
    if kind == "line":  # §7 step 26a — line-graph flow channel (arm B-LG)
        return line_graph_features(nodes, edges, as_of=as_of)
    raise ValueError(f"unknown feature kind {kind!r} (expected raw/structural/financial/line)")


def _feature_frame(
    kinds: str | list[str],
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    as_of: int | None,
    n_raw: int,
) -> tuple[pl.DataFrame, list[int]]:
    """Per-node features for one or several families, joined on node_id in
    config order, plus the per-family column widths (the context-fusion spans,
    Appendix A13). Family column names must not collide — a collision would
    silently corrupt the spans."""
    kind_list = [kinds] if isinstance(kinds, str) else list(kinds)
    frame = nodes.select("node_id")
    spans: list[int] = []
    seen: set[str] = set()
    for kind in kind_list:
        fam = _one_family(kind, nodes, edges, as_of, n_raw)
        cols = [c for c, dt in fam.schema.items() if c != "node_id" and dt.is_numeric()]
        clash = seen & set(cols)
        if clash:
            raise ValueError(f"feature family {kind!r} re-declares columns {sorted(clash)}")
        seen |= set(cols)
        spans.append(len(cols))
        frame = frame.join(fam.select(["node_id", *cols]), on="node_id", how="left")
    return frame, spans


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
    epochs: int = cfg.get("epochs", 200)
    patience: int = cfg.get("patience", 20)
    if epochs < 1 or patience < 1:
        raise ValueError(f"epochs and patience must be >= 1 (got {epochs}, {patience})")
    fence = split.get("fence_after")
    if fence is not None:
        nodes, edges = restrict_as_of(nodes, edges, fence)

    n_raw = meta.get("n_features", 0)
    feature_kind: str | list[str] = cfg.get("features", "raw")

    t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
    # training targets: what a supervisor could have known at train_end (F1)
    train_labels = resolve_train_labels(
        cfg.get("train_label_policy", "static"), labels, t_edges, train_end
    )
    # normalization stats are FIT on the train graph and FROZEN for inference
    # (F3): the model trains and scores under one normalization, not two
    train_raw, fusion_spans = _feature_frame(feature_kind, t_nodes, t_edges, train_end, n_raw)
    stats = fit_zscore(train_raw)
    train_data = build_graph(t_nodes, t_edges, train_labels, apply_zscore(train_raw, stats))
    infer_raw, _ = _feature_frame(feature_kind, nodes, edges, None, n_raw)
    infer_data = build_graph(nodes, edges, labels, apply_zscore(infer_raw, stats))

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
    fusion: str = model_cfg.pop("fusion", "concat")
    if fusion == "gated":  # context-fusion encoder needs the family widths (A13)
        model_cfg["fusion_spans"] = fusion_spans
    model = make_model(
        model_name,
        in_dim=train_data.x.shape[1],
        num_relations=int(train_data.num_relations),
        fusion=fusion,
        **model_cfg,
    )
    loss_cfg = dict(cfg.get("loss", {}))
    loss_fn = make_loss(loss_cfg.pop("name", "focal"), **loss_cfg)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=cfg.get("lr", 0.01), weight_decay=cfg.get("weight_decay", 5e-4)
    )

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
        # validation scores come from the TRAIN graph (F2): the same forward
        # that drove early stopping — test-period adjacency must not touch the
        # scores downstream calibration is fit on
        train_scores = torch.sigmoid(_forward(model, train_data)).numpy()
    scores_all = pl.DataFrame(
        {"node_id": pl.Series(infer_data.node_ids, dtype=pl.Utf8), "score": infer_scores}
    )
    train_scores_all = pl.DataFrame(
        {"node_id": pl.Series(train_data.node_ids, dtype=pl.Utf8), "score": train_scores}
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
    train_scores_all.filter(
        pl.col("node_id").is_in(pl.Series(sorted(val_ids)).implode())
    ).write_parquet(val_path)
    (out_dir / "feature_stats.json").write_text(
        json.dumps({"features": feature_kind, "stats": stats}, indent=2) + "\n", encoding="utf-8"
    )

    metrics = run_eval(
        {
            "dataset": dataset,
            "store_root": str(store.root),
            "budgets": cfg["budgets"],
            "node_scores": str(scores_path),
            "per_time_step": cfg.get("per_time_step", False),
            "output_dir": str(out_dir),
        }
    )
    run_record = {
        "dataset": dataset,
        "model": {"name": model_name, "fusion": fusion, **model_cfg},
        "features": feature_kind,
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
