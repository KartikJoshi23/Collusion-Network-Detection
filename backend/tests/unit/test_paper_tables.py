"""Paper-table builder correctness (§7 step 33, §9.1): values are copied from
fixture artifacts and formatted exactly; absent artifacts skip with a recorded
reason — never partial, never faked."""

import json
from pathlib import Path

from collusiongraph.eval.tables import build_paper_tables, to_latex, to_markdown


def _write(root: Path, rel: str, payload: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def fixture_tree(tmp_path: Path) -> Path:
    _write(
        tmp_path,
        "eval_outputs/ocds_georgia/injection_recovery_multiseed/injection_multiseed.json",
        {
            "population": 163327,
            "seeds": [0, 1],
            "fusion_mode": "rank_unlabeled",
            "recovery_multiseed": {
                "floor": {
                    "cover_bid": {
                        "n_members": 120,
                        "recall@2000": {"mean": 0.0, "std": 0.0, "values": {"0": 0, "1": 0}},
                    }
                },
                "gae": {
                    "cover_bid": {
                        "n_members": 120,
                        "recall@2000": {"mean": 0.25, "std": 0.05, "values": {"0": 0.2, "1": 0.3}},
                    }
                },
            },
        },
    )
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/transfer_loco_matrix/matrix.json",
        {
            "folds": [
                {
                    "test_group": "country_5",
                    "status": "completed",
                    "n_confirmed_test": 60,
                    "prevalence_baseline": 0.667,
                    "auc_pr_mean": 0.7625,
                    "auc_pr_std": 0.047,
                    "lift_mean": 1.14,
                },
                {"test_group": "country_9", "status": "skipped_no_val_group"},
            ],
            "summary": {"macro_lift_mean": 1.17},
        },
    )
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/significance/significance.json",
        {
            "comparisons": {
                "cal_vs_rank": {
                    "label_a": "ensemble_calibrated",
                    "label_b": "ensemble_rank",
                    "auc_pr_a": 0.5246,
                    "auc_pr_b": 0.0535,
                    "delta": 0.4711,
                    "delta_ci_low": 0.4400,
                    "delta_ci_high": 0.4990,
                    "p_value": 0.001,
                }
            }
        },
    )
    return tmp_path


def ablation_tree(tmp_path: Path) -> Path:
    """Minimal artifact set for the component-ablation table (§7 step 32)."""
    for run_dir, auc in [
        ("gnn_gatv2_focal", 0.5492),
        ("gnn_gatv2_focal_unidir", 0.3549),
        ("gnn_gatv2_focal_multi", 0.3781),
        ("gnn_gatv2_focal_line", 0.4986),
        ("gnn_gatv2_focal_cf", 0.4501),
    ]:
        _write(
            tmp_path,
            f"eval_outputs/elliptic_pp/{run_dir}/run.json",
            {"node_level": {"auc_pr": auc}},
        )
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/gnn_gatv2_focal_multiseed/multiseed.json",
        {"aggregate": {"auc_pr_mean": 0.4729, "auc_pr_std": 0.0525}},
    )
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/gnn_gatv2_wce_multiseed/multiseed.json",
        {"aggregate": {"auc_pr_mean": 0.4435, "auc_pr_std": 0.0615}},
    )
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/ensemble_multiseed/ensemble_multiseed.json",
        {
            "members": {
                "ensemble_calibrated": {"auc_pr_mean": 0.4434, "auc_pr_std": 0.0501},
                "supervised": {"auc_pr_mean": 0.4729, "auc_pr_std": 0.0525},
            }
        },
    )
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/baselines/scoreboard.json",
        {"baselines": {"b2_xgb": {"auc_pr": 0.3925, "precision@18": 0.2222}}},
    )
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/baselines_screens_ablation/scoreboard.json",
        {"baselines": {"b2_xgb": {"auc_pr": 0.4558, "precision@18": 0.6111}}},
    )
    return tmp_path


def test_ablation_deltas_are_formed_within_a_basis(tmp_path) -> None:
    ablation_tree(tmp_path)
    out = tmp_path / "paper" / "tables"
    report = build_paper_tables(root=tmp_path, out_dir=out)
    assert "ablations" in report["built"]
    md = (out / "ablations.md").read_text(encoding="utf-8")
    # multi-seed arm: Δ against the multi-seed reference, not the seed-0 one
    assert "| − focal loss (weighted CE) | 5 seeds | 0.4435 ± 0.0615 | -0.0294 |" in md
    # seed-0 arm: Δ against the seed-0 reference (the RT-1 separation)
    assert "| − bidirectional edges | seed 0 | 0.3549 | -0.1943 |" in md
    # ensemble composition: both operands copied from the one multiseed artifact
    assert "| − unsupervised members | 5 seeds | 0.4729 ± 0.0525 | +0.0295 |" in md
    # deterministic procurement arm
    assert "| + dataset screens | deterministic | 0.4558 | +0.0633 |" in md
    # every basis block opens with its own reference row
    assert md.count("| reference |") == 4


