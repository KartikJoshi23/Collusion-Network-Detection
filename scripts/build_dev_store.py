"""Dev serving store for UI design work on laptop-D (no trained artifacts here).

Uses the project's own machinery end-to-end: the motif injector plants real
motif instances into a synthetic background graph, the real matcher builds the
explanation bundles (so motifs/red-flags are genuine code-path output), and
write_serving_index wires it for `poe serve`. Output is gitignored
(eval_outputs/); numbers in the rigor artifacts are the ledger-published values
so the Model Lab renders realistic content. DESIGN SCAFFOLDING ONLY.

Run from the repo root: uv run python <this file>
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl
import pyarrow.parquet as pq
from api import write_serving_index
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.explain.bundles import build_bundle
from collusiongraph.injection.injector import inject
from collusiongraph.schema import Alert, Domain, GraphStore, MotifType, conform

REPO = Path.cwd()
OUT = REPO / "eval_outputs" / "dev_store"
STORE_ROOT = OUT / "interim"

MOTIF_MAP = {"coordinated_cluster": MotifType.CLIQUE}


def financial_background(rng: np.random.Generator, n: int = 320):
    ids = [f"acct:bg{i}" for i in range(n)]
    nodes = pl.DataFrame(
        {
            "node_id": pl.Series(ids, dtype=pl.Utf8),
            "node_type": ["account"] * n,
            "domain": ["financial"] * n,
            "time_first_seen": rng.integers(1, 50, size=n).tolist(),
            "raw_features": pl.Series([None] * n, dtype=pl.List(pl.Float32)),
            "raw_attrs": pl.Series([None] * n, dtype=pl.Utf8),
        }
    )
    # preferential-attachment-ish so the explorer shows hubs
    weights = 1.0 / (np.arange(n) + 8)
    weights /= weights.sum()
    rows = []
    for _ in range(760):
        s, d = rng.choice(n, size=2, replace=False, p=weights)
        rows.append(
            (
                ids[int(s)],
                ids[int(d)],
                "pays",
                int(rng.integers(1, 50)),
                float(rng.lognormal(9.2, 1.1)),
            )
        )
    edges = pl.DataFrame(
        {
            "src": [r[0] for r in rows],
            "dst": [r[1] for r in rows],
            "edge_type": [r[2] for r in rows],
            "timestamp": [r[3] for r in rows],
            "amount": [r[4] for r in rows],
            "directed": [True] * len(rows),
            "raw_attrs": pl.Series([None] * len(rows), dtype=pl.Utf8),
        }
    )
    return nodes, edges


def procurement_background(rng: np.random.Generator, n_firms: int = 90, n_tenders: int = 130):
    firms = [f"firm:bg:F{i}" for i in range(n_firms)]
    tenders = [f"tender:bg:T{i}" for i in range(n_tenders)]
    buyers = [f"buyer:bg:B{i}" for i in range(10)]
    rows_n = (
        [(f, "firm") for f in firms]
        + [(t, "tender") for t in tenders]
        + [(b, "buyer") for b in buyers]
    )
    nodes = pl.DataFrame(
        {
            "node_id": pl.Series([r[0] for r in rows_n], dtype=pl.Utf8),
            "node_type": [r[1] for r in rows_n],
            "domain": ["procurement"] * len(rows_n),
            "time_first_seen": rng.integers(2010, 2025, size=len(rows_n)).tolist(),
            "raw_features": pl.Series([None] * len(rows_n), dtype=pl.List(pl.Float32)),
            "raw_attrs": pl.Series([None] * len(rows_n), dtype=pl.Utf8),
        }
    )
    rows = []
    for ti, t in enumerate(tenders):
        year = int(rng.integers(2010, 2025))
        bidders = rng.choice(n_firms, size=int(rng.integers(2, 6)), replace=False)
        prices = rng.uniform(1e5, 9e5, size=len(bidders))
        for b, p in zip(bidders, prices, strict=True):
            rows.append((firms[int(b)], t, "bids_on", year, float(p), True))
        winner = firms[int(bidders[int(np.argmin(prices))])]
        rows.append((t, winner, "awarded", year, float(prices.min()), True))
        rows.append((buyers[ti % len(buyers)], winner, "buys_from", year, None, True))
    edges = pl.DataFrame(
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
    return nodes, edges


def member_edges_of(edges: pl.DataFrame, members: list[str]) -> pl.DataFrame:
    return edges.filter(pl.col("src").is_in(members) & pl.col("dst").is_in(members))


def build_dataset(name: str, domain: str, motifs: dict[str, int], window, seed: int):
    rng = np.random.default_rng(seed)
    if domain == "financial":
        bg_nodes, bg_edges = financial_background(rng)
    else:
        bg_nodes, bg_edges = procurement_background(rng)
    result = inject(bg_nodes, bg_edges, domain, motifs, window, seed=seed)
    nodes, edges, truth = result.nodes, result.edges, result.ground_truth

    store = GraphStore(STORE_ROOT)
    store.write(name, "nodes", nodes)
    store.write(name, "edges", edges)

    # alerts: injected instances first (high risk), then benign communities
    entries = []
    for row in truth.iter_rows(named=True):
        entries.append((row["motif_type"], row["member_node_ids"]))
    rng.shuffle(entries)
    n_benign = 9
    bg_ids = bg_nodes["node_id"].to_list()
    for _ in range(n_benign):
        anchor = bg_ids[int(rng.integers(0, len(bg_ids)))]
        hood = edges.filter((pl.col("src") == anchor) | (pl.col("dst") == anchor))
        members = sorted(
            {anchor, *hood["src"].to_list()[:4], *hood["dst"].to_list()[:4]} & set(bg_ids)
        ) or [anchor]
        entries.append((None, members))

    scores = np.sort(rng.uniform(0.28, 0.985, size=len(entries)))[::-1]
    # injected entries keep the top of the queue, benign fill the tail — but
    # interleave two benign into the head so the queue is not uniformly coral
    order = sorted(range(len(entries)), key=lambda i: (entries[i][0] is None, rng.random()))
    order = order[:6] + order[len(order) - 2 :] + order[6 : len(order) - 2]

    alerts, bundles = [], []
    for rank, idx in enumerate(order, start=1):
        motif, members = entries[idx]
        m_edges = member_edges_of(edges, members)
        ts = m_edges["timestamp"].cast(pl.Int64)
        alert = Alert(
            alert_id=f"{name}:dev0:{rank}",
            domain=Domain(domain),
            dataset=name,
            model_run_id="dev0",
            rank=rank,
            risk_score=float(scores[rank - 1]),
            community_id=f"c{idx}",
            member_node_ids=list(members),
            n_members=len(members),
            time_window_start=int(ts.min()) if m_edges.height else None,
            time_window_end=int(ts.max()) if m_edges.height else None,
            motif_type=(
                (MOTIF_MAP[motif] if motif in MOTIF_MAP else MotifType(motif)) if motif else None
            ),
        )
        alerts.append(alert.model_dump(mode="python"))

        explanation = None
        if motif is not None and rank <= 8 and domain == "financial":
            sub = members[: max(3, len(members) - 1)]
            explanation = SimpleNamespace(
                subgraph_node_ids=list(sub),
                subgraph_edges=[
                    (r["src"], r["dst"])
                    for r in member_edges_of(edges, list(sub)).iter_rows(named=True)
                ],
                fidelity_plus=float(rng.uniform(0.02, 0.06)),
                fidelity_minus=float(rng.uniform(-0.03, 0.0)),
                node_id=members[0],
            )
        bundle = build_bundle(
            alert.model_dump(mode="python"),
            domain,
            name,
            m_edges,
            nodes,
            explanation,
            budget_position=rank,
            explainer_name="pg_explainer",
        )
        bundles.append(bundle)

    alerts_path = OUT / name / "alerts.parquet"
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(conform("alerts", pl.DataFrame(alerts)), alerts_path)

    bundle_dir = OUT / name / "explanations"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for b in bundles:
        (bundle_dir / f"{b.alert_id.replace(':', '_')}.json").write_text(
            b.model_dump_json(), encoding="utf-8"
        )
    return alerts_path, bundle_dir


def write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return path


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    fin_alerts, fin_bundles = build_dataset(
        "dev_financial",
        "financial",
        {"cycle": 3, "fan_in": 3, "fan_out": 2, "common_control": 2, "pass_through": 3},
        (30, 49),
        seed=7,
    )
    proc_alerts, proc_bundles = build_dataset(
        "dev_procurement",
        "procurement",
        {
            "rotation": 3,
            "cover_bid": 3,
            "partition": 2,
            "common_control": 2,
            "coordinated_cluster": 3,
        },
        (2018, 2024),
        seed=11,
    )

    # metrics + rigor: ledger-published numbers, labeled dev copies
    fin_metrics = write_json(
        OUT / "dev_financial" / "metrics.json",
        {
            "node_level": {"auc_pr": 0.5492, "prevalence_baseline": 0.065, "precision@100": 0.96},
            "alert_level": {"n_alerts": 254, "precision@50": 0.32},
            "_dev_note": "ledger-published numbers; dev store for UI work",
        },
    )
    proc_metrics = write_json(
        OUT / "dev_procurement" / "metrics.json",
        {
            "node_level": {"auc_pr": 0.2808, "prevalence_baseline": 0.358, "precision@18": 0.222},
            "alert_level": {"n_alerts": 223, "precision@4": 0.50},
            "_dev_note": "ledger-published numbers; dev store for UI work",
        },
    )

    fin_rigor = {
        "multiseed_gatv2": write_json(
            OUT / "dev_financial" / "multiseed.json",
            {
                "kind": "multiseed_gnn",
                "aggregate": {
                    "auc_pr_mean": 0.4729,
                    "auc_pr_std": 0.0525,
                    "precision@100_mean": 0.812,
                    "precision@100_std": 0.238,
                },
                "per_seed": [
                    {"seed": s, "auc_pr": v}
                    for s, v in enumerate([0.5492, 0.4712, 0.4276, 0.4213, 0.4951])
                ],
            },
        ),
        "ensemble_multiseed": write_json(
            OUT / "dev_financial" / "ensemble_multiseed.json",
            {
                "members": {
                    "gatv2_focal": {
                        "auc_pr_mean": 0.4729,
                        "auc_pr_std": 0.0525,
                        "auc_pr_per_seed": [0.5492, 0.4712, 0.4276, 0.4213, 0.4951],
                    },
                    "ensemble_calibrated": {
                        "auc_pr_mean": 0.4434,
                        "auc_pr_std": 0.0501,
                        "auc_pr_per_seed": [0.5246, 0.4441, 0.4008, 0.3987, 0.4486],
                    },
                    "ensemble_rank": {
                        "auc_pr_mean": 0.0511,
                        "auc_pr_std": 0.0019,
                        "auc_pr_per_seed": [0.054, 0.0506, 0.0498, 0.0512, 0.0497],
                    },
                    "dominant": {"auc_pr_mean": 0.041, "auc_pr_std": 0.0003, "auc_pr_per_seed": []},
                    "gae": {"auc_pr_mean": 0.0386, "auc_pr_std": 0.0001, "auc_pr_per_seed": []},
                }
            },
        ),
        "significance": write_json(
            OUT / "dev_financial" / "significance.json",
            {
                "comparisons": {
                    "calibrated_vs_rank": {
                        "label_a": "ensemble_calibrated",
                        "label_b": "ensemble_rank",
                        "auc_pr_a": 0.5246,
                        "auc_pr_b": 0.0536,
                        "delta": 0.471,
                        "delta_ci_low": 0.44,
                        "delta_ci_high": 0.499,
                        "p_value": 0.001,
                    },
                    "gatv2_vs_b3": {
                        "label_a": "gatv2_focal",
                        "label_b": "b3_xgb_graph",
                        "auc_pr_a": 0.5492,
                        "auc_pr_b": 0.8104,
                        "delta": -0.261,
                        "delta_ci_low": -0.285,
                        "delta_ci_high": -0.235,
                        "p_value": 0.001,
                    },
                }
            },
        ),
        "label_noise": write_json(
            OUT / "dev_financial" / "noise_curve.json",
            {
                "curve": [
                    {"rate": 0.0, "auc_pr_mean": 0.4827, "auc_pr_std": 0.0616},
                    {"rate": 0.05, "auc_pr_mean": 0.5548, "auc_pr_std": 0.1217},
                    {"rate": 0.10, "auc_pr_mean": 0.5852, "auc_pr_std": 0.0428},
                    {"rate": 0.20, "auc_pr_mean": 0.5978, "auc_pr_std": 0.0248},
                ]
            },
        ),
    }

    garcia_matrix = (
        REPO / "eval_outputs" / "garcia_rodriguez" / "transfer_lomo_matrix" / "matrix.json"
    )
    proc_rigor = {
        "multiseed_rgcn": write_json(
            OUT / "dev_procurement" / "multiseed.json",
            {
                "kind": "multiseed_gnn",
                "aggregate": {"auc_pr_mean": 0.2808, "auc_pr_std": 0.0087},
                "per_seed": [
                    {"seed": s, "auc_pr": v}
                    for s, v in enumerate([0.2731, 0.2793, 0.2836, 0.2908, 0.2772])
                ],
            },
        ),
        "lomo_matrix_garcia": str(garcia_matrix),
        "label_efficiency_fin2proc": write_json(
            OUT / "dev_procurement" / "label_efficiency.json",
            {
                "curve": [
                    {
                        "k": k,
                        "status": "completed",
                        "source_probe_auc_pr_mean": s,
                        "transfer_gain_mean": g,
                    }
                    for k, s, g in [
                        (10, 0.201, -0.009),
                        (25, 0.205, -0.027),
                        (50, 0.214, -0.029),
                        (100, 0.229, 0.002),
                        (250, 0.244, -0.021),
                        (500, 0.259, -0.004),
                    ]
                ],
                "full_label_reference": {"source_probe_auc_pr": 0.2841, "raw_probe_auc_pr": 0.2705},
            },
        ),
    }

    index_path = REPO / "eval_outputs" / "serving.json"
    write_serving_index(
        index_path,
        {
            "dev_financial": {
                "domain": "financial",
                "store_root": str(STORE_ROOT),
                "alerts": str(fin_alerts),
                "explanations": str(fin_bundles),
                "metrics": [str(fin_metrics)],
                "rigor": {k: str(v) for k, v in fin_rigor.items()},
            },
            "dev_procurement": {
                "domain": "procurement",
                "store_root": str(STORE_ROOT),
                "alerts": str(proc_alerts),
                "explanations": str(proc_bundles),
                "metrics": [str(proc_metrics)],
                "rigor": {k: str(v) for k, v in proc_rigor.items()},
            },
        },
    )
    print(f"dev store written; serving index at {index_path}")
    print(SCREENING_CAVEAT)


if __name__ == "__main__":
    main()
