"""Evaluation-harness correctness (§4.5, §9.1): every metric validated against
hand-computed values on toy vectors, and against scikit-learn where overlapping;
NMS dedup and hit-rule logic on constructed overlapping-alert fixtures."""

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest
import yaml
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.cli import main as cli_main
from collusiongraph.eval import (
    alert_queue_metrics,
    apply_hit_rule,
    auc_pr,
    confirmed_node_vectors,
    fpr_at_k,
    illicit_coverage_at_budget,
    jaccard,
    nms_dedup,
    precision_at_k,
    recall_at_k,
    run_eval,
)
from collusiongraph.schema import GraphStore
from sklearn.metrics import average_precision_score


def alert_frame(rows: list[dict]) -> pl.DataFrame:
    """Minimal alert frame: alert_id, rank, member_node_ids (+ n_members)."""
    return pl.DataFrame(
        [
            {
                "alert_id": r["alert_id"],
                "rank": r["rank"],
                "member_node_ids": r["members"],
                "n_members": len(r["members"]),
            }
            for r in rows
        ]
    ).with_columns(pl.col("rank").cast(pl.Int32), pl.col("n_members").cast(pl.Int32))


class TestNmsDedup:
    def test_sixty_percent_overlap_exactly_one_survives(self) -> None:
        """The §9.1 fixture: two alerts with member-set Jaccard 0.6 — only the
        better-ranked one survives."""
        alerts = alert_frame(
            [
                {"alert_id": "A", "rank": 1, "members": ["a", "b", "c", "d"]},
                {"alert_id": "B", "rank": 2, "members": ["a", "b", "c", "e"]},
            ]
        )
        assert jaccard({"a", "b", "c", "d"}, {"a", "b", "c", "e"}) == pytest.approx(0.6)
        result = nms_dedup(alerts)
        assert result.kept["alert_id"].to_list() == ["A"]
        assert result.report["n_suppressed"] == 1
        # the suppressed alert carries its suppressor's overlap group
        b_row = result.alerts.filter(pl.col("alert_id") == "B")
        a_row = result.alerts.filter(pl.col("alert_id") == "A")
        assert b_row["overlap_group"][0] == a_row["overlap_group"][0]

    def test_jaccard_exactly_at_threshold_is_kept(self) -> None:
        """Suppression requires STRICTLY greater than the threshold (§4.5)."""
        alerts = alert_frame(
            [
                {"alert_id": "A", "rank": 1, "members": ["a", "b", "c"]},
                {"alert_id": "B", "rank": 2, "members": ["a", "b", "d"]},  # Jaccard 0.5
            ]
        )
        assert nms_dedup(alerts).kept.height == 2

    def test_disjoint_alerts_all_survive(self) -> None:
        alerts = alert_frame(
            [
                {"alert_id": "A", "rank": 1, "members": ["a", "b"]},
                {"alert_id": "B", "rank": 2, "members": ["c", "d"]},
            ]
        )
        result = nms_dedup(alerts)
        assert result.kept.height == 2
        assert result.report["n_suppressed"] == 0

    def test_rank_order_decides_the_survivor(self) -> None:
        """The queue is rank-ascending regardless of input row order."""
        alerts = alert_frame(
            [
                {"alert_id": "worse", "rank": 9, "members": ["a", "b", "c", "d"]},
                {"alert_id": "better", "rank": 1, "members": ["a", "b", "c", "e"]},
            ]
        )
        assert nms_dedup(alerts).kept["alert_id"].to_list() == ["better"]

    def test_mega_community_excluded_by_size_cap(self) -> None:
        """§4.5: a single mega-community cannot absorb the budget."""
        alerts = alert_frame(
            [
                {"alert_id": "mega", "rank": 1, "members": [f"n{i}" for i in range(101)]},
                {"alert_id": "ok", "rank": 2, "members": ["a", "b"]},
            ]
        )
        result = nms_dedup(alerts)
        assert result.kept["alert_id"].to_list() == ["ok"]
        assert result.report["n_oversized_excluded"] == 1


