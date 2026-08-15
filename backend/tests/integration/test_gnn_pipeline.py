"""Full-pipeline integration (§9.2): ingest → train (few epochs) → score →
calibrate → Leiden → alerts → harness, on a tiny synthetic financial dataset.
Runs in seconds; asserts the wiring, not model quality (units own correctness)."""

from itertools import pairwise

import numpy as np
import polars as pl
import pytest
from collusiongraph.schema import GraphStore
from collusiongraph.training import build_alert_queue, train_gnn

pytestmark = pytest.mark.integration


def synthetic_financial_store(tmp_path) -> GraphStore:
    """Feature-separable illicit/licit accounts over two eras; test era holds
    two clusters (one illicit-heavy, one clean) for the queue to rank."""
    rng = np.random.default_rng(0)
    store = GraphStore(tmp_path / "interim")

    def make_nodes(n: int, t0: int, illicit_share: float, prefix: str):
        rows = []
        for i in range(n):
            is_bad = i < int(n * illicit_share)
            loc = 1.0 if is_bad else -1.0
            rows.append(
                {
                    "node_id": f"acct:{prefix}{i}",
                    "node_type": "account",
                    "domain": "financial",
                    "time_first_seen": t0 + (i % 2),
                    "raw_features": (rng.normal(loc, 0.3, size=4)).astype(np.float32).tolist(),
                    "raw_attrs": None,
                    "_label": "illicit" if is_bad else ("unknown" if i % 7 == 6 else "licit"),
                }
            )
        return rows

    train_rows = make_nodes(40, 1, 0.25, "tr")  # t in {1,2}… val tail via t=3
    for i, row in enumerate(train_rows):
        row["time_first_seen"] = 1 + (i % 3)  # spread over t=1..3
    test_rows = make_nodes(16, 5, 0.25, "te")  # t in {5,6}
    all_rows = train_rows + test_rows

    nodes = pl.DataFrame([{k: v for k, v in r.items() if k != "_label"} for r in all_rows])
    labels = pl.DataFrame(
        [
            {
                "node_id": r["node_id"],
                "label": r["_label"],
                "label_source": "toy",
                "confidence": 1.0,
            }
            for r in all_rows
        ]
    )

    def chain_edges(ids: list[str], t: int) -> list[dict]:
        return [
            {
                "src": a,
                "dst": b,
                "edge_type": "pays",
                "timestamp": t,
                "amount": 100.0,
                "directed": True,
                "raw_attrs": None,
            }
            for a, b in pairwise(ids)
        ]

    train_ids = [r["node_id"] for r in train_rows]
    test_ids = [r["node_id"] for r in test_rows]
    edges = pl.DataFrame(
        chain_edges(train_ids, 2)
        + chain_edges(test_ids[:8], 5)  # cluster 1 (illicit-heavy: first 4 are illicit)
        + chain_edges(test_ids[8:], 6)  # cluster 2 (clean)
    )

    store.write("toyfin", "nodes", nodes)
    store.write("toyfin", "edges", edges)
    store.write("toyfin", "labels", labels)
    store.write_meta("toyfin", {"dataset": "toyfin", "time_unit": "step", "n_features": 4})
    return store


def test_train_score_queue_eval_end_to_end(tmp_path) -> None:
    store = synthetic_financial_store(tmp_path)
    out_dir = tmp_path / "run"
    record = train_gnn(
        {
            "dataset": "toyfin",
            "store_root": str(store.root),
            "output_dir": str(out_dir),
            "seed": 0,
            "features": "raw",
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "model": {"name": "graphsage", "hidden_dim": 16, "dropout": 0.0},
            "loss": {"name": "focal", "gamma": 2.0},
            "epochs": 60,
            "patience": 15,
            "lr": 0.05,
            "budgets": [4],
        }
    )
    assert (out_dir / "scores_test.parquet").is_file()
    assert (out_dir / "scores_val.parquet").is_file()
    assert (out_dir / "model.pt").is_file()
    assert 0.0 <= record["best_val_auc_pr"] <= 1.0
    # separable features: the GNN must beat the test prevalence baseline
    assert record["node_level"]["auc_pr"] > record["node_level"]["prevalence_baseline"]

    summary = build_alert_queue(
        {
            "dataset": "toyfin",
            "domain": "financial",
            "store_root": str(store.root),
            "scores_dir": str(out_dir),
            "output_dir": str(out_dir / "alerts"),
            "split": {"test_start": 5},
            "seed": 0,
            "budgets": [2],
            "model_run_id": "it0",
        }
    )
    assert summary["n_communities"] >= 2
    assert summary["n_alerts"] == summary["n_communities"]
    queue = summary["alert_level"]["queue"]["@2"]
    assert queue["k_effective"] == 2
    alerts = pl.read_parquet(out_dir / "alerts" / "alerts.parquet")
    assert alerts["rank"].to_list() == list(range(1, alerts.height + 1))
    assert ((alerts["risk_score"] >= 0.0) & (alerts["risk_score"] <= 1.0)).all()


