"""IR → PyG graph materialization (§3.2 graph store contract, §4.4).

Directionality is signal (fan-in vs fan-out are different crimes): every
directed IR edge is materialized in BOTH directions with a direction flag
(0 = original, 1 = reverse) following the bi-directional multi-edge evidence
from the Multi-GNN line (arXiv:2412.00241). R-GCN gets the same information as
relation ids (one forward + one reverse relation per IR edge type).

Labels follow §4.3 D1: y = 1 illicit / 0 licit / −1 unknown — unknowns
participate fully in message passing and are masked out of every loss.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import torch
from torch_geometric.data import Data

from collusiongraph.schema import Label


def build_graph(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    labels: pl.DataFrame,
    feature_frame: pl.DataFrame,
) -> Data:
    """Materialize a PyG ``Data`` from IR frames + a per-node feature table.

    ``feature_frame`` (node_id + numeric columns) supplies ``x`` — raw dataset
    features, the structural template, or both; NaN/null become 0.0 (models,
    unlike trees, cannot route on missingness).
    """
    node_ids = nodes["node_id"].to_list()
    index = {nid: i for i, nid in enumerate(node_ids)}

    numeric_cols = [
        c for c, dt in feature_frame.schema.items() if c != "node_id" and dt.is_numeric()
    ]
    aligned = (
        pl.DataFrame({"node_id": pl.Series(node_ids, dtype=pl.Utf8)})
        .join(feature_frame.select(["node_id", *numeric_cols]), on="node_id", how="left")
        .select(numeric_cols)
        .fill_null(0.0)
    )
    x = torch.from_numpy(np.nan_to_num(aligned.to_numpy().astype(np.float32), nan=0.0)).reshape(
        len(node_ids), len(numeric_cols)
    )

    src = np.fromiter((index[s] for s in edges["src"].to_list()), dtype=np.int64)
    dst = np.fromiter((index[d] for d in edges["dst"].to_list()), dtype=np.int64)
    edge_index = torch.from_numpy(
        np.stack([np.concatenate([src, dst]), np.concatenate([dst, src])])
    )
    n_e = len(src)
    direction = torch.cat([torch.zeros(n_e), torch.ones(n_e)]).unsqueeze(1)

    edge_types = sorted(edges["edge_type"].unique().to_list())
    type_of = {t: k for k, t in enumerate(edge_types)}
    fwd_rel = np.fromiter(
        (type_of[t] for t in edges["edge_type"].to_list()), dtype=np.int64, count=n_e
    )
    # reverse relations occupy ids [n_types, 2*n_types)
    edge_rel = torch.from_numpy(np.concatenate([fwd_rel, fwd_rel + len(edge_types)]))

    label_map = {
        nid: (1 if lab == Label.ILLICIT.value else 0 if lab == Label.LICIT.value else -1)
        for nid, lab in labels.select("node_id", "label").iter_rows()
    }
    y = torch.tensor([label_map.get(nid, -1) for nid in node_ids], dtype=torch.long)

    data = Data(x=x, edge_index=edge_index, y=y)
    data.edge_direction = direction
    data.edge_rel = edge_rel
    data.num_relations = 2 * len(edge_types)
    data.node_ids = node_ids
    return data


def confirmed_mask_for(data: Data, node_ids: set[str], node_type_prefix: str = "") -> torch.Tensor:
    """Boolean mask: confirmed-label nodes within ``node_ids`` (loss/eval pools).

    ``node_type_prefix`` (e.g. ``"firm:"``) restricts to one node type — the
    procurement regime where only firms are scored.
    """
    mask = torch.zeros(data.y.numel(), dtype=torch.bool)
    for i, nid in enumerate(data.node_ids):
        if nid in node_ids and data.y[i] >= 0 and nid.startswith(node_type_prefix):
            mask[i] = True
    return mask