def labels_frame(mapping: dict[str, str]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "node_id": list(mapping),
            "label": list(mapping.values()),
        }
    )


class TestHitRule:
    def test_one_confirmed_illicit_member_is_a_hit(self) -> None:
        alerts = alert_frame(
            [
                {"alert_id": "A", "rank": 1, "members": ["bad", "meh", "who"]},
                {"alert_id": "B", "rank": 2, "members": ["ok1", "ok2"]},
                {"alert_id": "C", "rank": 3, "members": ["who", "who2"]},  # unknowns only
            ]
        )
        labels = labels_frame({"bad": "illicit", "meh": "licit", "ok1": "licit", "ok2": "licit"})
        labeled = apply_hit_rule(alerts, labels).sort("rank")
        assert labeled["is_hit"].to_list() == [True, False, False]
        assert labeled["n_illicit_members"].to_list() == [1, 0, 0]
        # unknown members are neither hits nor confirmed (§4.3 D1)
        assert labeled["n_confirmed_members"].to_list() == [2, 2, 0]

    def test_fractional_rule_is_stricter(self) -> None:
        alerts = alert_frame(
            [{"alert_id": "A", "rank": 1, "members": ["bad", "ok1", "ok2", "ok3"]}]
        )
        labels = labels_frame({"bad": "illicit", "ok1": "licit", "ok2": "licit", "ok3": "licit"})
        assert apply_hit_rule(alerts, labels)["is_hit"][0]  # 1 of 4 confirmed
        assert not apply_hit_rule(alerts, labels, min_fraction=0.5)["is_hit"][0]
        labels2 = labels_frame({"bad": "illicit", "ok1": "illicit", "ok2": "licit", "ok3": "licit"})
        assert apply_hit_rule(alerts, labels2, min_fraction=0.5)["is_hit"][0]


# y_true/scores toy vector used across the node-level metric tests:
# positives sit at ranks 1 and 3 of the score ordering.
Y = np.array([1, 0, 1, 0, 0])
S = np.array([0.9, 0.8, 0.7, 0.6, 0.5])


class TestNodeMetrics:
    def test_precision_at_k_hand_computed(self) -> None:
        assert precision_at_k(Y, S, 1) == pytest.approx(1.0)
        assert precision_at_k(Y, S, 2) == pytest.approx(0.5)
        assert precision_at_k(Y, S, 5) == pytest.approx(0.4)

    def test_recall_at_k_hand_computed(self) -> None:
        assert recall_at_k(Y, S, 1) == pytest.approx(0.5)
        assert recall_at_k(Y, S, 3) == pytest.approx(1.0)

    def test_fpr_at_k_hand_computed(self) -> None:
        # 3 negatives total; top-2 contains one negative, top-5 all three
        assert fpr_at_k(Y, S, 2) == pytest.approx(1 / 3)
        assert fpr_at_k(Y, S, 5) == pytest.approx(1.0)

    def test_auc_pr_hand_computed_and_matches_sklearn(self) -> None:
        # AP = mean over positives of precision at their rank = (1/1 + 2/3) / 2
        result = auc_pr(Y, S)
        assert result["auc_pr"] == pytest.approx((1.0 + 2 / 3) / 2)
        assert result["auc_pr"] == pytest.approx(float(average_precision_score(Y, S)))
        assert result["prevalence_baseline"] == pytest.approx(0.4)

    def test_non_binary_truth_rejected(self) -> None:
        with pytest.raises(ValueError, match="binary"):
            precision_at_k(np.array([1, 2, 0]), np.array([0.3, 0.2, 0.1]), 1)

    def test_oversized_budget_truncates_honestly(self) -> None:
        """Audit F12: budgets beyond the scored population compute at the
        population size (mirroring alert-level k_effective), never dropped."""
        assert precision_at_k(Y, S, 6) == precision_at_k(Y, S, 5)
        with pytest.raises(ValueError, match="positive"):
            precision_at_k(Y, S, 0)

    def test_ties_scored_as_expected_value(self) -> None:
        """Audit F4: tie-heavy scorers (rules engines) must not have
        order-dependent P@k — ties at the cutoff take their expected rate."""
        y = np.array([1, 0, 0, 0, 1])
        scores = np.array([0.9, 0.5, 0.5, 0.5, 0.5])  # 4-way tie after rank 1
        # top-3 = 1 sure positive + 2 slots from a tie group with rate 1/4
        assert precision_at_k(y, scores, 3) == pytest.approx((1 + 2 * 0.25) / 3)
        # order-independence: shuffling the tied rows changes nothing
        perm = np.array([0, 4, 3, 2, 1])
        assert precision_at_k(y[perm], scores[perm], 3) == precision_at_k(y, scores, 3)
        assert recall_at_k(y, scores, 3) == pytest.approx((1 + 0.5) / 2)
        assert fpr_at_k(y, scores, 3) == pytest.approx((3 - 1.5) / 3)

    def test_unknowns_are_dropped_before_scoring(self) -> None:
        scores = pl.DataFrame({"node_id": ["a", "b", "c"], "score": [0.9, 0.8, 0.7]})
        labels = pl.DataFrame(
            {"node_id": ["a", "b", "c"], "label": ["illicit", "unknown", "licit"]}
        )
        y, s = confirmed_node_vectors(scores, labels)
        assert y.tolist() == [1, 0]
        assert s.tolist() == [0.9, 0.7]


