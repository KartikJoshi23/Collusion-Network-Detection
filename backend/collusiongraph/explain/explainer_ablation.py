"""Explainer fidelity ablation (§7 step 27): GNNExplainer vs PGExplainer vs
attention-only, on the same alert members.

Each arm proposes a top-k edge set for the same target node on the SAME ego
window; the arms are then scored with a UNIFORM hard-mask fidelity —
probability deltas of the model's own predicted class under hard edge
removal (necessity, fid+) and hard edge keeping (sufficiency, fid−) — so the
comparison is independent of each algorithm's internal soft-mask and metric
conventions. PyG's binary per-node fidelity is reported alongside for the
mask-based arms (it is what the published bundles carry).

Multi-edge caveat: kept sets are matched back to ego edges by (src, dst) node
pair, so if the doubled edge set contained duplicate pairs each duplicate is
kept together — an accepted approximation, absent from Elliptic++'s tx graph.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

import polars as pl
import torch
from torch_geometric.data import Data

from collusiongraph.eval import load_config
from collusiongraph.explain.explainer_runner import NodeExplanation, _ego, explain_nodes
from collusiongraph.explain.pgexplainer_runner import explain_nodes_pg
from collusiongraph.models.gnn import GATv2
from collusiongraph.schema import GraphStore

ARMS = ("gnn_explainer", "pg_explainer", "attention")


def hard_fidelity(
    model: torch.nn.Module, sub: Data, target_idx: int, kept: torch.Tensor
) -> tuple[float, float]:
    """(fid+, fid−) under hard masks: fid+ = p_full − p_without-explanation
    (necessity — large means removing the explanation breaks the prediction);
    fid− = p_full − p_explanation-only (sufficiency — small means the
    explanation alone reproduces it). p is the probability of the model's own
    predicted class on the full ego window."""

    def p_illicit(edge_mask: torch.Tensor) -> float:
        model.eval()
        with torch.no_grad():
            logits = model(
                x=sub.x,
                edge_index=sub.edge_index[:, edge_mask],
                edge_direction=sub.edge_direction[edge_mask],
                edge_rel=sub.edge_rel[edge_mask],
            )
        return float(torch.sigmoid(logits[target_idx]))

    full = torch.ones(sub.edge_index.shape[1], dtype=torch.bool)
    p_full_illicit = p_illicit(full)
    pred_is_illicit = p_full_illicit >= 0.5

    def as_pred(p: float) -> float:
        return p if pred_is_illicit else 1.0 - p

    p_full = as_pred(p_full_illicit)
    return (
        p_full - as_pred(p_illicit(~kept)),
        p_full - as_pred(p_illicit(kept)),
    )


def attention_topk_pairs(model: GATv2, sub: Data, top_edges: int) -> list[tuple[str, str]]:
    """The attention-only arm: rank the ego's edges by the last GATv2 layer's
    max-head attention (matched by (src, dst) pair — the conv appends
    self-loops, so column order is not relied on) and keep the top-k."""
    model.eval()
    with torch.no_grad():
        model(
            x=sub.x,
            edge_index=sub.edge_index,
            edge_direction=sub.edge_direction,
            edge_rel=sub.edge_rel,
        )
    assert model.last_attention is not None
    att_edge_index, att = model.last_attention
    score_of: dict[tuple[int, int], float] = {}
    for col in range(att_edge_index.shape[1]):
        pair = (int(att_edge_index[0, col]), int(att_edge_index[1, col]))
        score = float(att[col].max())
        score_of[pair] = max(score_of.get(pair, 0.0), score)

    pairs = [(int(s), int(d)) for s, d in sub.edge_index.t().tolist()]
    scores = [score_of.get(p, 0.0) for p in pairs]
    k = min(top_edges, len(pairs))
    kept_idx = sorted(range(len(pairs)), key=lambda i: -scores[i])[:k]
    return [(sub.node_ids[pairs[i][0]], sub.node_ids[pairs[i][1]]) for i in kept_idx]


def _mask_from_pairs(sub: Data, pairs: list[tuple[str, str]]) -> torch.Tensor:
    wanted = set(pairs)
    return torch.tensor(
        [
            (sub.node_ids[int(s)], sub.node_ids[int(d)]) in wanted
            for s, d in sub.edge_index.t().tolist()
        ],
        dtype=torch.bool,
    )


def run_explainer_ablation(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Config-driven §7-step-27 ablation over the top-k alerts' top members.
    Reuses the bundle writer's loading path (same checkpoint, same frozen
    normalization, same target selection) so the arms explain exactly the
    nodes the published bundles explain."""
    from collusiongraph.explain.bundles import load_supervised_for_explaining, top_members_of

    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    alerts = pl.read_parquet(cfg["alerts"]).sort("rank").head(cfg.get("top_k", 50))
    scores = pl.read_parquet(cfg["member_scores"])

    model, data = load_supervised_for_explaining(cfg, store, nodes, edges)
    targets = sorted(set(top_members_of(alerts, scores).values()))
    num_hops: int = cfg.get("num_hops", 2)
    top_edges: int = cfg.get("top_edges", 20)
    seed: int = cfg.get("seed", 0)
    arms: list[str] = list(cfg.get("arms", ARMS))
    pg_cfg = cfg.get("pg", {})

    kept_pairs: dict[str, dict[str, list[tuple[str, str]]]] = {}
    pyg_explanations: dict[str, dict[str, NodeExplanation]] = {}
    seconds: dict[str, float] = {}

    if "gnn_explainer" in arms:
        t0 = time.perf_counter()
        res = explain_nodes(
            model,
            data,
            targets,
            num_hops=num_hops,
            epochs=cfg.get("explainer_epochs", 100),
            top_edges=top_edges,
            seed=seed,
        )
        seconds["gnn_explainer"] = time.perf_counter() - t0
        pyg_explanations["gnn_explainer"] = res
        kept_pairs["gnn_explainer"] = {n: e.subgraph_edges for n, e in res.items()}

    if "pg_explainer" in arms:
        t0 = time.perf_counter()
        res = explain_nodes_pg(
            model,
            data,
            targets,
            num_hops=num_hops,
            train_epochs=pg_cfg.get("train_epochs", 30),
            lr=pg_cfg.get("lr", 0.003),
            top_edges=top_edges,
            seed=seed,
        )
        seconds["pg_explainer"] = time.perf_counter() - t0
        pyg_explanations["pg_explainer"] = res
        kept_pairs["pg_explainer"] = {n: e.subgraph_edges for n, e in res.items()}

    index_of = {nid: i for i, nid in enumerate(data.node_ids)}
    if "attention" in arms and isinstance(model, GATv2):
        t0 = time.perf_counter()
        att_pairs: dict[str, list[tuple[str, str]]] = {}
        for nid in targets:
            sub, _ = _ego(data, index_of[nid], num_hops)
            att_pairs[nid] = attention_topk_pairs(model, sub, top_edges)
        seconds["attention"] = time.perf_counter() - t0
        kept_pairs["attention"] = att_pairs

    per_node: list[dict[str, Any]] = []
    for nid in targets:
        sub, target_idx = _ego(data, index_of[nid], num_hops)
        for arm in arms:
            pairs = kept_pairs.get(arm, {}).get(nid)
            if pairs is None:
                continue
            fid_plus, fid_minus = hard_fidelity(
                model, sub, target_idx, _mask_from_pairs(sub, pairs)
            )
            row: dict[str, Any] = {
                "node_id": nid,
                "arm": arm,
                "hard_fidelity_plus": fid_plus,
                "hard_fidelity_minus": fid_minus,
                "hard_sane": fid_plus >= fid_minus,
                "n_kept_edges": len(pairs),
            }
            pyg = pyg_explanations.get(arm, {}).get(nid)
            if pyg is not None:
                row["pyg_fidelity_plus"] = pyg.fidelity_plus
                row["pyg_fidelity_minus"] = pyg.fidelity_minus
                row["pyg_sane"] = pyg.fidelity_plus >= pyg.fidelity_minus
            per_node.append(row)

    def _summary(arm: str) -> dict[str, Any]:
        rows = [r for r in per_node if r["arm"] == arm]
        if not rows:
            return {}
        out: dict[str, Any] = {
            "n_nodes": len(rows),
            "seconds": round(seconds.get(arm, 0.0), 2),
            "hard_fidelity_plus_mean": statistics.mean(r["hard_fidelity_plus"] for r in rows),
            "hard_fidelity_minus_mean": statistics.mean(r["hard_fidelity_minus"] for r in rows),
            "hard_sane_rate": statistics.mean(1.0 if r["hard_sane"] else 0.0 for r in rows),
        }
        if any("pyg_sane" in r for r in rows):
            out["pyg_sane_rate"] = statistics.mean(1.0 if r.get("pyg_sane") else 0.0 for r in rows)
        return out

    report = {
        "dataset": dataset,
        "arms": {arm: _summary(arm) for arm in arms},
        "config": {
            "top_k": cfg.get("top_k", 50),
            "num_hops": num_hops,
            "top_edges": top_edges,
            "seed": seed,
            "pg": {
                "train_epochs": pg_cfg.get("train_epochs", 30),
                "lr": pg_cfg.get("lr", 0.003),
            },
        },
        "per_node": per_node,
    }
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "explainer_ablation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
