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

    def embed(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_direction: torch.Tensor,
    ) -> torch.Tensor:
        """Penultimate node embeddings — the frozen-encoder channel for the
        §4.4 cross-domain probe (RQ4)."""
        flag = edge_direction.squeeze(-1)
        fwd_index = edge_index[:, flag == 0]
        rev_index = edge_index[:, flag == 1]  # already dst->src in the doubled set
        for layer in self.layers:
            x = self.dropout(torch.relu(layer(x, fwd_index, rev_index)))
        return x

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_direction: torch.Tensor,
        **_: object,
    ) -> torch.Tensor:
        return self.head(self.embed(x, edge_index, edge_direction)).squeeze(-1)


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


class ContextFusionEncoder(nn.Module):
    """Gated context fusion of per-node feature families (Appendix A13).

    Each family (raw dataset features / structural template / domain packs)
    gets its own linear encoder; a per-node sigmoid gate — computed from the
    concatenated family embeddings — weighs each family's contribution:

        fused = Σ_f  g_f ⊙ enc_f(x_f),   g = σ(W_g [enc_1 ‖ … ‖ enc_F])

    With ``fusion: concat`` (the default everywhere) this module is absent and
    the backbone consumes the plain concatenation — the B-CF ablation compares
    exactly these two paths under an otherwise identical protocol.
    """

    def __init__(self, family_dims: list[int], out_dim: int = 64) -> None:
        super().__init__()
        if len(family_dims) < 2:
            raise ValueError("context fusion needs >= 2 feature families; use concat otherwise")
        self.family_dims = list(family_dims)
        self.encoders = nn.ModuleList(nn.Linear(d, out_dim) for d in family_dims)
        self.gate = nn.Linear(len(family_dims) * out_dim, len(family_dims))
        self.out_dim = out_dim
        self.last_gates: torch.Tensor | None = None  # kept for inspection/ablation

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        parts, start = [], 0
        for dim, enc in zip(self.family_dims, self.encoders, strict=True):
            parts.append(torch.relu(enc(x[:, start : start + dim])))
            start += dim
        if start != x.shape[1]:
            raise ValueError(f"family dims {self.family_dims} do not cover x width {x.shape[1]}")
        gates = torch.sigmoid(self.gate(torch.cat(parts, dim=-1)))  # [N, F]
        self.last_gates = gates.detach()
        stacked = torch.stack(parts, dim=1)  # [N, F, out_dim]
        return (gates.unsqueeze(-1) * stacked).sum(dim=1)


class FusedModel(nn.Module):
    """Context-fusion encoder in front of any §4.4 backbone; forwards the
    backbone's signature untouched so trainer/explainer code is agnostic."""

    def __init__(self, encoder: ContextFusionEncoder, backbone: nn.Module) -> None:
        super().__init__()
        self.encoder = encoder
        self.backbone = backbone

    @property
    def last_attention(self) -> object:  # GATv2 corroboration signal (§4.4)
        return getattr(self.backbone, "last_attention", None)

    def forward(self, x: torch.Tensor, *args: object, **kwargs: object) -> torch.Tensor:
        return self.backbone(self.encoder(x), *args, **kwargs)


def make_model(
    name: str,
    in_dim: int,
    num_relations: int = 2,
    fusion: str = "concat",
    fusion_spans: list[int] | None = None,
    fusion_dim: int = 64,
    **kwargs: object,
) -> nn.Module:
    if fusion not in ("concat", "gated"):
        raise ValueError(f"unknown fusion {fusion!r} (expected concat/gated)")
    encoder: ContextFusionEncoder | None = None
    if fusion == "gated":
        if not fusion_spans:
            raise ValueError("fusion: gated requires fusion_spans (per-family widths)")
        if sum(fusion_spans) != in_dim:
            raise ValueError(f"fusion_spans {fusion_spans} must sum to in_dim {in_dim}")
        encoder = ContextFusionEncoder(fusion_spans, out_dim=fusion_dim)
        in_dim = fusion_dim

    backbone: nn.Module
    if name == "graphsage":
        backbone = GraphSAGE(in_dim, **kwargs)  # type: ignore[arg-type]
    elif name == "gatv2":
        backbone = GATv2(in_dim, **kwargs)  # type: ignore[arg-type]
    elif name == "rgcn":
        backbone = RGCN(in_dim, num_relations=num_relations, **kwargs)  # type: ignore[arg-type]
    else:
        raise ValueError(f"unknown model {name!r} (expected graphsage/gatv2/rgcn)")
    return FusedModel(encoder, backbone) if encoder is not None else backbone
