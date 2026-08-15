"""PyG Explainer runner (§4.4, §7 step 17): GNNExplainer over alert members.

Each explained node is attributed on its k-hop ego subgraph (GNNExplainer's
per-node mask optimization is affordable there; the ego graph is the node's
entire receptive field for a k-layer model, so nothing is lost). The
explainer attributes the SUPERVISED member's prediction — §4.4 scope honesty:
motif matcher and screens explain the other members, and the bundle labels
which evidence came from which source.

Works with GATv2 (each conv layer consumes the full doubled edge set, so
PyG's mask hooks align). GraphSAGE (slices edges by direction) and R-GCN
(RGCNConv propagates per relation over sliced edge subsets) are structurally
incompatible with mask-based explanation — enforced with a TypeError, not
silently wrong. That is the R12 de-risk finding: R-GCN explanations require
``HeteroExplanation`` over true ``HeteroData`` models (ledger follow-up);
until then procurement bundles carry matcher + screen evidence, labeled as
such per §4.4 scope honesty.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch_geometric.data import Data
from torch_geometric.explain import Explainer, GNNExplainer
from torch_geometric.explain.metric import fidelity
from torch_geometric.utils import k_hop_subgraph

from collusiongraph.models.gnn import GATv2


@dataclass(frozen=True)
class NodeExplanation:
    node_id: str
    subgraph_node_ids: list[str]  # explainer-selected minimal subgraph
    subgraph_edges: list[tuple[str, str]]
    fidelity_plus: float
    fidelity_minus: float


def attention_summaries(
    model: GATv2, data: Data, node_ids: list[str]
) -> dict[str, dict[str, float]]:
    """§4.4 attention corroboration (audit F15): one full-graph forward, then
    per requested node the mean/max last-layer attention over its INCOMING
    messages — the learned counterpart to the explainer's edge mask."""
    index_of = {nid: i for i, nid in enumerate(data.node_ids)}
    model.eval()
    with torch.no_grad():
        model(
            x=data.x,
            edge_index=data.edge_index,
            edge_direction=data.edge_direction,
            edge_rel=data.edge_rel,
        )
    assert model.last_attention is not None
    att_edge_index, att = model.last_attention  # att: (E', heads)
    out: dict[str, dict[str, float]] = {}
    for node_id in node_ids:
        idx = index_of.get(node_id)
        if idx is None:
            continue
        incoming = att_edge_index[1] == idx
        if not bool(incoming.any()):
            continue
        weights = att[incoming]
        out[node_id] = {
            "mean_incoming_attention": float(weights.mean()),
            "max_incoming_attention": float(weights.max()),
            "n_heads": float(weights.shape[1]),
            "n_incoming": float(weights.shape[0]),
        }
    return out


def _ego(data: Data, node_idx: int, num_hops: int) -> tuple[Data, int]:
    subset, edge_index, mapping, edge_mask = k_hop_subgraph(
        node_idx, num_hops, data.edge_index, relabel_nodes=True, num_nodes=data.x.shape[0]
    )
    sub = Data(x=data.x[subset], edge_index=edge_index)
    sub.edge_direction = data.edge_direction[edge_mask]
    sub.edge_rel = data.edge_rel[edge_mask]
    sub.node_ids = [data.node_ids[i] for i in subset.tolist()]
    return sub, int(mapping[0])


def explain_nodes(
    model: torch.nn.Module,
    data: Data,
    node_ids: list[str],
    num_hops: int = 2,
    epochs: int = 100,
    top_edges: int = 20,
    seed: int = 0,
) -> dict[str, NodeExplanation]:
    """GNNExplainer attribution for each requested node id present in ``data``."""
    if not isinstance(model, GATv2):
        raise TypeError(
            "the mask-based explainer supports GATv2 only (full-edge-set convs); "
            f"got {type(model).__name__} — R-GCN needs HeteroExplanation (R12, ledger)"
        )
    index_of = {nid: i for i, nid in enumerate(data.node_ids)}
    out: dict[str, NodeExplanation] = {}
    for node_id in node_ids:
        if node_id not in index_of:
            continue
        torch.manual_seed(seed)
        sub, target_idx = _ego(data, index_of[node_id], num_hops)
        explainer = Explainer(
            model=model,
            algorithm=GNNExplainer(epochs=epochs),
            explanation_type="model",
            edge_mask_type="object",
            node_mask_type="attributes",
            model_config=dict(mode="binary_classification", task_level="node", return_type="raw"),
            threshold_config=dict(
                threshold_type="topk", value=min(top_edges, sub.edge_index.shape[1])
            ),
        )
        explanation = explainer(
            sub.x,
            sub.edge_index,
            index=target_idx,
            edge_direction=sub.edge_direction,
            edge_rel=sub.edge_rel,
        )
        fid_plus, fid_minus = fidelity(explainer, explanation)

        kept = explanation.edge_mask > 0
        kept_edges = sub.edge_index[:, kept]
        kept_nodes = sorted({int(i) for i in kept_edges.flatten().tolist()} | {target_idx})
        out[node_id] = NodeExplanation(
            node_id=node_id,
            subgraph_node_ids=[sub.node_ids[i] for i in kept_nodes],
            subgraph_edges=[
                (sub.node_ids[int(s)], sub.node_ids[int(d)]) for s, d in kept_edges.t().tolist()
            ],
            fidelity_plus=float(fid_plus),
            fidelity_minus=float(fid_minus),
        )
    return out
