"""Sensitivity-sweep tests (§7 step 29 iii): grid mechanics and direction-of-
effect identities on a hand-built queue — the published setting must be an
ordinary grid point, never special-cased."""

import polars as pl
from collusiongraph.eval import run_sensitivity


def queue_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    # ranked queue: a1/a2 overlap 2/3 (jaccard 0.5 — suppressed only when the
    # threshold drops BELOW 0.5, strict-greater rule); a3 disjoint
    alerts = pl.DataFrame(
        {
            "alert_id": ["a1", "a2", "a3"],
            "rank": [1, 2, 3],
            "n_members": [3, 3, 2],
            "member_node_ids": [["x", "y", "z"], ["x", "y", "w"], ["p", "q"]],
        }
    )
    labels = pl.DataFrame(
        {
            "node_id": ["x", "y", "z", "w", "p", "q"],
            # a1: 1 illicit of 3 confirmed (share 1/3); a2: same members bar w
            # (unknown → 2 confirmed, share 1/2); a3: clean
            "label": ["illicit", "licit", "licit", "unknown", "licit", "licit"],
            "label_source": ["toy"] * 6,
            "confidence": [1.0] * 6,
        }
    )
    return alerts, labels


class TestSensitivitySweep:
    def test_grid_and_direction_of_effect(self, tmp_path) -> None:
        alerts, labels = queue_fixture()
        alerts_path = tmp_path / "alerts.parquet"
        labels_path = tmp_path / "labels.parquet"
        alerts.write_parquet(alerts_path)
        labels.write_parquet(labels_path)
        report = run_sensitivity(
            {
                "dataset": "toy",
                "alerts": str(alerts_path),
                "labels": str(labels_path),
                "output_dir": str(tmp_path / "sens"),
                "budgets": [2],
                "sweep": {
                    "jaccard_thresholds": [0.4, 0.5],
                    "min_fractions": [None, 0.4, 0.9],
                },
            }
        )
        rows = report["results"]
        assert len(rows) == 6  # 2 × 3 grid
        by_key = {(r["jaccard_threshold"], r["min_fraction"]): r for r in rows}
        # strict-greater NMS: at 0.5 the 0.5-overlap pair BOTH survive; at 0.4
        # the later one is suppressed
        assert by_key[(0.5, None)]["n_kept"] == 3
        assert by_key[(0.4, None)]["n_kept"] == 2
        # published rule (≥1 confirmed illicit member): a1 and a2 hit
        assert by_key[(0.5, None)]["n_hits_total"] == 2
        # fractional 0.4: a1 (share 1/3) drops out, a2 (1/2) survives
        assert by_key[(0.5, 0.4)]["n_hits_total"] == 1
        # fractional 0.9: nothing reaches the bar
        assert by_key[(0.5, 0.9)]["n_hits_total"] == 0
        # stricter fractions never ADD hits at any grid point
        for jt in (0.4, 0.5):
            hits = [by_key[(jt, mf)]["n_hits_total"] for mf in (None, 0.4, 0.9)]
            assert hits == sorted(hits, reverse=True)
        assert (tmp_path / "sens" / "sensitivity.json").is_file()

    def test_defaults_are_the_published_single_point(self, tmp_path) -> None:
        alerts, labels = queue_fixture()
        alerts_path = tmp_path / "alerts.parquet"
        labels_path = tmp_path / "labels.parquet"
        alerts.write_parquet(alerts_path)
        labels.write_parquet(labels_path)
        report = run_sensitivity(
            {
                "dataset": "toy",
                "alerts": str(alerts_path),
                "labels": str(labels_path),
                "output_dir": str(tmp_path / "sens"),
                "budgets": [2],
            }
        )
        assert report["grid"] == {"jaccard_thresholds": [0.5], "min_fractions": [None]}
        assert len(report["results"]) == 1

    def test_cli_eval_routes_sweep_configs(self) -> None:
        # the eval command dispatches on the presence of "sweep" — pure check
        # that both entry points are importable from the package surface
        from collusiongraph.eval import run_eval, run_sensitivity  # noqa: F401


def test_percent_budgets_resolve_against_swept_queue(tmp_path) -> None:
    alerts, labels = queue_fixture()
    alerts_path = tmp_path / "alerts.parquet"
    labels_path = tmp_path / "labels.parquet"
    alerts.write_parquet(alerts_path)
    labels.write_parquet(labels_path)
    report = run_sensitivity(
        {
            "dataset": "toy",
            "alerts": str(alerts_path),
            "labels": str(labels_path),
            "output_dir": str(tmp_path / "sens"),
            "budgets": ["50%"],
            "sweep": {"jaccard_thresholds": [0.4, 0.5]},
        }
    )
    by_jt = {r["jaccard_threshold"]: r for r in report["results"]}
    # 50% of 3 kept → k=2 at threshold 0.5; 50% of 2 kept → k=1 at 0.4
    assert "@2" in by_jt[0.5]["queue"]
    assert "@1" in by_jt[0.4]["queue"]