class TestAlertQueueMetrics:
    def queue(self) -> pl.DataFrame:
        alerts = alert_frame(
            [
                {"alert_id": "A", "rank": 1, "members": ["bad1", "x"]},
                {"alert_id": "B", "rank": 2, "members": ["ok1", "ok2"]},
                {"alert_id": "C", "rank": 3, "members": ["bad2"]},
            ]
        )
        labels = labels_frame(
            {
                "bad1": "illicit",
                "bad2": "illicit",
                "bad3": "illicit",
                "ok1": "licit",
                "ok2": "licit",
            }
        )
        return apply_hit_rule(alerts, labels), labels

    def test_budget_metrics_hand_computed(self) -> None:
        labeled, _ = self.queue()
        out = alert_queue_metrics(labeled, budgets=[2, 10])
        assert out["@2"] == {
            "k_requested": 2,
            "k_effective": 2,
            "precision": 0.5,
            "false_alert_rate": 0.5,
            "n_hits": 1,
        }
        # budget larger than the queue truncates honestly
        assert out["@10"]["k_effective"] == 3
        assert out["@10"]["precision"] == pytest.approx(2 / 3)

    def test_illicit_coverage_hand_computed(self) -> None:
        labeled, labels = self.queue()
        cov = illicit_coverage_at_budget(labeled, labels, budgets=[1, 3])
        # 3 confirmed illicit nodes exist; top-1 captures bad1, top-3 adds bad2
        assert cov["@1"] == pytest.approx(1 / 3)
        assert cov["@3"] == pytest.approx(2 / 3)


class TestResolveBudgets:
    def test_mendeley_manual_resolution_reproduced(self) -> None:
        """The M1 hand-resolved budgets (ledger 2026-07-15): top 1/5/10% of the
        363-firm Mendeley test queue = 4/18/36 — the rule must reproduce them."""
        from collusiongraph.eval import resolve_budgets

        assert resolve_budgets(["1%", "5%", "10%"], 363) == [4, 18, 36]

    def test_ints_pass_through_and_tiny_percents_clamp_to_one(self) -> None:
        from collusiongraph.eval import resolve_budgets

        assert resolve_budgets([50, 100], 363) == [50, 100]
        assert resolve_budgets(["1%"], 10) == [1]  # round(0.1) clamps to 1
        assert resolve_budgets([25, "50%"], 10) == [25, 5]

    def test_malformed_budgets_rejected(self) -> None:
        from collusiongraph.eval import resolve_budgets

        with pytest.raises(ValueError, match="N%"):
            resolve_budgets(["fifty"], 100)
        with pytest.raises(ValueError, match="percent"):
            resolve_budgets(["0%"], 100)
        with pytest.raises(ValueError, match="percent"):
            resolve_budgets(["150%"], 100)


