"""Week-7 transfer probes (§7 steps 20–21; §4.4 transfer & domain adaptation).

Step 20 — **LOCO transfer** (procurement): train on all countries but one, early-stop
on a held-out *train* country (group-respecting validation — the test country
touches nothing), score the test country's own subgraph in isolation. That is
the honest deployment scenario: a model shipped to a market it has never seen,
message-passing only over that market's graph.

Step 21 — **cross-domain frozen probe** (RQ4): a GraphSAGE encoder trained on the
*source* domain's shared structural channel (§4.2 rule 2) is frozen; target-node
embeddings feed a logistic-regression probe fit on the target's train period and
evaluated on its test period. Per-graph normalization discipline: each graph is
z-scored against its own train-subgraph stats (F3 within a graph, rule-2 across
graphs) — source stats never touch target features.

Honest-reporting requirement (§4.4): a weak or negative transfer result is a
result; nothing here retries or tunes toward a desired number.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from collusiongraph.eval import load_config, run_eval
from collusiongraph.features import apply_zscore, fit_zscore, restrict_as_of, structural_features
from collusiongraph.models.gnn import GraphSAGE, make_model
from collusiongraph.schema import GraphStore
from collusiongraph.splits import loco_folds

from .graph_build import build_graph, confirmed_mask_for
from .losses import make_loss
from .trainer import train_gnn

_TIME = "time_first_seen"


def _per_group_structural(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    """§4.2 rule-2 channel for entity-disjoint folds: the structural template is
    computed on each group's own subgraph and z-scored within that group, so no
    market's scale leaks into another's features."""
    grouped = nodes.with_columns(pl.col("node_id").str.split(":").list.get(1).alias("_g"))
    node_group = grouped.select("node_id", "_g")
    edges_g = edges.join(
        node_group.rename({"node_id": "src", "_g": "_sg"}), on="src", how="left"
    ).join(node_group.rename({"node_id": "dst", "_g": "_dg"}), on="dst", how="left")
    frames = []
    for (group,), sub in sorted(grouped.group_by("_g"), key=lambda g: g[0]):
        group_edges = edges_g.filter((pl.col("_sg") == group) & (pl.col("_dg") == group)).drop(
            "_sg", "_dg"
        )
        feats = structural_features(sub.drop("_g"), group_edges, as_of=None)
        stats = fit_zscore(feats)
        frames.append(apply_zscore(feats, stats))
    return pl.concat(frames)


def run_loco_transfer(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    seed: int = cfg.get("seed", 0)
    torch.manual_seed(seed)
    np.random.seed(seed)

    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    test_group: str = cfg["test_group"]
    val_group: str = cfg["val_group"]
    if test_group == val_group:
        raise ValueError("validation group must differ from the test group (nested honesty)")
    out_dir = Path(cfg.get("output_dir", f"eval_outputs/{dataset}/transfer_loco_{test_group}"))
    prefix = f"{cfg['node_type']}:" if cfg.get("node_type") else ""

    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")

    fold = next(f for f in loco_folds(nodes, edges) if f.test_group == test_group)
    features = _per_group_structural(nodes, edges)

    train_data = build_graph(fold.train_nodes, fold.train_edges, labels, features)
    test_data = build_graph(fold.test_nodes, fold.test_edges, labels, features)
    if sorted(fold.train_edges["edge_type"].unique()) != sorted(
        fold.test_edges["edge_type"].unique()
    ):
        raise ValueError("train/test folds disagree on edge types — relation ids would shift")

    val_ids = {
        nid for nid in fold.train_nodes["node_id"].to_list() if nid.split(":")[1] == val_group
    }
    loss_ids = set(fold.train_nodes["node_id"].to_list()) - val_ids
    loss_mask = confirmed_mask_for(train_data, loss_ids, prefix)
    val_mask = confirmed_mask_for(train_data, val_ids, prefix)
    for name, mask in (("loss", loss_mask), ("val", val_mask)):
        pool = train_data.y[mask]
        if pool.numel() == 0 or pool.min() == pool.max():
            raise ValueError(f"{name} pool lacks both classes — pick another val_group")

    model_cfg = dict(cfg.get("model", {}))
    model_name = model_cfg.pop("name", "rgcn")
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

    def _forward(data: Any) -> torch.Tensor:
        return model(
            x=data.x,
            edge_index=data.edge_index,
            edge_direction=data.edge_direction,
            edge_rel=data.edge_rel,
        )

    epochs, patience = cfg.get("epochs", 300), cfg.get("patience", 30)
    best_val, best_state, best_epoch = -1.0, None, -1
    val_y = train_data.y[val_mask].numpy()
    t0 = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        loss = loss_fn(_forward(train_data)[loss_mask], train_data.y[loss_mask])
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            val_ap = float(
                average_precision_score(
                    val_y, torch.sigmoid(_forward(train_data)[val_mask]).numpy()
                )
            )
        if val_ap > best_val:
            best_val, best_epoch = val_ap, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= patience:
            break
    assert best_state is not None
    model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        test_scores = torch.sigmoid(_forward(test_data)).numpy()
    scored = pl.DataFrame(
        {"node_id": pl.Series(test_data.node_ids, dtype=pl.Utf8), "score": test_scores}
    ).filter(pl.col("node_id").str.starts_with(prefix))

    out_dir.mkdir(parents=True, exist_ok=True)
    scores_path = out_dir / "scores_test.parquet"
    scored.write_parquet(scores_path)
    metrics = run_eval(
        {
            "dataset": dataset,
            "store_root": str(store.root),
            "budgets": cfg["budgets"],
            "node_scores": str(scores_path),
            "output_dir": str(out_dir),
        }
    )
    record = {
        "kind": "loco_transfer",
        "dataset": dataset,
        "test_group": test_group,
        "val_group": val_group,
        "model": {"name": model_name, **model_cfg},
        "seed": seed,
        "epochs_run": epoch + 1,
        "best_val_auc_pr": best_val,
        "train_seconds": round(time.perf_counter() - t0, 1),
        "fold": fold.report,
        "node_level": metrics.get("node_level"),
    }
    torch.save(model.state_dict(), out_dir / "model.pt")
    (out_dir / "run.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


def _structural_frames_for_probe(
    nodes: pl.DataFrame, edges: pl.DataFrame, train_end: int
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Target-domain features under target-only normalization (F3 within the
    graph, §4.2 rule 2 across graphs): stats fit on the train-period subgraph,
    frozen for the inference graph."""
    t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
    train_feats = structural_features(t_nodes, t_edges, as_of=train_end)
    stats = fit_zscore(train_feats)
    infer_feats = structural_features(nodes, edges, as_of=None)
    return apply_zscore(train_feats, stats), apply_zscore(infer_feats, stats)


