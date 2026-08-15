"""Amortized PGExplainer runner (§7 step 27, Phase 2).

PGExplainer trains ONE shared edge-scoring MLP over the explained instances
(amortized: ``train_epochs × N`` cheap ego forwards up front, then any node
explains in a single forward) — the queue-scale answer to GNNExplainer's
per-node mask optimization, and the candidate fix for the measured
explanation-quality defect (fidelity_sane false on 38/50 published Elliptic++
bundles).

PyG's PGExplainer supports phenomenon explanations only, so this runner feeds
the model's OWN hard predictions as the target: it explains model behavior,
touches no labels (leakage-safe by construction), and makes phenomenon-mode
fidelity coincide with the GNNExplainer runner's model-mode fidelity — the
two runners' fidelity numbers are directly comparable.

GATv2-only, enforced with a TypeError — the same R12 constraint as the
GNNExplainer runner (mask hooks require full-edge-set convs).
"""

from __future__ import annotations

import torch
from torch_geometric.data import Data
from torch_geometric.explain import Explainer
from torch_geometric.explain.algorithm import PGExplainer
from torch_geometric.explain.metric import fidelity

from collusiongraph.explain.explainer_runner import NodeExplanation, _ego
from collusiongraph.models.gnn import GATv2

_MODEL_CONFIG = dict(mode="binary_classification", task_level="node", return_type="raw")


def explain_nodes_pg(
    model: torch.nn.Module,
    data: Data,
    node_ids: list[str],
    num_hops: int = 2,
    train_epochs: int = 30,
    lr: float = 0.003,
    top_edges: int = 20,
    seed: int = 0,
) -> dict[str, NodeExplanation]:
    """PGExplainer attribution for each requested node id present in ``data``.

    Mirrors ``explain_nodes`` (same ego windows, same top-k edge thresholding,
    same ``NodeExplanation`` output) so the two explainers are drop-in
    alternatives for the bundle writer and directly comparable in the
    §7-step-27 ablation.
    """
    if not isinstance(model, GATv2):
        raise TypeError(
            "the mask-based explainer supports GATv2 only (full-edge-set convs); "
            f"got {type(model).__name__} — R-GCN needs HeteroExplanation (R12, ledger)"
        )
    index_of = {nid: i for i, nid in enumerate(data.node_ids)}
    present = [nid for nid in node_ids if nid in index_of]
    if not present:
        return {}

    torch.manual_seed(seed)
    algorithm = PGExplainer(epochs=train_epochs, lr=lr)
    # Constructing the wrapper wires explainer/model configs into the
    # algorithm (Explainer.connect) — required before algorithm.train().
    Explainer(
        model=model,
        algorithm=algorithm,
        explanation_type="phenomenon",
        edge_mask_type="object",
        model_config=_MODEL_CONFIG,
    )

    # Ego windows + targets (the model's own hard predictions) are computed
    # once and shared between the training loop and the explain pass.
    model.eval()
    egos: dict[str, tuple[Data, int, torch.Tensor]] = {}
    for nid in present:
        sub, target_idx = _ego(data, index_of[nid], num_hops)
        with torch.no_grad():
            logits = model(
                x=sub.x,
                edge_index=sub.edge_index,
                edge_direction=sub.edge_direction,
                edge_rel=sub.edge_rel,
            )
        egos[nid] = (sub, target_idx, (logits > 0).long())

    for epoch in range(train_epochs):
        for nid in present:
            sub, target_idx, target = egos[nid]
            algorithm.train(
                epoch,
                model,
                sub.x,
                sub.edge_index,
                target=target,
                index=target_idx,
                edge_direction=sub.edge_direction,
                edge_rel=sub.edge_rel,
            )

    out: dict[str, NodeExplanation] = {}
    for nid in present:
        sub, target_idx, target = egos[nid]
        explainer = Explainer(
            model=model,
            algorithm=algorithm,  # shared, already trained
            explanation_type="phenomenon",
            edge_mask_type="object",
            model_config=_MODEL_CONFIG,
            threshold_config=dict(
                threshold_type="topk", value=min(top_edges, sub.edge_index.shape[1])
            ),
        )
        explanation = explainer(
            sub.x,
            sub.edge_index,
            target=target,
            index=target_idx,
            edge_direction=sub.edge_direction,
            edge_rel=sub.edge_rel,
        )
        fid_plus, fid_minus = fidelity(explainer, explanation)

        kept = explanation.edge_mask > 0
        kept_edges = sub.edge_index[:, kept]
        kept_nodes = sorted({int(i) for i in kept_edges.flatten().tolist()} | {target_idx})
        out[nid] = NodeExplanation(
            node_id=nid,
            subgraph_node_ids=[sub.node_ids[i] for i in kept_nodes],
            subgraph_edges=[
                (sub.node_ids[int(s)], sub.node_ids[int(d)]) for s, d in kept_edges.t().tolist()
            ],
            fidelity_plus=float(fid_plus),
            fidelity_minus=float(fid_minus),
        )
    return out
