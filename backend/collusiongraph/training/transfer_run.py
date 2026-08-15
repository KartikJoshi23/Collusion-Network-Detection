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


def _group_label_stats(
    nodes: pl.DataFrame, labels: pl.DataFrame, prefix: str
) -> dict[str, tuple[int, int, int]]:
    """Confirmed-label counts per LOCO group for the typed nodes the fold
    scores: {group: (n_labeled, n_illicit, n_licit)}. Group = the second
    node_id segment, matching ``loco_folds``/``run_loco_transfer``."""
    typed = nodes.filter(pl.col("node_id").str.starts_with(prefix)) if prefix else nodes
    joined = (
        typed.select("node_id")
        .join(labels, on="node_id", how="inner")
        .with_columns(pl.col("node_id").str.split(":").list.get(1).alias("_g"))
    )
    stats: dict[str, tuple[int, int, int]] = {}
    for (group,), sub in joined.group_by("_g"):
        n_illicit = int((sub["label"] == "illicit").sum())
        n_licit = int((sub["label"] == "licit").sum())
        stats[str(group)] = (sub.height, n_illicit, n_licit)
    return stats


def _pick_val_group(
    test_group: str,
    stats: dict[str, tuple[int, int, int]],
    min_per_class: int,
    overrides: dict[str, str],
) -> str:
    """Deterministic validation-group policy, fixed before any test number is
    read: the SMALLEST other group with >= min_per_class confirmed nodes per
    class (ties break lexicographically). Small val pools keep supervision in
    the loss pool — the published country_5/country_7 pairing is this rule's
    output — while the per-class floor excludes degenerate early-stopping
    pools. Explicit ``val_groups`` overrides win."""
    if test_group in overrides:
        return overrides[test_group]
    candidates = sorted(
        (n_labeled, group)
        for group, (n_labeled, n_illicit, n_licit) in stats.items()
        if group != test_group and n_illicit >= min_per_class and n_licit >= min_per_class
    )
    if not candidates:
        raise ValueError(
            f"no viable validation group for test fold {test_group!r} "
            f"(need >= {min_per_class} confirmed nodes per class)"
        )
    return candidates[0][1]


