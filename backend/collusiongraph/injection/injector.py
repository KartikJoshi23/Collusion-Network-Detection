"""Synthetic motif injection into IR graphs (§4.4 item 4, §7 step 16).

``inject`` plants requested motif instances into a background graph and
returns the augmented frames plus a ground-truth record per instance — the
controlled recall/precision measurement RQ2 needs. Injected subgraphs are
optionally bridged to random background nodes with a few extra edges so they
are not trivially isolated components.

Background rows are never modified — only appended to (pinned by test).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from .generators.financial import GENERATORS as FINANCIAL_GENERATORS
from .generators.procurement import GENERATORS as PROCUREMENT_GENERATORS

GENERATORS = {"financial": FINANCIAL_GENERATORS, "procurement": PROCUREMENT_GENERATORS}


@dataclass(frozen=True)
class InjectionResult:
    nodes: pl.DataFrame
    edges: pl.DataFrame
    ground_truth: pl.DataFrame  # instance_id · motif_type · member_node_ids · n_edges


def inject(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    domain: str,
    motifs: dict[str, int],
    window: tuple[int, int],
    seed: int = 0,
    n_bridge_edges: int = 1,
) -> InjectionResult:
    """Plant ``motifs`` (motif name → instance count) into the background graph.

    ``window`` is the (t0, t1) timestamp range injected activity must live in —
    inject into the split the experiment scores (e.g. the test window), never
    across split boundaries.
    """
    generators = GENERATORS.get(domain)
    if generators is None:
        raise ValueError(f"unknown domain {domain!r}")
    unknown = set(motifs) - set(generators)
    if unknown:
        raise ValueError(f"unknown motifs for {domain}: {sorted(unknown)} ")
    t0, t1 = window
    if not t0 < t1:
        raise ValueError("window must satisfy t0 < t1")

    rng = np.random.default_rng(seed)
    background_ids = nodes["node_id"].to_list()
    seen_ids: set[str] = set(background_ids)
    new_nodes, new_edges, records = [], [], []
    for motif, count in motifs.items():
        for k in range(count):
            tag = f"{seed}x{k}"
            n_frame, e_frame, members = generators[motif](tag, rng, t0, t1)
            # Duplicate ids across instances silently corrupt ground truth and
            # every downstream join (found 2026-07-20: procurement families
            # shared market strings) — refuse loudly instead.
            fresh = n_frame["node_id"].to_list()
            clash = seen_ids.intersection(fresh)
            if clash:
                raise ValueError(
                    f"{motif} instance {tag} emits node ids that already exist "
                    f"(background or another instance): {sorted(clash)[:5]}"
                )
            seen_ids.update(fresh)
            bridges = _bridge_edges(members, background_ids, domain, rng, t0, t1, n_bridge_edges)
            new_nodes.append(n_frame)
            new_edges.append(e_frame)
            if bridges is not None:
                new_edges.append(bridges)
            records.append(
                {
                    "instance_id": f"{motif}:{tag}",
                    "motif_type": motif,
                    "member_node_ids": members,
                    "n_edges": e_frame.height,
                }
            )

    return InjectionResult(
        nodes=pl.concat([nodes, *new_nodes], how="vertical_relaxed"),
        edges=pl.concat([edges, *new_edges], how="vertical_relaxed"),
        ground_truth=pl.DataFrame(
            records,
            schema={
                "instance_id": pl.Utf8,
                "motif_type": pl.Utf8,
                "member_node_ids": pl.List(pl.Utf8),
                "n_edges": pl.Int64,
            },
        ),
    )


def _bridge_edges(
    members: list[str],
    background_ids: list[str],
    domain: str,
    rng: np.random.Generator,
    t0: int,
    t1: int,
    n: int,
) -> pl.DataFrame | None:
    """Light camouflage: connect injected nodes to random background nodes so
    the motif is embedded, not a floating component.

    Endpoints respect edge-type semantics (audit F26): financial bridges are
    ``pays`` between accounts (either direction); procurement bridges are
    ``bids_on`` from an injected FIRM to a background TENDER — never a
    schema-legal-but-nonsensical pairing."""
    if n <= 0 or not background_ids:
        return None
    if domain == "financial":
        edge_type, symmetric = "pays", True
        srcs_pool, dsts_pool = members, background_ids
    else:
        edge_type, symmetric = "bids_on", False
        srcs_pool = [m for m in members if m.startswith("firm:")]
        dsts_pool = [b for b in background_ids if b.startswith("tender:")]
        if not srcs_pool or not dsts_pool:
            return None  # nothing semantically valid to bridge with
    rows: dict[str, list] = {
        "src": [],
        "dst": [],
        "edge_type": [],
        "timestamp": [],
        "amount": [],
        "directed": [],
        "raw_attrs": [],
    }
    for _ in range(n):
        a = srcs_pool[int(rng.integers(len(srcs_pool)))]
        b = dsts_pool[int(rng.integers(len(dsts_pool)))]
        src, dst = (a, b) if (not symmetric or rng.random() < 0.5) else (b, a)
        rows["src"].append(src)
        rows["dst"].append(dst)
        rows["edge_type"].append(edge_type)
        rows["timestamp"].append(int(rng.integers(t0, t1 + 1)))
        rows["amount"].append(float(rng.uniform(1e3, 5e4)))
        rows["directed"].append(True)
        rows["raw_attrs"].append(None)
    return pl.DataFrame(rows).with_columns(
        pl.col("amount").cast(pl.Float64), pl.col("raw_attrs").cast(pl.Utf8)
    )


def recovery_at_budget(
    scores: pl.DataFrame,
    ground_truth: pl.DataFrame,
    budgets: list[int],
) -> pl.DataFrame:
    """Recall of injected members inside the top-k of a score frame, per motif
    type — the §7 step-16 recovery metric (RQ2's controlled measurement)."""
    ranked = scores.sort("score", descending=True)["node_id"].to_list()
    out = []
    for motif in ground_truth["motif_type"].unique().sort().to_list():
        members = set(
            ground_truth.filter(pl.col("motif_type") == motif)["member_node_ids"]
            .explode(empty_as_null=False)
            .to_list()
        )
        row: dict[str, object] = {"motif_type": motif, "n_members": len(members)}
        for k in budgets:
            top = set(ranked[:k])
            row[f"recall@{k}"] = len(top & members) / len(members)
        out.append(row)
    return pl.DataFrame(out)
