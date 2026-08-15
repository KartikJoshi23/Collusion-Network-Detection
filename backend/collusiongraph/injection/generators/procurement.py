"""Procurement motif generators (§4.4 motif table, §7 step 16) — the five
rows' cartel variants, following the OECD red-flag catalogue. Node ids embed a
synthetic market group (``inj_<motif>_<tag>``) so LOCO grouping still works on
augmented graphs. The motif name MUST be part of the market group: the injector
reuses the same tag across families, and market strings without the family
collided (firm:inj0x0:F0 from rotation vs common_control vs
coordinated_cluster) — found 2026-07-20 when the at-scale OCDS study crashed on
the duplicated ids; the injector now also guards against any recurrence."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

DOMAIN = "procurement"


def _nodes(rows: list[tuple[str, str]], t0: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "node_id": pl.Series([r[0] for r in rows], dtype=pl.Utf8),
            "node_type": [r[1] for r in rows],
            "domain": [DOMAIN] * len(rows),
            "time_first_seen": [t0] * len(rows),
            "raw_features": pl.Series([None] * len(rows), dtype=pl.List(pl.Float32)),
            "raw_attrs": pl.Series([None] * len(rows), dtype=pl.Utf8),
        }
    )


def _edges(rows: Sequence[tuple[str, str, str, int, float | None, bool]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src": [r[0] for r in rows],
            "dst": [r[1] for r in rows],
            "edge_type": [r[2] for r in rows],
            "timestamp": [r[3] for r in rows],
            "amount": pl.Series([r[4] for r in rows], dtype=pl.Float64),
            "directed": [r[5] for r in rows],
            "raw_attrs": pl.Series([None] * len(rows), dtype=pl.Utf8),
        }
    )


def rotation(tag: str, rng: np.random.Generator, t0: int, t1: int, n_firms: int = 4):
    """Row 1 — circular coordination: the win rotates around n firms."""
    market = f"inj_rotation_{tag}"
    firms = [f"firm:{market}:F{i}" for i in range(n_firms)]
    n_tenders = n_firms * 2
    tenders = [f"tender:{market}:T{i}" for i in range(n_tenders)]
    years = np.sort(rng.integers(t0, t1 + 1, size=n_tenders))
    edges = [
        (tenders[i], firms[i % n_firms], "awarded", int(years[i]), None, True)
        for i in range(n_tenders)
    ]
    nodes = _nodes([(f, "firm") for f in firms] + [(t, "tender") for t in tenders], t0)
    return nodes, _edges(edges), firms + tenders


def cover_bid(tag: str, rng: np.random.Generator, t0: int, t1: int, k_covers: int = 4):
    """Row 2 — convergent funneling: losing bids sit tightly above the
    pre-agreed winner."""
    market = f"inj_cover_bid_{tag}"
    tender = f"tender:{market}:T0"
    winner = f"firm:{market}:W"
    covers = [f"firm:{market}:C{i}" for i in range(k_covers)]
    year = int(rng.integers(t0, t1 + 1))
    w_price = float(rng.uniform(1e5, 1e6))
    edges = [
        (winner, tender, "bids_on", year, w_price, True),
        (tender, winner, "awarded", year, w_price, True),
    ] + [
        (c, tender, "bids_on", year, w_price * float(rng.uniform(1.01, 1.05)), True) for c in covers
    ]
    nodes = _nodes([(winner, "firm")] + [(c, "firm") for c in covers] + [(tender, "tender")], t0)
    return nodes, _edges(edges), [winner, *covers, tender]


def partition(tag: str, rng: np.random.Generator, t0: int, t1: int, n_per_side: int = 2):
    """Row 3 — divergent dispersal: firms split buyers exclusively (market
    allocation) — nobody ever crosses the line."""
    market = f"inj_partition_{tag}"
    firms_a = [f"firm:{market}:A{i}" for i in range(n_per_side)]
    firms_b = [f"firm:{market}:B{i}" for i in range(n_per_side)]
    buyers = [f"buyer:{market}:P", f"buyer:{market}:Q"]
    edges = []
    tenders = []
    for side, (buyer, firms) in enumerate(zip(buyers, [firms_a, firms_b], strict=True)):
        for j in range(2 * n_per_side):
            tender = f"tender:{market}:S{side}T{j}"
            tenders.append(tender)
            year = int(rng.integers(t0, t1 + 1))
            edges.append((buyer, tender, "buys_from", year, None, True))
            edges.append((tender, firms[j % n_per_side], "awarded", year, None, True))
    members = firms_a + firms_b + buyers + tenders
    nodes = _nodes(
        [(f, "firm") for f in firms_a + firms_b]
        + [(b, "buyer") for b in buyers]
        + [(t, "tender") for t in tenders],
        t0,
    )
    return nodes, _edges(edges), members


def common_control(tag: str, rng: np.random.Generator, t0: int, t1: int, k: int = 3):
    """Row 4 — hidden common control: 'rival' firms joined by a linked_to
    clique (shared director/address analog), all winning from one buyer."""
    market = f"inj_common_control_{tag}"
    firms = [f"firm:{market}:F{i}" for i in range(k)]
    buyer = f"buyer:{market}:B"
    tenders = [f"tender:{market}:T{i}" for i in range(k)]
    edges = [
        (firms[i], firms[j], "linked_to", t0, None, False)
        for i in range(k)
        for j in range(i + 1, k)
    ]
    for i, tender in enumerate(tenders):
        year = int(rng.integers(t0, t1 + 1))
        edges.append((buyer, tender, "buys_from", year, None, True))
        edges.append((tender, firms[i], "awarded", year, None, True))
    nodes = _nodes(
        [(f, "firm") for f in firms] + [(buyer, "buyer")] + [(t, "tender") for t in tenders], t0
    )
    return nodes, _edges(edges), [*firms, buyer, *tenders]


def coordinated_cluster(tag: str, rng: np.random.Generator, t0: int, t1: int, k: int = 4):
    """Row 5 — coordinated clustering: a co-bid near-clique with clustered
    prices and sequential timestamps."""
    market = f"inj_coordinated_cluster_{tag}"
    firms = [f"firm:{market}:F{i}" for i in range(k)]
    tenders = [f"tender:{market}:T{i}" for i in range(k)]
    edges = []
    base_year = int(rng.integers(t0, max(t0 + 1, t1 - k)))
    for j, tender in enumerate(tenders):
        year = base_year + (j % max(t1 - base_year, 1))
        base = float(rng.uniform(1e5, 5e5))
        for i, firm in enumerate(firms):
            price = base * (1.0 + 0.01 * i + float(rng.uniform(0, 0.004)))  # clustered
            edges.append((firm, tender, "bids_on", year, price, True))
        edges.append((tender, firms[j % k], "awarded", year, base, True))
    nodes = _nodes([(f, "firm") for f in firms] + [(t, "tender") for t in tenders], t0)
    return nodes, _edges(edges), firms + tenders


GENERATORS = {
    "rotation": rotation,
    "cover_bid": cover_bid,
    "partition": partition,
    "common_control": common_control,
    "coordinated_cluster": coordinated_cluster,
}
