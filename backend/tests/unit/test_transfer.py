"""Transfer-probe tests (§7 steps 20–21): wiring + leakage discipline on tiny
fixtures. Model quality on real data is the run's job, not the tests'."""

import numpy as np
import polars as pl
import pytest
from collusiongraph.schema import GraphStore
from collusiongraph.training import run_cross_domain_probe, run_loco_transfer

RNG = np.random.default_rng(11)


def procurement_store(tmp_path) -> GraphStore:
    """Three countries, firm/tender graphs with awarded edges; every country
    carries both classes so any val_group choice is viable."""
    store = GraphStore(tmp_path / "interim")
    rows, edges, labels = [], [], []
    for c in ("c1", "c2", "c3"):
        for i in range(8):
            bad = i % 4 == 0
            firm, tender = f"firm:{c}:F{i}", f"tender:{c}:T{i}"
            year = 2010 + (i % 3)
            rows += [
                {
                    "node_id": firm,
                    "node_type": "firm",
                    "domain": "procurement",
                    "time_first_seen": year,
                    "raw_features": None,
                    "raw_attrs": None,
                },
                {
                    "node_id": tender,
                    "node_type": "tender",
                    "domain": "procurement",
                    "time_first_seen": year,
                    "raw_features": None,
                    "raw_attrs": None,
                },
            ]
            edges.append(
                {
                    "src": tender,
                    "dst": firm,
                    "edge_type": "awarded",
                    "timestamp": year,
                    "amount": None,
                    "directed": True,
                    "raw_attrs": None,
                }
            )
            # collusive firms co-award with their neighbor (a detectable pattern)
            if bad and i > 0:
                edges.append(
                    {
                        "src": tender,
                        "dst": f"firm:{c}:F{i - 1}",
                        "edge_type": "awarded",
                        "timestamp": year,
                        "amount": None,
                        "directed": True,
                        "raw_attrs": None,
                    }
                )
            labels.append(
                {
                    "node_id": firm,
                    "label": "illicit" if bad else "licit",
                    "label_source": "toy",
                    "confidence": 1.0,
                }
            )
    store.write("toyproc", "nodes", pl.DataFrame(rows))
    store.write("toyproc", "edges", pl.DataFrame(edges))
    store.write("toyproc", "labels", pl.DataFrame(labels))
    store.write_meta("toyproc", {"dataset": "toyproc", "time_unit": "year", "n_features": 0})
    return store


class TestLocoTransfer:
    def test_end_to_end_and_test_country_isolation(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        record = run_loco_transfer(
            {
                "dataset": "toyproc",
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "loco"),
                "seed": 0,
                "node_type": "firm",
                "test_group": "c3",
                "val_group": "c2",
                "model": {"name": "rgcn", "hidden_dim": 8, "dropout": 0.0},
                "epochs": 5,
                "patience": 5,
                "budgets": [4],
            }
        )
        assert record["test_group"] == "c3"
        assert record["fold"]["n_cross_group_edges_excluded"] == 0
        scores = pl.read_parquet(tmp_path / "loco" / "scores_test.parquet")
        assert scores.height > 0
        assert all(nid.startswith("firm:c3:") for nid in scores["node_id"].to_list())
        assert record["node_level"]["auc_pr"] >= 0.0

    def test_val_group_must_differ_from_test_group(self, tmp_path) -> None:
        store = procurement_store(tmp_path)
        with pytest.raises(ValueError, match="must differ"):
            run_loco_transfer(
                {
                    "dataset": "toyproc",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "x"),
                    "node_type": "firm",
                    "test_group": "c3",
                    "val_group": "c3",
                    "budgets": [4],
                }
            )


def financial_store(tmp_path) -> GraphStore:
    """Two-era financial account graph (source AND target for the probe)."""
    store = GraphStore(tmp_path / "interim")
    rows, edges, labels = [], [], []
    bad_ids = {0, 2, 4, 8, 10}
    for i in range(16):
        bad = i in bad_ids
        t = 1 + (i % 3) if i < 10 else 5
        rows.append(
            {
                "node_id": f"acct:n{i}",
                "node_type": "account",
                "domain": "financial",
                "time_first_seen": t,
                "raw_features": None,
                "raw_attrs": None,
            }
        )
        labels.append(
            {
                "node_id": f"acct:n{i}",
                "label": "illicit" if bad else "licit",
                "label_source": "toy",
                "confidence": 1.0,
            }
        )
    for i in range(15):
        edges.append(
            {
                "src": f"acct:n{i}",
                "dst": f"acct:n{i + 1}",
                "edge_type": "pays",
                "timestamp": 1 + (i % 3) if i < 9 else 5,
                "amount": 50.0,
                "directed": True,
                "raw_attrs": None,
            }
        )
    # fan-in onto each bad node — structural signal the probe can carry over
    for b in sorted(bad_ids):
        for j in range(2):
            src = f"acct:n{(b + 5 + j) % 16}"
            edges.append(
                {
                    "src": src,
                    "dst": f"acct:n{b}",
                    "edge_type": "pays",
                    "timestamp": 2 if b < 10 else 5,
                    "amount": 9.0,
                    "directed": True,
                    "raw_attrs": None,
                }
            )
    store.write("toysrc", "nodes", pl.DataFrame(rows))
    store.write("toysrc", "edges", pl.DataFrame(edges))
    store.write("toysrc", "labels", pl.DataFrame(labels))
    store.write_meta("toysrc", {"dataset": "toysrc", "time_unit": "step", "n_features": 0})
    return store


class TestCrossDomainProbe:
    def test_probe_end_to_end(self, tmp_path) -> None:
        store = financial_store(tmp_path)
        record = run_cross_domain_probe(
            {
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "probe"),
                "seed": 0,
                "budgets": [4],
                "source": {
                    "dataset": "toysrc",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "src_run"),
                    "seed": 0,
                    "features": "structural",
                    "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
                    "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
                    "epochs": 5,
                    "patience": 5,
                    "budgets": [4],
                },
                "target": {
                    "dataset": "toysrc",
                    "split": {"train_end": 3, "test_start": 5},
                },
            }
        )
        assert record["kind"] == "cross_domain_probe"
        assert record["n_probe_train"] > 0 and record["n_probe_test"] > 0
        assert 0.0 <= record["node_level"]["auc_pr"] <= 1.0
        scores = pl.read_parquet(tmp_path / "probe" / "scores_test.parquet")
        assert ((scores["score"] >= 0.0) & (scores["score"] <= 1.0)).all()

    def test_probe_rejects_non_structural_source(self, tmp_path) -> None:
        store = financial_store(tmp_path)
        with pytest.raises(ValueError, match="structural channel"):
            run_cross_domain_probe(
                {
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "p2"),
                    "budgets": [4],
                    "source": {"dataset": "toysrc", "features": "raw"},
                    "target": {"dataset": "toysrc", "split": {"train_end": 3}},
                }
            )
