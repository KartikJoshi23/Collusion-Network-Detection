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


def test_markdown_shape() -> None:
    md = to_markdown(["A", "B"], [["x", "y"]], "cap")
    lines = md.splitlines()
    assert lines[0] == "*cap*"
    assert lines[2] == "| A | B |"
    assert lines[3] == "|---|---|"
    assert lines[4] == "| x | y |"
