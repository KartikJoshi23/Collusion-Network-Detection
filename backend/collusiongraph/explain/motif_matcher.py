"""Rule-based motif matcher (§4.4, §7 step 18).

The learned model finds the region; these transparent rules name the pattern.
The matcher operates on an IR (sub)graph and is deliberately independent of
the injection generators — §9.1 requires it to recover every injected motif
family with 100% recall on fixtures, so the two implementations cross-validate
each other.

Detection is pattern-level (cycles, stars, cliques, chains, rotation
sequences, bid clusters), not statistics-level — precisely what the M3
injection-recovery report showed graph-scale statistics miss.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import polars as pl


@dataclass(frozen=True)
class MotifMatch:
    motif_type: str
    member_node_ids: list[str]
    params: dict = field(default_factory=dict)

    def because(self) -> str:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(self.params.items()))
        return f"detected {self.motif_type} over {len(self.member_node_ids)} nodes ({detail})"


def _pays_digraph(edges: pl.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for src, dst, ts, amount in (
        edges.filter(pl.col("edge_type") == "pays")
        .select("src", "dst", "timestamp", "amount")
        .iter_rows()
    ):
        g.add_edge(src, dst, timestamp=ts, amount=amount)
    return g


def match_financial(
    edges: pl.DataFrame,
    fan_min: int = 5,
    cycle_max_len: int = 8,
    chain_min_len: int = 3,
    retention_min: float = 0.9,
    hold_max: int = 2,
    clique_min: int = 3,
) -> list[MotifMatch]:
    """The five financial motif-table rows on an IR (sub)graph."""
    g = _pays_digraph(edges)
    matches: list[MotifMatch] = []

    for cycle in nx.simple_cycles(g, length_bound=cycle_max_len):
        if len(cycle) >= 3:
            matches.append(MotifMatch("cycle", sorted(cycle), {"length": len(cycle)}))

    for node in g.nodes:
        in_deg, out_deg = g.in_degree(node), g.out_degree(node)
        if in_deg >= fan_min:
            members = sorted([node, *g.predecessors(node)])
            matches.append(MotifMatch("fan_in", members, {"m": in_deg}))
        if out_deg >= fan_min:
            members = sorted([node, *g.successors(node)])
            matches.append(MotifMatch("fan_out", members, {"m": out_deg}))

    matches.extend(_pass_through_chains(g, chain_min_len, retention_min, hold_max))
    matches.extend(_linked_cliques(edges, clique_min))
    return matches


def _pass_through_chains(
    g: nx.DiGraph, min_len: int, retention_min: float, hold_max: int
) -> list[MotifMatch]:
    """Maximal chains of consecutive hops with near-full retention and short
    holds: for middle nodes in==out==1, each hop forwards >= retention_min of
    the amount within <= hold_max time units."""

    def hop_ok(a: str, b: str, c: str) -> bool:
        e1, e2 = g.edges[a, b], g.edges[b, c]
        if e1["amount"] is None or e2["amount"] is None or not e1["amount"]:
            return False
        if e1["timestamp"] is None or e2["timestamp"] is None:
            return False
        return (
            e2["amount"] / e1["amount"] >= retention_min
            and 0 <= e2["timestamp"] - e1["timestamp"] <= hold_max
        )

    matches = []
    seen: set[tuple[str, ...]] = set()
    starts = [n for n in g.nodes if g.out_degree(n) == 1 and g.in_degree(n) == 0]
    for start in starts:
        chain = [start]
        node = start
        while g.out_degree(node) == 1:
            (nxt,) = g.successors(node)
            if len(chain) >= 2 and not hop_ok(chain[-2], node, nxt):
                break
            chain.append(nxt)
            if g.in_degree(nxt) != 1:
                break
            node = nxt
        if len(chain) - 1 >= min_len and tuple(chain) not in seen:
            seen.add(tuple(chain))
            matches.append(MotifMatch("pass_through", sorted(chain), {"hops": len(chain) - 1}))
    return matches


def _linked_cliques(edges: pl.DataFrame, clique_min: int) -> list[MotifMatch]:
    linked = edges.filter(pl.col("edge_type") == "linked_to")
    if linked.is_empty():
        return []
    g = nx.Graph(linked.select("src", "dst").iter_rows())
    return [
        MotifMatch("common_control", sorted(clique), {"k": len(clique)})
        for clique in nx.find_cliques(g)
        if len(clique) >= clique_min
    ]


def match_procurement(
    edges: pl.DataFrame,
    rotation_min_firms: int = 3,
    rotation_min_wins: int = 2,
    cover_margin: float = 0.06,
    cover_min: int = 2,
    cluster_cv_max: float = 0.05,
    co_bid_min_firms: int = 3,
    co_bid_min_tenders: int = 2,
    clique_min: int = 3,
) -> list[MotifMatch]:
    """The five procurement motif-table rows on an IR (sub)graph. Markets come
    from the node-id group segment (LOCO convention)."""
    matches: list[MotifMatch] = []
    awarded = edges.filter(pl.col("edge_type") == "awarded").select(
        pl.col("src").alias("tender"),
        pl.col("dst").alias("firm"),
        pl.col("timestamp"),
        pl.col("dst").str.split(":").list.get(1).alias("market"),
    )
    bids = edges.filter((pl.col("edge_type") == "bids_on") & pl.col("amount").is_not_null()).select(
        pl.col("src").alias("firm"), pl.col("dst").alias("tender"), "amount"
    )
    buys = edges.filter(pl.col("edge_type") == "buys_from").select(
        pl.col("src").alias("buyer"), pl.col("dst").alias("tender")
    )

    # rotation: within a market, >= n firms each winning >= w times
    for (market,), grp in awarded.group_by("market"):
        wins = grp.group_by("firm").len()
        rotating = wins.filter(pl.col("len") >= rotation_min_wins)
        if rotating.height >= rotation_min_firms:
            members = sorted(set(rotating["firm"]) | set(grp["tender"]))
            matches.append(
                MotifMatch(
                    "rotation",
                    members,
                    {"market": market, "n_firms": rotating.height},
                )
            )

    # cover bidding: >= cover_min losing bids all within (w, (1+margin)·w]
    for (tender,), grp in bids.group_by("tender"):
        if grp.height < cover_min + 1:
            continue
        amounts = grp.sort("amount")
        w = amounts["amount"][0]
        losing = amounts["amount"][1:]
        if ((losing > w) & (losing <= w * (1 + cover_margin))).all():
            matches.append(
                MotifMatch(
                    "cover_bid",
                    sorted([tender, *amounts["firm"].to_list()]),
                    {"n_covers": len(losing), "margin": cover_margin},
                )
            )

    # market allocation: >= 2 buyers with >= 2 awards each, firms never crossing
    pairs = awarded.join(buys, on="tender").select("buyer", "firm").unique()
    if pairs["buyer"].n_unique() >= 2:
        crossing = pairs.group_by("firm").len().filter(pl.col("len") > 1)
        per_buyer = pairs.group_by("buyer").len()
        if crossing.is_empty() and (per_buyer["len"] >= 2).all():
            matches.append(
                MotifMatch(
                    "partition",
                    sorted(set(pairs["buyer"]) | set(pairs["firm"])),
                    {"n_buyers": pairs["buyer"].n_unique()},
                )
            )

    # coordinated clustering: >= n firms sharing >= t tenders, clustered prices
    if not bids.is_empty():
        shared = (
            bids.join(bids, on="tender")
            .filter(pl.col("firm") != pl.col("firm_right"))
            .group_by("firm", "firm_right")
            .len()
        )
        core_firms = set(shared.filter(pl.col("len") >= co_bid_min_tenders)["firm"].to_list())
        if len(core_firms) >= co_bid_min_firms:
            cv = (
                bids.filter(pl.col("firm").is_in(sorted(core_firms)))
                .group_by("tender")
                .agg((pl.col("amount").std() / pl.col("amount").mean()).alias("cv"))
                .drop_nulls("cv")
            )
            if not cv.is_empty() and (cv["cv"] <= cluster_cv_max).all():
                tenders = bids.filter(pl.col("firm").is_in(sorted(core_firms)))["tender"]
                max_cv = cv["cv"].max()
                assert isinstance(max_cv, float)
                matches.append(
                    MotifMatch(
                        "clique",
                        sorted(core_firms | set(tenders)),
                        {"n_firms": len(core_firms), "max_cv": max_cv},
                    )
                )

    matches.extend(_linked_cliques(edges, clique_min))
    return matches


def match_motifs(edges: pl.DataFrame, domain: str, **params: float) -> list[MotifMatch]:
    if domain == "financial":
        return match_financial(edges, **params)  # type: ignore[arg-type]
    if domain == "procurement":
        return match_procurement(edges, **params)  # type: ignore[arg-type]
    raise ValueError(f"unknown domain {domain!r}")
