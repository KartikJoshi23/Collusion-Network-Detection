"""Financial motif generators (§4.4 motif table, §7 step 16) — one generator
per motif-table row. Each returns IR-conformant (nodes, edges, member_ids) for
one injected instance; the injector composes them into a background graph.

Parameters are randomized within realistic ranges by the caller's rng;
timestamps land inside the caller-supplied window; amounts follow the row's
tradecraft (sub-threshold smurfing deposits, near-zero pass-through retention).
AMLworld ground-truth calibration (§4.4) is deferred until a machine with
Kaggle credentials — recorded in the ledger.
"""

from __future__ import annotations

import numpy as np
import polars as pl

DOMAIN = "financial"
NODE_TYPE = "account"


def _nodes(ids: list[str], t0: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "node_id": pl.Series(ids, dtype=pl.Utf8),
            "node_type": [NODE_TYPE] * len(ids),
            "domain": [DOMAIN] * len(ids),
            "time_first_seen": [t0] * len(ids),
            "raw_features": pl.Series([None] * len(ids), dtype=pl.List(pl.Float32)),
            "raw_attrs": pl.Series([None] * len(ids), dtype=pl.Utf8),
        }
    )


def _pays(rows: list[tuple[str, str, int, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src": [r[0] for r in rows],
            "dst": [r[1] for r in rows],
            "edge_type": ["pays"] * len(rows),
            "timestamp": [r[2] for r in rows],
            "amount": [r[3] for r in rows],
            "directed": [True] * len(rows),
            "raw_attrs": pl.Series([None] * len(rows), dtype=pl.Utf8),
        }
    )


def cycle(tag: str, rng: np.random.Generator, t0: int, t1: int, k: int = 5):
    """Row 1 — circular coordination: funds return via k intermediaries ≤ window."""
    ids = [f"inj:cycle:{tag}:{i}" for i in range(k)]
    times = np.sort(rng.integers(t0, t1 + 1, size=k))
    amount = float(rng.uniform(5_000, 50_000))
    rows = [
        (ids[i], ids[(i + 1) % k], int(times[i]), amount * float(rng.uniform(0.97, 1.0)))
        for i in range(k)
    ]
    return _nodes(ids, t0), _pays(rows), ids


def fan_in(tag: str, rng: np.random.Generator, t0: int, t1: int, m: int = 8):
    """Row 2 — convergent funneling: m sub-threshold deposits into one target."""
    target = f"inj:fan_in:{tag}:target"
    sources = [f"inj:fan_in:{tag}:s{i}" for i in range(m)]
    rows = [
        (
            s,
            target,
            int(rng.integers(t0, t1 + 1)),
            float(rng.uniform(8_000, 9_900)),  # structured below the classic 10k threshold
        )
        for s in sources
    ]
    ids = [target, *sources]
    return _nodes(ids, t0), _pays(rows), ids


def fan_out(tag: str, rng: np.random.Generator, t0: int, t1: int, m: int = 8):
    """Row 3 — divergent dispersal: one source scatters to m mules."""
    source = f"inj:fan_out:{tag}:source"
    sinks = [f"inj:fan_out:{tag}:d{i}" for i in range(m)]
    total = float(rng.uniform(50_000, 200_000))
    shares = rng.dirichlet(np.ones(m)) * total
    rows = [
        (source, d, int(rng.integers(t0, t1 + 1)), float(a))
        for d, a in zip(sinks, shares, strict=True)
    ]
    ids = [source, *sinks]
    return _nodes(ids, t0), _pays(rows), ids


def common_control(tag: str, rng: np.random.Generator, t0: int, t1: int, k: int = 4):
    """Row 4 — hidden common control: accounts joined by a linked_to clique
    (shared agent/owner) with light pays activity among them."""
    ids = [f"inj:common_control:{tag}:{i}" for i in range(k)]
    linked = pl.DataFrame(
        {
            "src": [ids[i] for i in range(k) for j in range(i + 1, k)],
            "dst": [ids[j] for i in range(k) for j in range(i + 1, k)],
            "edge_type": ["linked_to"] * (k * (k - 1) // 2),
            "timestamp": [t0] * (k * (k - 1) // 2),
            "amount": pl.Series([None] * (k * (k - 1) // 2), dtype=pl.Float64),
            "directed": [False] * (k * (k - 1) // 2),
            "raw_attrs": pl.Series([None] * (k * (k - 1) // 2), dtype=pl.Utf8),
        }
    )
    pays = _pays(
        [
            (ids[i], ids[(i + 1) % k], int(rng.integers(t0, t1 + 1)), float(rng.uniform(1e3, 2e4)))
            for i in range(k - 1)
        ]
    )
    return _nodes(ids, t0), pl.concat([linked, pays]), ids


def pass_through(tag: str, rng: np.random.Generator, t0: int, t1: int, k: int = 5):
    """Row 5 — coordinated clustering: a chain with near-zero retention and
    abnormally short holding times."""
    ids = [f"inj:pass_through:{tag}:{i}" for i in range(k)]
    amount = float(rng.uniform(20_000, 100_000))
    t = int(rng.integers(t0, max(t0 + 1, t1 - k)))
    rows = []
    for i in range(k - 1):
        rows.append((ids[i], ids[i + 1], t + i, amount))  # hop per tick: shortest holds
        amount *= float(rng.uniform(0.985, 0.999))  # near-zero retention at each hop
    return _nodes(ids, t0), _pays(rows), ids


GENERATORS = {
    "cycle": cycle,
    "fan_in": fan_in,
    "fan_out": fan_out,
    "common_control": common_control,
    "pass_through": pass_through,
}
