"""Multi-seed runner tests (§7 step 29): orchestration, resume semantics, and
aggregation on a scripted trainer plus one tiny real train. Model quality on
real data is the run's job, not the tests'."""

import json
from itertools import pairwise
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from collusiongraph.schema import GraphStore
from collusiongraph.training import run_multiseed


def _fake_record(seed: int, auc: float) -> dict:
    return {
        "dataset": "toyfin",
        "model": {"name": "graphsage"},
        "features": "raw",
        "seed": seed,
        "epochs_run": 3,
        "best_epoch": 1,
        "best_val_auc_pr": 0.9,
        "train_seconds": 0.1,
        "node_level": {
            "auc_pr": auc,
            "prevalence_baseline": 0.25,
            "n_confirmed": 12,
            "precision@4": auc / 2,
        },
    }


def _script_trainer(monkeypatch, calls: list[int]) -> None:
    """Replace train_gnn inside the multiseed module with a fast fake that
    mimics the real contract: run.json is written LAST."""

    def fake_train(cfg: dict) -> dict:
        seed = cfg["seed"]
        calls.append(seed)
        record = _fake_record(seed, auc=0.5 + 0.1 * seed)
        out = Path(cfg["output_dir"])
        out.mkdir(parents=True, exist_ok=True)
        (out / "run.json").write_text(json.dumps(record), encoding="utf-8")
        return record

    import collusiongraph.training.multiseed as ms

    monkeypatch.setattr(ms, "train_gnn", fake_train)


BASE_CFG = {
    "dataset": "toyfin",
    "multiseed": True,
    "features": "raw",
    "model": {"name": "graphsage", "hidden_dim": 8},
    "budgets": [4],
}