def test_market_test_group_queue(tmp_path) -> None:
    """Entity-disjoint (LOMO) market queue: `test_group` selects one market by
    the id's second segment and uses precalibrated fold scores — the García
    path (no temporal test window). Asserts market isolation + the guard."""
    store = GraphStore(tmp_path / "interim")
    rows, edges, labels = [], [], []
    for m in ("A", "B"):
        for i in range(4):
            fid = f"firm:{m}:{i}"
            rows.append(
                {
                    "node_id": fid,
                    "node_type": "firm",
                    "domain": "procurement",
                    "time_first_seen": 2010,
                    "raw_features": None,
                    "raw_attrs": None,
                }
            )
            labels.append(
                {
                    "node_id": fid,
                    "label": "illicit" if i == 0 else "licit",
                    "label_source": "toy",
                    "confidence": 1.0,
                }
            )
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:  # one community per market
            edges.append(
                {
                    "src": f"firm:{m}:{a}",
                    "dst": f"firm:{m}:{b}",
                    "edge_type": "linked",
                    "timestamp": 2010,
                    "amount": None,
                    "directed": True,
                    "raw_attrs": None,
                }
            )
    store.write("toyproc", "nodes", pl.DataFrame(rows))
    store.write("toyproc", "edges", pl.DataFrame(edges))
    store.write("toyproc", "labels", pl.DataFrame(labels))
    store.write_meta("toyproc", {"dataset": "toyproc", "time_unit": "year", "n_features": 0})

    run_dir = tmp_path / "fold_A"
    run_dir.mkdir()
    pl.DataFrame(
        {"node_id": [f"firm:A:{i}" for i in range(4)], "score": [0.9, 0.8, 0.7, 0.6]}
    ).write_parquet(run_dir / "scores_test.parquet")

    summary = build_alert_queue(
        {
            "dataset": "toyproc",
            "domain": "procurement",
            "store_root": str(store.root),
            "scores_dir": str(run_dir),
            "output_dir": str(tmp_path / "q"),
            "test_group": "A",
            "precalibrated": True,
            "scores_file": "scores_test.parquet",
            "seed": 0,
            "budgets": [2],
            "model_run_id": "lomo_A",
        }
    )
    assert summary["n_alerts"] >= 1
    alerts = pl.read_parquet(tmp_path / "q" / "alerts.parquet")
    members = [m for row in alerts["member_node_ids"].to_list() for m in row]
    assert members and all(":A:" in m for m in members)  # market B never leaks in

    with pytest.raises(ValueError, match="precalibrated"):
        build_alert_queue(
            {
                "dataset": "toyproc",
                "domain": "procurement",
                "store_root": str(store.root),
                "scores_dir": str(run_dir),
                "output_dir": str(tmp_path / "q2"),
                "test_group": "A",
                "seed": 0,
                "budgets": [2],
                "model_run_id": "x",
            }
        )


