"""Practitioner-study kit correctness (§7 step 31, §10.3, §9.1).

Krippendorff's α is hand-computed on a fixture small enough to check on paper
(the §9.1 metric-test discipline); sampling and rendering are pinned for
determinism, quota strictness, arm balance, and the ground-truth leak guard.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.eval.study import (
    build_study_packets,
    krippendorff_alpha,
    sample_study_cases,
    summarize_study,
)


def toy_bundle(alert_id: str, rank: int, motif: dict | None) -> dict:
    return {
        "alert_id": alert_id,
        "domain": "procurement",
        "dataset": "toy",
        "rank": rank,
        "risk_score": 1.0 / rank,
        "budget_position": rank,
        "minimal_subgraph": {"nodes": ["firm:M:F1"], "edges": []},
        "attention_summary": None,
        "motif": motif,
        "evidence": {"n_members": 3, "time_window": [2010, 2012]},
        "evidence_sources": {"learned": [], "structural": [], "screen": []},
        "red_flags": (
            []
            if motif is None
            else [
                {
                    "framework": "OECD",
                    "indicator_id": "OECD-BID-01",
                    "indicator_text": "identical or suspiciously close bids",
                    "matched_because": "cover_bid geometry",
                }
            ]
        ),
        "fidelity": None,
        "fidelity_sane": None,
        "caveats": SCREENING_CAVEAT,
    }


def write_bundles(tmp_path: Path, n_flagged: int, n_unflagged: int) -> Path:
    exp_dir = tmp_path / "explanations"
    exp_dir.mkdir(parents=True, exist_ok=True)
    rank = 1
    for i in range(n_flagged):
        b = toy_bundle(f"toy:alert_f{i}", rank, {"type": "cover_bid", "params": {"k": 3}})
        (exp_dir / f"f{i}.json").write_text(json.dumps(b), encoding="utf-8")
        rank += 1
    for i in range(n_unflagged):
        b = toy_bundle(f"toy:alert_u{i}", rank, None)
        (exp_dir / f"u{i}.json").write_text(json.dumps(b), encoding="utf-8")
        rank += 1
    return exp_dir


def study_cfg(tmp_path: Path, exp_dir: Path, n_f: int = 2, n_u: int = 2) -> dict:
    return {
        "seed": 0,
        "output_dir": str(tmp_path / "packets"),
        "datasets": [
            {
                "dataset": "toy",
                "explanations_dir": str(exp_dir),
                "strata": [
                    {"rule": "motif_flagged", "n": n_f},
                    {"rule": "motif_unflagged", "n": n_u},
                ],
            }
        ],
    }


class TestKrippendorffAlpha:
    def test_hand_computed_ordinal_example(self) -> None:
        """Two raters, four units: A(1,1) B(2,2) C(3,3) D(1,2).

        Coincidence matrix (each unit contributes both ordered pairs / (m−1)=1):
        o11=2, o22=2, o33=2, o12=o21=1 → marginals n1=3, n2=3, n3=2, n=8.
        Ordinal δ²: δ12²=(n1+n2−(n1+n2)/2)²=9; δ23²=(n2+n3−(n2+n3)/2)²=6.25;
        δ13²=(n1+n2+n3−(n1+n3)/2)²=30.25.
        D_o = (o12+o21)·9/8 = 2.25.
        D_e = [2·3·3·9 + 2·3·2·30.25 + 2·3·2·6.25] / (8·7) = 600/56.
        α = 1 − 2.25·56/600 = 0.79 exactly.
        """
        units = pl.DataFrame({"r1": [1, 2, 3, 1], "r2": [1, 2, 3, 2]})
        assert krippendorff_alpha(units, level="ordinal") == pytest.approx(0.79)

    def test_perfect_agreement_is_one(self) -> None:
        units = pl.DataFrame({"r1": [1, 5, 3], "r2": [1, 5, 3], "r3": [1, 5, 3]})
        assert krippendorff_alpha(units) == pytest.approx(1.0)

    def test_single_rating_units_are_excluded(self) -> None:
        """A unit only one rater saw carries no agreement information."""
        with_missing = pl.DataFrame({"r1": [1, 2, 4], "r2": [1, 2, None]})
        without = pl.DataFrame({"r1": [1, 2], "r2": [1, 2]})
        assert krippendorff_alpha(with_missing) == pytest.approx(krippendorff_alpha(without))

    def test_all_units_missing_rejected(self) -> None:
        with pytest.raises(ValueError, match="two or more"):
            krippendorff_alpha(pl.DataFrame({"r1": [1, 2], "r2": [None, None]}))

    def test_nominal_differs_from_ordinal_on_distance(self) -> None:
        """Ordinal penalizes 1-vs-5 harder than 1-vs-2; nominal cannot tell."""
        near = pl.DataFrame({"r1": [1, 3, 5, 2], "r2": [2, 3, 5, 2]})
        far = pl.DataFrame({"r1": [1, 3, 5, 2], "r2": [5, 3, 5, 2]})
        assert krippendorff_alpha(near, "ordinal") > krippendorff_alpha(far, "ordinal")


class TestSampling:
    def test_deterministic_and_quota_exact(self, tmp_path) -> None:
        exp_dir = write_bundles(tmp_path, n_flagged=4, n_unflagged=4)
        cfg = study_cfg(tmp_path, exp_dir)
        a = sample_study_cases(cfg)
        b = sample_study_cases(cfg)
        assert [c["alert_id"] for c in a] == [c["alert_id"] for c in b]
        assert sum(1 for c in a if c["stratum"] == "motif_flagged") == 2
        assert len({c["alert_id"] for c in a}) == 4  # no duplicates across strata

    def test_unmeetable_stratum_raises(self, tmp_path) -> None:
        exp_dir = write_bundles(tmp_path, n_flagged=1, n_unflagged=4)
        with pytest.raises(ValueError, match="never short-fill"):
            sample_study_cases(study_cfg(tmp_path, exp_dir, n_f=2))

    def test_arms_split_evenly_in_randomized_order(self, tmp_path) -> None:
        exp_dir = write_bundles(tmp_path, n_flagged=3, n_unflagged=3)
        cases = sample_study_cases(study_cfg(tmp_path, exp_dir, n_f=3, n_u=3))
        arms = [c["arm"] for c in sorted(cases, key=lambda c: c["case_number"])]
        assert arms.count("bundle_only") == 3
        assert arms.count("bundle_plus_copilot") == 3


class TestPackets:
    def test_end_to_end_renders_all_artifacts(self, tmp_path) -> None:
        exp_dir = write_bundles(tmp_path, n_flagged=2, n_unflagged=2)
        summary = build_study_packets(study_cfg(tmp_path, exp_dir))
        out = tmp_path / "packets"
        assert summary["n_cases"] == 4
        assert summary["per_arm"] == {"bundle_only": 2, "bundle_plus_copilot": 2}
        packets = sorted(out.glob("case_*.md"))
        assert len(packets) == 4
        text = packets[0].read_text(encoding="utf-8")
        assert SCREENING_CAVEAT in text
        assert (out / "ratings_template.csv").is_file()
        manifest = json.loads((out / "study_manifest.json").read_text(encoding="utf-8"))
        assert len(manifest["cases"]) == 4
        assert all("bundle" not in c for c in manifest["cases"])

    def test_ground_truth_vocabulary_refused(self, tmp_path) -> None:
        """§10.3 validity guard: a bundle whose text smuggles label vocabulary
        must fail the render, never reach a rater."""
        exp_dir = write_bundles(tmp_path, n_flagged=0, n_unflagged=1)
        poisoned = toy_bundle("toy:alert_p", 9, None)
        poisoned["evidence"]["note"] = "ground_truth: is_cartel=1"
        (exp_dir / "p.json").write_text(json.dumps(poisoned), encoding="utf-8")
        cfg = study_cfg(tmp_path, exp_dir, n_f=0, n_u=2)
        with pytest.raises(ValueError, match="ground-truth"):
            build_study_packets(cfg)


class TestSummary:
    def test_summary_math_and_arm_split(self, tmp_path) -> None:
        header = "rater_id,case,arm,verifiability,red_flag_alignment,actionability,notes\n"
        r1 = header + ("r1,01,bundle_only,4,5,3,\n" "r1,02,bundle_plus_copilot,2,3,1,\n")
        r2 = header + ("r2,01,bundle_only,4,5,3,\n" "r2,02,bundle_plus_copilot,2,3,2,\n")
        p1, p2 = tmp_path / "r1.csv", tmp_path / "r2.csv"
        p1.write_text(r1, encoding="utf-8")
        p2.write_text(r2, encoding="utf-8")
        report = summarize_study([p1, p2])
        assert report["n_raters"] == 2
        assert report["n_cases"] == 2
        assert report["dimensions"]["verifiability"]["mean"] == pytest.approx(3.0)
        # verifiability agrees perfectly on both units
        assert report["dimensions"]["verifiability"]["krippendorff_alpha_ordinal"] == (
            pytest.approx(1.0)
        )
        assert report["per_arm"]["bundle_only"]["actionability"] == pytest.approx(3.0)
        assert report["per_arm"]["bundle_plus_copilot"]["actionability"] == pytest.approx(1.5)