class TestRunEval:
    def _store_with_fixture(self, tmp_path) -> GraphStore:
        store = GraphStore(tmp_path / "interim")
        labels = pl.DataFrame(
            {
                "node_id": ["bad1", "bad2", "ok1", "ok2"],
                "label": ["illicit", "illicit", "licit", "licit"],
                "label_source": ["toy"] * 4,
                "confidence": [1.0] * 4,
            }
        )
        alerts = pl.DataFrame(
            {
                "alert_id": ["A", "B"],
                "domain": ["financial"] * 2,
                "dataset": ["toy"] * 2,
                "model_run_id": ["run0"] * 2,
                "rank": [1, 2],
                "risk_score": [0.9, 0.5],
                "member_node_ids": [["bad1", "ok1"], ["ok2"]],
                "n_members": [2, 1],
                "created_at": [datetime.now(UTC)] * 2,
                "caveats": [SCREENING_CAVEAT] * 2,
            }
        )
        store.write("toy", "labels", labels)
        store.write("toy", "alerts", alerts)
        return store

    def test_config_driven_run_writes_metrics_json(self, tmp_path) -> None:
        store = self._store_with_fixture(tmp_path)
        scores = pl.DataFrame(
            {"node_id": ["bad1", "bad2", "ok1", "ok2"], "score": [0.9, 0.8, 0.7, 0.1]}
        )
        scores_path = tmp_path / "scores.parquet"
        scores.write_parquet(scores_path)
        config = {
            "dataset": "toy",
            "store_root": str(store.root),
            "budgets": [1, 2],
            "node_scores": str(scores_path),
            "output_dir": str(tmp_path / "out"),
        }
        metrics = run_eval(config)
        assert (tmp_path / "out" / "metrics.json").is_file()
        assert metrics["alert_level"]["queue"]["@1"]["precision"] == 1.0
        assert metrics["alert_level"]["queue"]["@2"]["precision"] == 0.5
        assert metrics["alert_level"]["illicit_coverage"]["@2"] == pytest.approx(0.5)
        # node level: positives at score-ranks 1 and 2 -> AP = 1.0
        assert metrics["node_level"]["auc_pr"] == pytest.approx(1.0)
        assert metrics["node_level"]["prevalence_baseline"] == pytest.approx(0.5)

    def test_percent_budgets_resolve_per_level(self, tmp_path) -> None:
        """§4.5 top-% budgets: "50%" cuts half of EACH ranked list — 2-alert
        queue → @1, 4 confirmed nodes → @2 — and the resolution is recorded."""
        store = self._store_with_fixture(tmp_path)
        scores = pl.DataFrame(
            {"node_id": ["bad1", "bad2", "ok1", "ok2"], "score": [0.9, 0.8, 0.7, 0.1]}
        )
        scores_path = tmp_path / "scores.parquet"
        scores.write_parquet(scores_path)
        metrics = run_eval(
            {
                "dataset": "toy",
                "store_root": str(store.root),
                "budgets": ["50%"],
                "node_scores": str(scores_path),
                "output_dir": str(tmp_path / "out"),
            }
        )
        assert metrics["alert_level"]["queue"]["@1"]["precision"] == 1.0
        assert metrics["alert_level"]["resolved_budgets"] == {"50%": 1}
        assert metrics["node_level"]["precision@2"] == 1.0
        assert metrics["node_level"]["resolved_budgets"] == {"50%": 2}

    def test_cli_eval_runs_a_config_file(self, tmp_path, capsys) -> None:
        store = self._store_with_fixture(tmp_path)
        config_path = tmp_path / "exp.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "dataset": "toy",
                    "store_root": str(store.root),
                    "budgets": [2],
                    "output_dir": str(tmp_path / "out"),
                }
            ),
            encoding="utf-8",
        )
        assert cli_main(["eval", "-c", str(config_path)]) == 0
        assert "metrics.json" in capsys.readouterr().out
