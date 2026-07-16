"""Supervised GNN family (§4.4): direction-aware GraphSAGE, GATv2, R-GCN.

Directionality handling per §4.4: SAGE aggregates forward and reverse
neighborhoods through separate weight matrices (relation-typed message
passing lite); GATv2 receives the direction flag as an edge feature
(``edge_dim=1``); R-GCN gets one forward + one reverse relation per IR edge
type. All models emit **binary logits per node** — community/subgraph scores
are produced downstream by the roll-up layer, never inside the encoders.
"""

from __future__ import annotations

from itertools import pairwise

import torch
from torch import nn
from torch_geometric.nn import GATv2Conv, RGCNConv, SAGEConv


class DirectedSAGELayer(nn.Module):
    """h' = W_self h + W_fwd · mean(in-neighbors) + W_rev · mean(out-neighbors).

    Two root-free SAGE aggregations (one per direction) plus an explicit self
    transform — summing stock SAGEConvs would double-count the root. Direction
    halves are selected from the doubled edge set via the flag, so every model
    consumes the same ``build_graph`` output.
    """

    def __init__(self, in_dim: int, out_dim: int) -> None:
        super().__init__()
        self.self_lin = nn.Linear(in_dim, out_dim)
        self.fwd = SAGEConv(in_dim, out_dim, root_weight=False)
        self.rev = SAGEConv(in_dim, out_dim, root_weight=False)

    def forward(
        self, x: torch.Tensor, fwd_index: torch.Tensor, rev_index: torch.Tensor
    ) -> torch.Tensor:
        return self.self_lin(x) + self.fwd(x, fwd_index) + self.rev(x, rev_index)


class GraphSAGE(nn.Module):
    def __init__(
        self, in_dim: int, hidden_dim: int = 128, num_layers: int = 2, dropout: float = 0.3
    ) -> None:
        super().__init__()
        dims = [in_dim] + [hidden_dim] * num_layers
        self.layers = nn.ModuleList(DirectedSAGELayer(a, b) for a, b in pairwise(dims))
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_direction: torch.Tensor,
        **_: object,
    ) -> torch.Tensor:
        flag = edge_direction.squeeze(-1)
        fwd_index = edge_index[:, flag == 0]
        rev_index = edge_index[:, flag == 1]  # already dst->src in the doubled set
        for layer in self.layers:
            x = self.dropout(torch.relu(layer(x, fwd_index, rev_index)))
        return self.head(x).squeeze(-1)


class GATv2(nn.Module):
    """GATv2 on the doubled edge set with the direction flag as edge feature;
    attention coefficients of the last layer are kept for the explanation
    layer's corroboration signal (§4.4)."""

    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        heads: int = 4,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.convs = nn.ModuleList()
        dim = in_dim
        for _ in range(num_layers):
            self.convs.append(GATv2Conv(dim, hidden_dim, heads=heads, edge_dim=1, concat=True))
            dim = hidden_dim * heads
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(dim, 1)
        self.last_attention: tuple[torch.Tensor, torch.Tensor] | None = None

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_direction: torch.Tensor,
        **_: object,
    ) -> torch.Tensor:
        for k, conv in enumerate(self.convs):
            if k == len(self.convs) - 1:
                x, attention = conv(
                    x, edge_index, edge_attr=edge_direction, return_attention_weights=True
                )
                self.last_attention = attention
            else:
                x = conv(x, edge_index, edge_attr=edge_direction)
            x = self.dropout(torch.relu(x))
        return self.head(x).squeeze(-1)


class RGCN(nn.Module):
    """R-GCN over relation ids (forward + reverse per IR edge type) — the
    §4.4 model for the inherently heterogeneous procurement graph."""

    def __init__(
        self,
        in_dim: int,
        num_relations: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        dims = [in_dim] + [hidden_dim] * num_layers
        self.convs = nn.ModuleList(
            RGCNConv(a, b, num_relations=num_relations) for a, b in pairwise(dims)
        )
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_rel: torch.Tensor,
        **_: object,
    ) -> torch.Tensor:
        for conv in self.convs:
            x = self.dropout(torch.relu(conv(x, edge_index, edge_rel)))
        return self.head(x).squeeze(-1)


def make_model(name: str, in_dim: int, num_relations: int = 2, **kwargs: object) -> nn.Module:
    if name == "graphsage":
        return GraphSAGE(in_dim, **kwargs)  # type: ignore[arg-type]
    if name == "gatv2":
        return GATv2(in_dim, **kwargs)  # type: ignore[arg-type]
    if name == "rgcn":
        return RGCN(in_dim, num_relations=num_relations, **kwargs)  # type: ignore[arg-type]
    raise ValueError(f"unknown model {name!r} (expected graphsage/gatv2/rgcn)")