def test_explainer_ablation_end_to_end(tmp_path) -> None:
    """§7 step 27 wiring: train a tiny GATv2 → queue → three-arm explainer
    ablation over the queue's top members; asserts report structure and the
    uniform hard-fidelity bounds, not explainer quality."""
    store = synthetic_financial_store(tmp_path)
    out_dir = tmp_path / "run"
    train_gnn(
        {
            "dataset": "toyfin",
            "store_root": str(store.root),
            "output_dir": str(out_dir),
            "seed": 0,
            "features": "raw",
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "model": {
                "name": "gatv2",
                "hidden_dim": 8,
                "num_layers": 2,
                "heads": 2,
                "dropout": 0.0,
            },
            "loss": {"name": "focal", "gamma": 2.0},
            "epochs": 30,
            "patience": 10,
            "lr": 0.05,
            "budgets": [4],
        }
    )
    build_alert_queue(
        {
            "dataset": "toyfin",
            "domain": "financial",
            "store_root": str(store.root),
            "scores_dir": str(out_dir),
            "output_dir": str(out_dir / "alerts"),
            "split": {"test_start": 5},
            "seed": 0,
            "budgets": [2],
            "model_run_id": "it0",
        }
    )

    from collusiongraph.explain import run_explainer_ablation

    report = run_explainer_ablation(
        {
            "dataset": "toyfin",
            "domain": "financial",
            "store_root": str(store.root),
            "alerts": str(out_dir / "alerts" / "alerts.parquet"),
            "member_scores": str(out_dir / "scores_test.parquet"),
            "output_dir": str(out_dir / "ablation"),
            "top_k": 2,
            "seed": 0,
            "supervised_model": {
                "name": "gatv2",
                "checkpoint": str(out_dir / "model.pt"),
                "hidden_dim": 8,
                "num_layers": 2,
                "heads": 2,
                "dropout": 0.0,
            },
            "arms": ["gnn_explainer", "pg_explainer", "attention"],
            "explainer_epochs": 10,
            "top_edges": 4,
            "pg": {"train_epochs": 5, "lr": 0.003},
        }
    )
    assert (out_dir / "ablation" / "explainer_ablation.json").is_file()
    for arm in ("gnn_explainer", "pg_explainer", "attention"):
        summary = report["arms"][arm]
        assert summary["n_nodes"] >= 1
        assert 0.0 <= summary["hard_sane_rate"] <= 1.0
        # hard fidelities are probability deltas
        assert -1.0 <= summary["hard_fidelity_plus_mean"] <= 1.0
        assert -1.0 <= summary["hard_fidelity_minus_mean"] <= 1.0
    # PyG per-node fidelity rides along for the mask-based arms only
    assert "pyg_sane_rate" in report["arms"]["gnn_explainer"]
    assert "pyg_sane_rate" in report["arms"]["pg_explainer"]
    assert "pyg_sane_rate" not in report["arms"]["attention"]
    for row in report["per_node"]:
        assert row["n_kept_edges"] <= 4


def test_training_is_blind_to_test_period_edges(tmp_path) -> None:
    """§9.1 leakage, end to end: adding test-period edges must not change the
    trained model's validation trajectory or its scores on train-period nodes."""
    store = synthetic_financial_store(tmp_path)
    cfg = {
        "dataset": "toyfin",
        "store_root": str(store.root),
        "output_dir": str(tmp_path / "runA"),
        "seed": 3,
        "features": "raw",
        "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
        "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
        "epochs": 15,
        "patience": 15,
        "budgets": [4],
    }
    record_a = train_gnn(cfg)
    val_a = pl.read_parquet(tmp_path / "runA" / "scores_val.parquet").sort("node_id")

    # poison the test period with heavy extra adjacency, retrain
    edges = store.read("toyfin", "edges")
    extra = pl.DataFrame(
        {
            "src": ["acct:te0"] * 5,
            "dst": [f"acct:te{i}" for i in range(3, 8)],
            "edge_type": ["pays"] * 5,
            "timestamp": [6] * 5,
            "amount": [9_999.0] * 5,
            "directed": [True] * 5,
            "raw_attrs": [None] * 5,
        }
    )
    store.write("toyfin", "edges", pl.concat([edges, extra]))
    cfg["output_dir"] = str(tmp_path / "runB")
    record_b = train_gnn(cfg)
    val_b = pl.read_parquet(tmp_path / "runB" / "scores_val.parquet").sort("node_id")

    assert record_a["best_val_auc_pr"] == record_b["best_val_auc_pr"]
    assert val_a.equals(val_b)
