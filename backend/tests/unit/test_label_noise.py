"""Label-noise robustness machinery tests (§7 step 29 iv): flip semantics,
leakage safety (evaluation labels untouched — pinned via prevalence
invariance), curve-runner mechanics on a scripted trainer."""

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from collusiongraph.training import apply_label_noise, run_label_noise, train_gnn

from .test_multiseed import tiny_store


def label_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "node_id": [f"n{i}" for i in range(10)],
            "label": ["illicit"] * 3 + ["licit"] * 5 + ["unknown"] * 2,
            "label_source": ["toy"] * 10,
            "confidence": [1.0] * 10,
        }
    )


class TestApplyLabelNoise:
    def test_rate_zero_is_exact_noop(self) -> None:
        labels = label_frame()
        out, n = apply_label_noise(labels, 0.0, seed=0)
        assert n == 0
        assert out.equals(labels)

    def test_exact_flip_count_and_confirmed_only(self) -> None:
        labels = label_frame()
        out, n = apply_label_noise(labels, 0.5, seed=0)
        assert n == 4  # round(0.5 × 8 confirmed)
        changed = (out["label"] != labels["label"]).sum()
        assert changed == 4
        # unknowns are never flipped
        assert out["label"].to_list()[8:] == ["unknown", "unknown"]
        # flips are symmetric swaps — confirmed count is conserved
        assert out["label"].is_in(["illicit", "licit"]).sum() == 8

    def test_deterministic_per_seed(self) -> None:
        labels = label_frame()
        a, _ = apply_label_noise(labels, 0.25, seed=5)
        b, _ = apply_label_noise(labels, 0.25, seed=5)
        c, _ = apply_label_noise(labels, 0.25, seed=6)
        assert a.equals(b)
        assert not a.equals(c)

    def test_invalid_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="rate"):
            apply_label_noise(label_frame(), 1.0, seed=0)
        with pytest.raises(ValueError, match="rate"):
            apply_label_noise(label_frame(), -0.1, seed=0)


TRAIN_CFG = {
    "dataset": "toyfin",
    "features": "raw",
    "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
    "model": {"name": "graphsage", "hidden_dim": 8, "dropout": 0.0},
    "loss": {"name": "focal", "gamma": 2.0},
    "epochs": 8,
    "patience": 4,
    "lr": 0.05,
    "budgets": [4],
}


class TestTrainerIntegration:
    def test_noise_never_touches_evaluation_labels(self, tmp_path) -> None:
        """Leakage-safety pin: the flip corrupts TRAIN supervision only — the
        test-side prevalence baseline (computed from stored labels) must be
        identical between a clean and a heavily-noised run."""
        store = tiny_store(tmp_path)
        clean = train_gnn(
            {**TRAIN_CFG, "store_root": str(store.root), "output_dir": str(tmp_path / "clean")}
        )
        noisy = train_gnn(
            {
                **TRAIN_CFG,
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "noisy"),
                "label_noise": {"rate": 0.4, "seed": 0},
            }
        )
        assert "label_noise" not in clean
        assert noisy["label_noise"]["n_flipped"] > 0
        assert (
            noisy["node_level"]["prevalence_baseline"] == clean["node_level"]["prevalence_baseline"]
        )
        assert noisy["node_level"]["n_confirmed"] == clean["node_level"]["n_confirmed"]

    def test_unidirectional_trainer_arm(self, tmp_path) -> None:  # §7 step 32 (−bidir)
        store = tiny_store(tmp_path)
        record = train_gnn(
            {
                **TRAIN_CFG,
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "unidir"),
                "bidirectional": False,
            }
        )
        assert record["bidirectional"] is False
        assert 0.0 <= record["node_level"]["auc_pr"] <= 1.0

    def test_rate_zero_matches_clean_run_exactly(self, tmp_path) -> None:
        store = tiny_store(tmp_path)
        clean = train_gnn(
            {**TRAIN_CFG, "store_root": str(store.root), "output_dir": str(tmp_path / "c")}
        )
        zero = train_gnn(
            {
                **TRAIN_CFG,
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "z"),
                "label_noise": {"rate": 0.0, "seed": 0},
            }
        )
        assert zero["node_level"]["auc_pr"] == clean["node_level"]["auc_pr"]
        assert zero["best_val_auc_pr"] == clean["best_val_auc_pr"]
        assert zero["label_noise"]["n_flipped"] == 0


class TestCurveRunner:
    def _script_trainer(self, monkeypatch, calls: list[tuple[float, int]]) -> None:
        def fake_train(cfg: dict) -> dict:
            rate = cfg.get("label_noise", {}).get("rate", 0.0)
            seed = cfg["seed"]
            calls.append((rate, seed))
            record = {
                "dataset": cfg["dataset"],
                "model": {"name": "graphsage"},
                "features": "raw",
                "seed": seed,
                "epochs_run": 2,
                "best_val_auc_pr": 0.9 - rate,
                "train_seconds": 0.1,
                "label_noise": {"rate": rate, "seed": seed, "n_flipped": int(rate * 100)},
                "node_level": {
                    "auc_pr": 0.8 - rate + 0.01 * seed,
                    "prevalence_baseline": 0.25,
                    "n_confirmed": 12,
                },
            }
            out = Path(cfg["output_dir"])
            out.mkdir(parents=True, exist_ok=True)
            (out / "run.json").write_text(json.dumps(record), encoding="utf-8")
            return record

        import collusiongraph.training.multiseed as ms

        monkeypatch.setattr(ms, "train_gnn", fake_train)

    def test_grid_resume_and_aggregation(self, tmp_path, monkeypatch) -> None:
        calls: list[tuple[float, int]] = []
        self._script_trainer(monkeypatch, calls)
        cfg = {
            "dataset": "toyfin",
            "label_noise_curve": True,
            "rates": [0.0, 0.1],
            "seeds": [0, 1],
            "model": {"name": "graphsage"},
            "budgets": [4],
            "output_dir": str(tmp_path),
        }
        report = run_label_noise(cfg)
        assert calls == [(0.0, 0), (0.0, 1), (0.1, 0), (0.1, 1)]
        assert [c["rate"] for c in report["curve"]] == [0.0, 0.1]
        clean = report["curve"][0]
        assert clean["auc_pr_mean"] == pytest.approx(np.mean([0.8, 0.81]))
        assert (tmp_path / "noise_curve.json").is_file()
        # resume: a second invocation retrains NOTHING
        report2 = run_label_noise(cfg)
        assert calls == [(0.0, 0), (0.0, 1), (0.1, 0), (0.1, 1)]
        assert report2["curve"][0]["auc_pr_mean"] == clean["auc_pr_mean"]

    def test_resume_rejects_foreign_grid_point(self, tmp_path, monkeypatch) -> None:
        calls: list[tuple[float, int]] = []
        self._script_trainer(monkeypatch, calls)
        run_dir = tmp_path / "rate_0.1_seed_0"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(
            json.dumps({"seed": 0, "label_noise": {"rate": 0.3}}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="different grid point"):
            run_label_noise(
                {
                    "dataset": "toyfin",
                    "label_noise_curve": True,
                    "rates": [0.1],
                    "seeds": [0],
                    "budgets": [4],
                    "output_dir": str(tmp_path),
                }
            )

    def test_cli_dispatch(self) -> None:
        from collusiongraph.cli import select_train_runner

        assert select_train_runner({"label_noise_curve": True}) == "label_noise_curve"
        # a plain gnn config with an inline label_noise key stays a gnn run
        assert select_train_runner({"model": {}, "label_noise": {"rate": 0.1}}) == "gnn"