def run_loco_matrix(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """§7 step 28: the FULL LOCO matrix — every group takes one turn as the
    held-out market — under §7 step 29's multi-seed protocol (``seeds:``).

    Each fold is scored by the published single-fold protocol verbatim
    (``run_loco_transfer`` is called unchanged), so a matrix fold with the
    same seed and val group byte-reproduces the corresponding single-fold
    run. Folds whose test pool lacks both classes, or for which no viable
    validation group exists, are recorded as skipped with the reason —
    never silently dropped (§4.4 honest reporting)."""
    cfg = load_config(config)
    dataset: str = cfg["dataset"]
    store = GraphStore(cfg.get("store_root", "data/interim"))
    out_root = Path(cfg.get("output_dir", f"eval_outputs/{dataset}/transfer_loco_matrix"))
    seeds = [int(s) for s in cfg.get("seeds", [cfg.get("seed", 0)])]
    min_per_class = int(cfg.get("min_val_per_class", 3))
    overrides = {str(k): str(v) for k, v in (cfg.get("val_groups") or {}).items()}
    prefix = f"{cfg['node_type']}:" if cfg.get("node_type") else ""

    nodes = store.read(dataset, "nodes")
    labels = store.read(dataset, "labels")
    stats = _group_label_stats(nodes, labels, prefix)
    test_groups = cfg.get("test_groups")  # optional subset (chunked big matrices)
    if test_groups is not None:
        if unknown := sorted(set(test_groups) - set(stats)):
            raise ValueError(f"test_groups not in the dataset's labeled groups: {unknown}")
        stats_to_run = {g: stats[g] for g in test_groups}
    else:
        stats_to_run = stats

    passthrough: dict[str, Any] = {
        key: cfg[key]
        for key in (
            "dataset",
            "store_root",
            "node_type",
            "model",
            "loss",
            "lr",
            "weight_decay",
            "epochs",
            "patience",
            "budgets",
        )
        if key in cfg
    }

    folds: list[dict[str, Any]] = []
    for test_group in sorted(stats_to_run):
        n_labeled, n_illicit, n_licit = stats[test_group]
        if n_illicit == 0 or n_licit == 0:
            folds.append(
                {
                    "test_group": test_group,
                    "status": "skipped",
                    "reason": (
                        f"test pool lacks both classes "
                        f"({n_illicit} illicit / {n_licit} licit of {n_labeled})"
                    ),
                }
            )
            continue
        try:
            val_group = _pick_val_group(test_group, stats, min_per_class, overrides)
        except ValueError as e:
            folds.append({"test_group": test_group, "status": "skipped", "reason": str(e)})
            continue
        runs: list[dict[str, Any]] = []
        fold_failed = False
        for seed in seeds:
            try:
                record = run_loco_transfer(
                    {
                        **passthrough,
                        "test_group": test_group,
                        "val_group": val_group,
                        "seed": seed,
                        "output_dir": str(out_root / f"fold_{test_group}_s{seed}"),
                    }
                )
            except ValueError as e:  # per-fold structural failure — record, keep the matrix
                folds.append(
                    {
                        "test_group": test_group,
                        "val_group": val_group,
                        "status": "skipped",
                        "reason": f"seed {seed}: {e}",
                    }
                )
                fold_failed = True
                break
            runs.append(record)
        if fold_failed:
            continue
        aucs = [r["node_level"]["auc_pr"] for r in runs]
        prevalence = runs[0]["node_level"]["prevalence_baseline"]
        fold_entry: dict[str, Any] = {
            "test_group": test_group,
            "val_group": val_group,
            "status": "completed",
            "n_confirmed_test": runs[0]["node_level"]["n_confirmed"],
            "prevalence_baseline": prevalence,
            "auc_pr_per_seed": aucs,
            "auc_pr_mean": float(np.mean(aucs)),
            "auc_pr_std": float(np.std(aucs, ddof=1)) if len(aucs) > 1 else 0.0,
            "lift_mean": float(np.mean(aucs) / prevalence),
        }
        for key in runs[0]["node_level"]:
            if key.startswith("precision@"):
                fold_entry[f"{key}_mean"] = float(np.mean([r["node_level"][key] for r in runs]))
        folds.append(fold_entry)

    completed = [f for f in folds if f["status"] == "completed"]
    matrix = {
        "kind": "loco_matrix",
        "dataset": dataset,
        "seeds": seeds,
        "min_val_per_class": min_per_class,
        "val_policy": (
            "smallest other group with >= min_val_per_class confirmed nodes "
            "per class; explicit val_groups overrides win"
        ),
        "folds": folds,
        "summary": {
            "n_folds": len(folds),
            "n_completed": len(completed),
            "macro_auc_pr_mean": (
                float(np.mean([f["auc_pr_mean"] for f in completed])) if completed else None
            ),
            "macro_lift_mean": (
                float(np.mean([f["lift_mean"] for f in completed])) if completed else None
            ),
        },
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "matrix.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return matrix


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


def _target_graphs(
    target_cfg: dict[str, Any], store: GraphStore
) -> tuple[Any, Any, dict[str, int], int, int]:
    """Target graphs under target-only normalization (F3 within the graph,
    §4.2 rule 2 across graphs) — shared by the frozen probe and the
    label-efficiency curve."""
    dataset: str = target_cfg["dataset"]
    train_end: int = target_cfg["split"]["train_end"]
    test_start: int = target_cfg["split"].get("test_start", train_end + 1)
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    labels = store.read(dataset, "labels")
    if (fence := target_cfg["split"].get("fence_after")) is not None:
        nodes, edges = restrict_as_of(nodes, edges, fence)
    train_feats, infer_feats = _structural_frames_for_probe(nodes, edges, train_end)
    t_nodes, t_edges = restrict_as_of(nodes, edges, train_end)
    train_data = build_graph(t_nodes, t_edges, labels, train_feats)
    infer_data = build_graph(nodes, edges, labels, infer_feats)
    times = dict(nodes.select("node_id", _TIME).iter_rows())
    return train_data, infer_data, times, train_end, test_start


def _pool_indices(
    data: Any, times: dict[str, int], prefix: str, lo: int, hi: int | None
) -> np.ndarray:
    """Confirmed, typed, time-windowed node positions (the probe's pool rule)."""
    keep = [
        i
        for i, nid in enumerate(data.node_ids)
        if data.y[i] >= 0
        and nid.startswith(prefix)
        and (t := times.get(nid)) is not None
        and t >= lo
        and (hi is None or t <= hi)
    ]
    return np.array(keep, dtype=np.int64)


def _source_encoder_kwargs(source_record: dict[str, Any]) -> dict[str, Any]:
    if source_record["model"].get("name", "graphsage") != "graphsage":
        raise ValueError("the frozen probe expects a GraphSAGE source encoder (embed() channel)")
    return {
        k: v
        for k, v in source_record["model"].items()
        if k not in ("name", "fusion", "fusion_spans", "fusion_dim")
    }


def _stratified_subsample(y: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """k positions from a confirmed-label pool, at least one per class (a probe
    fit needs both), class-proportional otherwise. k >= pool size returns the
    whole pool; k < 2 cannot hold both classes and raises."""
    if k >= len(y):
        return np.arange(len(y), dtype=np.int64)
    if k < 2:
        raise ValueError(f"k={k} cannot hold both classes (need k >= 2)")
    pos = np.flatnonzero(y == 1)
    neg = np.flatnonzero(y == 0)
    n_pos = int(np.clip(round(k * len(pos) / len(y)), 1, k - 1))
    picked = np.concatenate(
        [
            rng.choice(pos, size=min(n_pos, len(pos)), replace=False),
            rng.choice(neg, size=min(k - n_pos, len(neg)), replace=False),
        ]
    )
    return np.sort(picked)


def run_label_efficiency(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """§7 step 28 remainder: the cross-domain LABEL-EFFICIENCY curve — how much
    target supervision the transferred encoder needs before it pays off.

    At each k in ``k_grid``: fit the frozen-source-encoder probe on a
    stratified subsample of k labeled target-train nodes, and — on the SAME
    subsample — a paired no-transfer comparator (a probe on the target's own
    structural features). Both score the full target test pool (AP + its
    prevalence). ``n_draws`` subsample draws per k give mean ± std. The
    encoder and embeddings are computed once; nothing is tuned toward a
    desired curve (§4.4 honest reporting — the comparator can and may win)."""
    cfg = load_config(config)
    seed: int = cfg.get("seed", 0)
    torch.manual_seed(seed)
    np.random.seed(seed)

    source_cfg = dict(cfg["source"])
    target_cfg = dict(cfg["target"])
    out_dir = Path(cfg["output_dir"])
    store = GraphStore(cfg.get("store_root", "data/interim"))
    k_grid = sorted({int(k) for k in cfg.get("k_grid", [10, 25, 50, 100, 250])})
    n_draws = int(cfg.get("n_draws", 5))
    if any(k < 2 for k in k_grid):
        raise ValueError("k_grid values must be >= 2 (a probe fit needs both classes)")

    if source_cfg.get("features", "structural") != "structural":
        raise ValueError("the cross-domain probe operates on the shared structural channel only")
    source_record = train_gnn(source_cfg)
    checkpoint = Path(source_cfg["output_dir"]) / "model.pt"

    dataset: str = target_cfg["dataset"]
    prefix = f"{target_cfg['node_type']}:" if target_cfg.get("node_type") else ""
    train_data, infer_data, times, train_end, test_start = _target_graphs(target_cfg, store)

    encoder = GraphSAGE(in_dim=train_data.x.shape[1], **_source_encoder_kwargs(source_record))
    encoder.load_state_dict(torch.load(checkpoint, weights_only=True))
    encoder.eval()
    with torch.no_grad():
        emb_train = encoder.embed(
            train_data.x, train_data.edge_index, train_data.edge_direction
        ).numpy()
        emb_infer = encoder.embed(
            infer_data.x, infer_data.edge_index, infer_data.edge_direction
        ).numpy()

    idx_tr = _pool_indices(train_data, times, prefix, lo=0, hi=train_end)
    idx_te = _pool_indices(infer_data, times, prefix, lo=test_start, hi=None)
    y_tr = train_data.y.numpy()[idx_tr]
    y_te = infer_data.y.numpy()[idx_te]
    if y_tr.min() == y_tr.max() or y_te.min() == y_te.max():
        raise ValueError("probe pools lack both classes — check target split")
    # the paired comparator uses the target's own structural features
    raw_tr = train_data.x.numpy()[idx_tr]
    raw_te = infer_data.x.numpy()[idx_te]
    enc_tr, enc_te = emb_train[idx_tr], emb_infer[idx_te]
    prevalence = float(y_te.mean())

    def _fit_ap(x_fit: np.ndarray, y_fit: np.ndarray, x_eval: np.ndarray) -> float:
        probe = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
        probe.fit(x_fit, y_fit)
        return float(average_precision_score(y_te, probe.predict_proba(x_eval)[:, 1]))

    curve: list[dict[str, Any]] = []
    for k in k_grid:
        enc_aps: list[float] = []
        raw_aps: list[float] = []
        for draw in range(n_draws):
            rng = np.random.default_rng(seed * 10_000 + k * 100 + draw)
            try:
                sub = _stratified_subsample(y_tr, k, rng)
            except ValueError:
                break
            if y_tr[sub].min() == y_tr[sub].max():  # degenerate pool at tiny k
                continue
            enc_aps.append(_fit_ap(enc_tr[sub], y_tr[sub], enc_te))
            raw_aps.append(_fit_ap(raw_tr[sub], y_tr[sub], raw_te))
        if not enc_aps:
            curve.append({"k": k, "status": "skipped", "reason": "no viable subsample"})
            continue
        curve.append(
            {
                "k": min(k, len(y_tr)),
                "status": "completed",
                "n_draws": len(enc_aps),
                "source_probe_auc_pr_mean": float(np.mean(enc_aps)),
                "source_probe_auc_pr_std": (
                    float(np.std(enc_aps, ddof=1)) if len(enc_aps) > 1 else 0.0
                ),
                "raw_probe_auc_pr_mean": float(np.mean(raw_aps)),
                "raw_probe_auc_pr_std": (
                    float(np.std(raw_aps, ddof=1)) if len(raw_aps) > 1 else 0.0
                ),
                "transfer_gain_mean": float(np.mean(enc_aps) - np.mean(raw_aps)),
            }
        )

    record = {
        "kind": "label_efficiency",
        "direction": f"{source_cfg['dataset']} -> {dataset}",
        "seed": seed,
        "n_draws": n_draws,
        "n_pool_train": len(y_tr),
        "n_pool_test": len(y_te),
        "prevalence_baseline": prevalence,
        "source_val_auc_pr": source_record["best_val_auc_pr"],
        "full_label_reference": {
            "source_probe_auc_pr": _fit_ap(enc_tr, y_tr, enc_te),
            "raw_probe_auc_pr": _fit_ap(raw_tr, y_tr, raw_te),
        },
        "curve": curve,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "label_efficiency.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


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
    prefix = f"{target_cfg['node_type']}:" if target_cfg.get("node_type") else ""
    train_data, infer_data, times, train_end, test_start = _target_graphs(target_cfg, store)

    # 3. Frozen encoder (weights from the source run; head is ignored).
    model_kwargs = _source_encoder_kwargs(source_record)
    encoder = GraphSAGE(in_dim=train_data.x.shape[1], **model_kwargs)
    state = torch.load(checkpoint, weights_only=True)
    encoder.load_state_dict(state)
    encoder.eval()

    def _embed(data: Any) -> np.ndarray:
        with torch.no_grad():
            return encoder.embed(data.x, data.edge_index, data.edge_direction).numpy()

    emb_train, emb_infer = _embed(train_data), _embed(infer_data)

    # 4. Probe: fit on target train-period confirmed nodes, score the test period.
    idx_tr = _pool_indices(train_data, times, prefix, lo=0, hi=train_end)
    idx_te = _pool_indices(infer_data, times, prefix, lo=test_start, hi=None)
    x_tr, y_tr = emb_train[idx_tr], train_data.y.numpy()[idx_tr]
    x_te, y_te = emb_infer[idx_te], infer_data.y.numpy()[idx_te]
    ids_te = [infer_data.node_ids[i] for i in idx_te]
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