def run_cross_domain_probe(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """§7 step 21: frozen source encoder → target embeddings → linear probe."""
    cfg = load_config(config)
    seed: int = cfg.get("seed", 0)
    torch.manual_seed(seed)
    np.random.seed(seed)

    source_cfg = dict(cfg["source"])
    target_cfg = dict(cfg["target"])
    out_dir = Path(cfg["output_dir"])
    store = GraphStore(cfg.get("store_root", "data/interim"))

    # 1. Source encoder: a normal §4.4 GraphSAGE run on the structural channel.
    if source_cfg.get("features", "structural") != "structural":
        raise ValueError("the cross-domain probe operates on the shared structural channel only")
    source_record = train_gnn(source_cfg)
    checkpoint = Path(source_cfg["output_dir"]) / "model.pt"

    # 2. Target graphs under target-only normalization.
    dataset: str = target_cfg["dataset"]
    train_end: int = target_cfg["split"]["train_end"]
    test_start: int = target_cfg["split"].get("test_start", train_end + 1)
    prefix = f"{target_cfg['node_type']}:" if target_cfg.get("node_type") else ""
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")
    if (fence := target_cfg["split"].get("fence_after")) is not None:
        nodes, edges = restrict_as_of(nodes, edges, fence)
    train_feats, infer_feats = _structural_frames_for_probe(nodes, edges, train_end)

    t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
    train_data = build_graph(t_nodes, t_edges, labels, train_feats)
    infer_data = build_graph(nodes, edges, labels, infer_feats)

    # 3. Frozen encoder (weights from the source run; head is ignored).
    model_kwargs = {k: v for k, v in source_record["model"].items() if k not in ("name", "fusion")}
    encoder = GraphSAGE(in_dim=train_data.x.shape[1], **model_kwargs)
    state = torch.load(checkpoint, weights_only=True)
    encoder.load_state_dict(state)
    encoder.eval()

    def _embed(data: Any) -> np.ndarray:
        with torch.no_grad():
            return encoder.embed(data.x, data.edge_index, data.edge_direction).numpy()

    emb_train, emb_infer = _embed(train_data), _embed(infer_data)

    # 4. Probe: fit on target train-period confirmed nodes, score the test period.
    times = dict(nodes.select("node_id", _TIME).iter_rows())

    def _pool(data: Any, emb: np.ndarray, lo: int, hi: int | None) -> tuple:
        keep = [
            i
            for i, nid in enumerate(data.node_ids)
            if data.y[i] >= 0
            and nid.startswith(prefix)
            and (t := times.get(nid)) is not None
            and t >= lo
            and (hi is None or t <= hi)
        ]
        idx = np.array(keep, dtype=np.int64)
        return emb[idx], data.y.numpy()[idx], [data.node_ids[i] for i in keep]

    x_tr, y_tr, _ = _pool(train_data, emb_train, lo=0, hi=train_end)
    x_te, y_te, ids_te = _pool(infer_data, emb_infer, lo=test_start, hi=None)
    if y_tr.min() == y_tr.max() or y_te.min() == y_te.max():
        raise ValueError("probe pools lack both classes — check target split")
    probe = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    probe.fit(x_tr, y_tr)
    scores = probe.predict_proba(x_te)[:, 1]

    out_dir.mkdir(parents=True, exist_ok=True)
    scores_path = out_dir / "scores_test.parquet"
    pl.DataFrame({"node_id": pl.Series(ids_te, dtype=pl.Utf8), "score": scores}).write_parquet(
        scores_path
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
    record = {
        "kind": "cross_domain_probe",
        "direction": f"{source_cfg['dataset']} -> {dataset}",
        "seed": seed,
        "source_val_auc_pr": source_record["best_val_auc_pr"],
        "source_node_level": source_record.get("node_level"),
        "n_probe_train": len(y_tr),
        "n_probe_test": len(y_te),
        "node_level": metrics.get("node_level"),
    }
    (out_dir / "run.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record