def test_ablation_table_skips_whole_when_one_arm_is_absent(tmp_path) -> None:
    ablation_tree(tmp_path)
    (tmp_path / "eval_outputs/elliptic_pp/gnn_gatv2_focal_line/run.json").unlink()
    out = tmp_path / "paper" / "tables"
    report = build_paper_tables(root=tmp_path, out_dir=out)
    assert "ablations" in report["skipped"]
    assert "gnn_gatv2_focal_line/run.json" in report["skipped"]["ablations"]
    assert not (out / "ablations.md").exists()


def test_mendeley_screens_rows_name_the_mechanism_not_the_baseline(tmp_path) -> None:
    """b4_screens is already the structural screen composite, so a bare '+screens'
    suffix renders 'b4_screens +screens' — a reviewer reads that as a duplication.
    The suffix must name what is actually added: the publisher's pc_* columns."""
    ablation_tree(tmp_path)  # supplies baselines + screens_ablation scoreboards
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/baselines_b4_precomputed/scoreboard.json",
        {"baselines": {"b4_screens": {"auc_pr": 0.3874, "precision@18": 0.5}}},
    )
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/gnn_rgcn_focal_multiseed/multiseed.json",
        {
            "aggregate": {
                "auc_pr_mean": 0.2808,
                "auc_pr_std": 0.0087,
                "precision@18_mean": 0.0746,
                "precision@18_std": 0.0363,
            }
        },
    )
    out = tmp_path / "paper" / "tables"
    build_paper_tables(root=tmp_path, out_dir=out)
    md = (out / "mendeley_headline.md").read_text(encoding="utf-8")
    assert "b4_screens +screens" not in md
    assert "| b4_screens +dataset screens | 0.3874 (det.) | 0.50 |" in md
    assert "| b2_xgb +dataset screens | 0.4558 (det.) | 0.61 |" in md
    assert "pc_* screen" in md  # the caption says what was added


def test_builds_available_and_skips_missing_with_reason(tmp_path) -> None:
    fixture_tree(tmp_path)
    report = build_paper_tables(root=tmp_path, out_dir=tmp_path / "paper" / "tables")
    assert set(report["built"]) == {"injection_ocds", "loco_mendeley", "significance"}
    # everything else is skipped with the missing artifact path recorded
    assert "elliptic_headline" in report["skipped"]
    assert "missing artifact" in report["skipped"]["elliptic_headline"]
    for name in report["built"]:
        assert (tmp_path / "paper" / "tables" / f"{name}.md").is_file()
        assert (tmp_path / "paper" / "tables" / f"{name}.tex").is_file()
    for name in report["skipped"]:
        assert not (tmp_path / "paper" / "tables" / f"{name}.md").exists()
    on_disk = json.loads(
        (tmp_path / "paper" / "tables" / "BUILD_REPORT.json").read_text(encoding="utf-8")
    )
    assert on_disk == report


def test_values_are_copied_and_formatted_exactly(tmp_path) -> None:
    fixture_tree(tmp_path)
    out = tmp_path / "paper" / "tables"
    build_paper_tables(root=tmp_path, out_dir=out)
    matrix_md = (out / "loco_mendeley.md").read_text(encoding="utf-8")
    assert "| country_5 | 60 | 0.667 | 0.7625 ± 0.0470 | 1.14 |" in matrix_md
    assert "skipped_no_val_group" in matrix_md  # incomplete folds shown, not dropped
    assert "Macro lift 1.17." in matrix_md
    sig_md = (out / "significance.md").read_text(encoding="utf-8")
    assert "| ensemble_calibrated vs ensemble_rank | +0.471 | [0.440, 0.499] | 0.001 |" in sig_md
    inj_md = (out / "injection_ocds.md").read_text(encoding="utf-8")
    assert "| cover_bid | 0.0000 ± 0.0000 | 0.2500 ± 0.0500 |" in inj_md
    assert "163,327" in inj_md


def test_latex_escapes_and_structure() -> None:
    tex = to_latex(
        ["Model", "Δ AUC-PR"],
        [["ensemble_rank", "0.05 ± 0.01"]],
        "50% of a_b → done",
    )
    assert r"ensemble\_rank" in tex
    assert r"$\pm$" in tex
    assert r"$\Delta$" in tex
    assert r"50\% of a\_b $\to$ done" in tex
    assert tex.count(r"\toprule") == 1 and tex.count(r"\bottomrule") == 1
    # U+2212 opens every ablation arm label and is not a LaTeX-safe character
    assert r"$-$ focal loss" in to_latex(["A"], [["− focal loss"]], "cap")


def test_markdown_shape() -> None:
    md = to_markdown(["A", "B"], [["x", "y"]], "cap")
    lines = md.splitlines()
    assert lines[0] == "*cap*"
    assert lines[2] == "| A | B |"
    assert lines[3] == "|---|---|"
    assert lines[4] == "| x | y |"
