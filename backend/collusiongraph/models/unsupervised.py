"""Unsupervised anomaly arm (§4.4, §7 step 14): DOMINANT-style and GAE-style
detectors + the transparent structural z-score floor.

PyGOD (the planned backend) cannot run in this environment: its ``fit`` routes
through ``NeighborLoader``, which requires the pyg-lib/torch-sparse compiled
extensions §4.1 deliberately excludes on Windows. These are faithful native
implementations of the same two detectors (decision-logged deviation):

* **DOMINANT** (Ding et al. 2019): shared GCN encoder, attribute decoder +
  inner-product structure decoder; node score = α·attribute reconstruction
  error + (1−α)·structure reconstruction error.
* **GAE** (attribute autoencoder): GCN encoder/decoder; score = attribute
  reconstruction error.

Both run on homogeneous projections (the caller filters to one edge type) and
never see labels — they are validated on labeled subsets they never trained on
(§4.4 evaluation policy) and by planted-anomaly unit tests (§9.1).
"""

from __future__ import annotations

import numpy as np
import polars as pl
import torch
from torch import nn
from torch_geometric.nn import GCNConv
from torch_geometric.utils import negative_sampling

from collusiongraph.features import structural_features, zscore_per_graph


class _GCNAutoencoder(nn.Module):
    """Shared encoder + attribute decoder (+ optional inner-product structure
    decoder scores computed outside the module)."""

    def __init__(self, in_dim: int, hid_dim: int = 32) -> None:
        super().__init__()
        self.enc1 = GCNConv(in_dim, hid_dim)
        self.enc2 = GCNConv(hid_dim, hid_dim)
        self.attr_dec = GCNConv(hid_dim, in_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor):
        h = torch.relu(self.enc1(x, edge_index))
        h = self.enc2(h, edge_index)
        x_hat = self.attr_dec(torch.relu(h), edge_index)
        return h, x_hat


def _edge_recon_errors(h: torch.Tensor, edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Per-node structure reconstruction error: BCE of the inner-product
    decoder on real edges (should be 1) and sampled non-edges (should be 0),
    averaged over each node's incident pairs."""
    neg = negative_sampling(edge_index, num_nodes=num_nodes, num_neg_samples=edge_index.shape[1])
    pairs = torch.cat([edge_index, neg], dim=1)
    targets = torch.cat([torch.ones(edge_index.shape[1]), torch.zeros(neg.shape[1])])
    logits = (h[pairs[0]] * h[pairs[1]]).sum(dim=1)
    errors = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")

    per_node = torch.zeros(num_nodes)
    counts = torch.zeros(num_nodes)
    for side in (0, 1):
        per_node.index_add_(0, pairs[side], errors)
        counts.index_add_(0, pairs[side], torch.ones_like(errors))
    return per_node / counts.clamp(min=1)


def _fit_scores(
    x: torch.Tensor,
    edge_index: torch.Tensor,
    method: str,
    hid_dim: int,
    epochs: int,
    lr: float,
    alpha: float,
    seed: int,
) -> np.ndarray:
    torch.manual_seed(seed)
    model = _GCNAutoencoder(x.shape[1], hid_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    n = x.shape[0]
    for _ in range(epochs):
        optimizer.zero_grad()
        h, x_hat = model(x, edge_index)
        attr_loss = ((x - x_hat) ** 2).mean()
        if method == "dominant":
            struct_loss = _edge_recon_errors(h, edge_index, n).mean()
            loss = alpha * attr_loss + (1 - alpha) * struct_loss
        else:  # gae: attribute reconstruction only
            loss = attr_loss
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        h, x_hat = model(x, edge_index)
        attr_err = ((x - x_hat) ** 2).mean(dim=1)
        if method == "dominant":
            struct_err = _edge_recon_errors(h, edge_index, n)
            scores = alpha * attr_err + (1 - alpha) * struct_err
        else:
            scores = attr_err
    return scores.numpy()


def unsupervised_scores(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    features: pl.DataFrame,
    method: str = "dominant",
    hid_dim: int = 32,
    epochs: int = 50,
    lr: float = 0.005,
    alpha: float = 0.5,
    seed: int = 0,
) -> pl.DataFrame:
    """Anomaly scores on a homogeneous projection (caller pre-filters edges to
    one edge type). ``features`` should be z-scored; nulls become 0."""
    if method not in ("dominant", "gae"):
        raise ValueError(f"unknown method {method!r} (expected dominant/gae)")
    node_ids = nodes["node_id"].to_list()
    index = {nid: i for i, nid in enumerate(node_ids)}

    numeric = [c for c, dt in features.schema.items() if c != "node_id" and dt.is_numeric()]
    aligned = (
        pl.DataFrame({"node_id": pl.Series(node_ids, dtype=pl.Utf8)})
        .join(features.select(["node_id", *numeric]), on="node_id", how="left")
        .select(numeric)
        .fill_null(0.0)
    )
    x = torch.from_numpy(np.nan_to_num(aligned.to_numpy().astype(np.float32), nan=0.0)).reshape(
        len(node_ids), len(numeric)
    )

    src = np.fromiter((index[s] for s in edges["src"].to_list()), dtype=np.int64)
    dst = np.fromiter((index[d] for d in edges["dst"].to_list()), dtype=np.int64)
    edge_index = torch.from_numpy(
        np.stack([np.concatenate([src, dst]), np.concatenate([dst, src])])
    )

    scores = _fit_scores(x, edge_index, method, hid_dim, epochs, lr, alpha, seed)
    return pl.DataFrame(
        {"node_id": pl.Series(node_ids, dtype=pl.Utf8), "score": scores.astype(np.float64)}
    )


def structural_floor(
    nodes: pl.DataFrame, edges: pl.DataFrame, as_of: int | None = None
) -> pl.DataFrame:
    """The transparent floor (§4.4): mean of positive per-graph z-scores over
    the structural template — high only when a node is structurally extreme in
    multiple ways at once. (Simplification of the planned degree-preserving
    null-model z-scores — Phase-2 upgrade, decision-logged.)"""
    z = zscore_per_graph(structural_features(nodes, edges, as_of=as_of))
    cols = [c for c in z.columns if c != "node_id"]
    return z.select(
        "node_id",
        pl.mean_horizontal([pl.col(c).clip(lower_bound=0.0) for c in cols]).alias("score"),
    )