class TestOrchestration:
    def test_aggregation_and_report(self, tmp_path, monkeypatch) -> None:
        calls: list[int] = []
        _script_trainer(monkeypatch, calls)
        report = run_multiseed({**BASE_CFG, "seeds": [0, 1, 2], "output_dir": str(tmp_path)})
        assert calls == [0, 1, 2]
        assert [p["seed"] for p in report["per_seed"]] == [0, 1, 2]
        # hand math: aucs 0.5/0.6/0.7
        assert report["aggregate"]["auc_pr_mean"] == pytest.approx(0.6)
        expected_std = float(np.std([0.5, 0.6, 0.7], ddof=1))
        assert report["aggregate"]["auc_pr_std"] == pytest.approx(expected_std)
        assert report["aggregate"]["precision@4_mean"] == pytest.approx(0.3)
        assert (tmp_path / "multiseed.json").is_file()

    def test_resume_skips_completed_seeds(self, tmp_path, monkeypatch) -> None:
        calls: list[int] = []
        _script_trainer(monkeypatch, calls)
        run_multiseed({**BASE_CFG, "seeds": [0], "output_dir": str(tmp_path)})
        report = run_multiseed({**BASE_CFG, "seeds": [0, 1], "output_dir": str(tmp_path)})
        # seed 0 was loaded from its run.json, never re-trained
        assert calls == [0, 1]
        assert len(report["per_seed"]) == 2

    def test_resume_rejects_foreign_protocol(self, tmp_path, monkeypatch) -> None:
        calls: list[int] = []
        _script_trainer(monkeypatch, calls)
        seed_dir = tmp_path / "seed_0"
        seed_dir.mkdir(parents=True)
        foreign = _fake_record(0, auc=0.5) | {"features": "structural"}
        (seed_dir / "run.json").write_text(json.dumps(foreign), encoding="utf-8")
        with pytest.raises(ValueError, match="different protocol"):
            run_multiseed({**BASE_CFG, "seeds": [0], "output_dir": str(tmp_path)})

    def test_rejects_duplicate_seeds_and_missing_flag(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            run_multiseed({**BASE_CFG, "seeds": [1, 1], "output_dir": str(tmp_path)})
        with pytest.raises(ValueError, match="multiseed: true"):
            cfg = {**BASE_CFG, "multiseed": False, "seeds": [0], "output_dir": str(tmp_path)}
            run_multiseed(cfg)

    def test_cli_dispatch(self) -> None:
        from collusiongraph.cli import select_train_runner

        assert select_train_runner({"multiseed": True, "model": {}}) == "multiseed"
        assert select_train_runner({"model": {}}) == "gnn"


class TestEnsembleMultiseed:
    def _script_ensemble(self, monkeypatch, calls: list[int]) -> None:
        from collusiongraph.training import multiseed as ms

        def fake_ensemble(cfg: dict) -> dict:
            seed = cfg["seed"]
            calls.append(seed)
            report = {
                "dataset": cfg["dataset"],
                "seed": seed,
                "members": {
                    "supervised": {"auc_pr": 0.5 + 0.1 * seed},
                    "ensemble_calibrated": {"auc_pr": 0.52 + 0.1 * seed},
                },
            }
            out = Path(cfg["output_dir"])
            out.mkdir(parents=True, exist_ok=True)
            (out / "ensemble_report.json").write_text(json.dumps(report), encoding="utf-8")
            # the wrapper must have routed the campaign's per-seed scores
            assert cfg["supervised_scores_dir"].endswith(f"seed_{seed}")
            return report

        monkeypatch.setattr(ms, "run_ensemble", fake_ensemble, raising=False)
        import collusiongraph.training.ensemble_run as er

        monkeypatch.setattr(er, "run_ensemble", fake_ensemble)

    def _campaign_root(self, tmp_path, seeds) -> Path:
        root = tmp_path / "campaign"
        for s in seeds:
            d = root / f"seed_{s}"
            d.mkdir(parents=True)
            (d / "scores_test.parquet").write_bytes(b"")
        return root

    def test_grid_resume_and_aggregation(self, tmp_path, monkeypatch) -> None:
        from collusiongraph.training import run_ensemble_multiseed

        calls: list[int] = []
        self._script_ensemble(monkeypatch, calls)
        cfg = {
            "dataset": "toyfin",
            "ensemble_multiseed": True,
            "seeds": [0, 1],
            "supervised_scores_root": str(self._campaign_root(tmp_path, [0, 1])),
            "output_dir": str(tmp_path / "ens"),
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "budgets": [4],
        }
        summary = run_ensemble_multiseed(cfg)
        assert calls == [0, 1]
        cal = summary["members"]["ensemble_calibrated"]
        assert cal["auc_pr_mean"] == pytest.approx(np.mean([0.52, 0.62]))
        assert (tmp_path / "ens" / "ensemble_multiseed.json").is_file()
        # resume: nothing re-runs
        run_ensemble_multiseed(cfg)
        assert calls == [0, 1]

    def test_missing_supervised_seed_dir_is_a_clear_error(self, tmp_path, monkeypatch) -> None:
        from collusiongraph.training import run_ensemble_multiseed

        calls: list[int] = []
        self._script_ensemble(monkeypatch, calls)
        with pytest.raises(ValueError, match="run the GNN multi-seed campaign first"):
            run_ensemble_multiseed(
                {
                    "dataset": "toyfin",
                    "ensemble_multiseed": True,
                    "seeds": [7],
                    "supervised_scores_root": str(self._campaign_root(tmp_path, [0])),
                    "output_dir": str(tmp_path / "ens"),
                    "budgets": [4],
                }
            )
        assert calls == []

    def test_cli_dispatch(self) -> None:
        from collusiongraph.cli import select_train_runner

        cfg = {"ensemble_multiseed": True, "supervised_scores_root": "x"}
        assert select_train_runner(cfg) == "ensemble_multiseed"
        # a plain ensemble config keeps its route
        assert select_train_runner({"supervised_scores_dir": "x"}) == "ensemble"


def tiny_store(tmp_path) -> GraphStore:
    """Minimal separable two-era account graph (pattern from the §9.2
    integration fixture, shrunk for a seconds-fast real double-train)."""
    rng = np.random.default_rng(0)
    store = GraphStore(tmp_path / "interim")
    rows, labels = [], []
    for era, (prefix, t0, n) in enumerate((("tr", 1, 30), ("te", 5, 12))):
        for i in range(n):
            bad = i < n // 4
            rows.append(
                {
                    "node_id": f"acct:{prefix}{i}",
                    "node_type": "account",
                    "domain": "financial",
                    "time_first_seen": (t0 + (i % 3)) if era == 0 else (t0 + (i % 2)),
                    "raw_features": rng.normal(1.0 if bad else -1.0, 0.3, size=4)
                    .astype(np.float32)
                    .tolist(),
                    "raw_attrs": None,
                }
            )
            labels.append(
                {
                    "node_id": f"acct:{prefix}{i}",
                    "label": "illicit" if bad else "licit",
                    "label_source": "toy",
                    "confidence": 1.0,
                }
            )
    ids = [r["node_id"] for r in rows]
    edges = pl.DataFrame(
        [
            {
                "src": a,
                "dst": b,
                "edge_type": "pays",
                "timestamp": 2 if a.startswith("acct:tr") else 5,
                "amount": 10.0,
                "directed": True,
                "raw_attrs": None,
            }
            for a, b in pairwise(ids[:30])
        ]
        + [
            {
                "src": a,
                "dst": b,
                "edge_type": "pays",
                "timestamp": 5,
                "amount": 10.0,
                "directed": True,
                "raw_attrs": None,
            }
            for a, b in pairwise(ids[30:])
        ]
    )
    store.write("toyfin", "nodes", pl.DataFrame(rows))
    store.write("toyfin", "edges", edges)
    store.write("toyfin", "labels", labels and pl.DataFrame(labels))
    store.write_meta("toyfin", {"dataset": "toyfin", "time_unit": "step", "n_features": 4})
    return store


@pytest.mark.integration
def test_real_two_seed_run(tmp_path) -> None:
    store = tiny_store(tmp_path)
    report = run_multiseed(
        {
            "dataset": "toyfin",
            "store_root": str(store.root),
            "output_dir": str(tmp_path / "ms"),
            "multiseed": True,
            "seeds": [0, 1],
            "features": "raw",
            "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
            "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
            "loss": {"name": "focal", "gamma": 2.0},
            "epochs": 10,
            "patience": 5,
            "lr": 0.05,
            "budgets": [4],
        }
    )
    assert (tmp_path / "ms" / "seed_0" / "run.json").is_file()
    assert (tmp_path / "ms" / "seed_1" / "run.json").is_file()
    assert 0.0 <= report["aggregate"]["auc_pr_mean"] <= 1.0
    assert report["aggregate"]["auc_pr_std"] >= 0.0
