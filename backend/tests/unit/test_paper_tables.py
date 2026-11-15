"""Paper-table builder correctness (§7 step 33, §9.1): values are copied from
fixture artifacts and formatted exactly; absent artifacts skip with a recorded
reason — never partial, never faked."""

import json
from pathlib import Path

from collusiongraph.eval.tables import build_paper_tables, regularisers, to_latex, to_markdown


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


def _tree(auc: float, sd: float, p18: float, p18_sd: float) -> dict:
    return {
        "auc_pr_mean": auc,
        "auc_pr_std": sd,
        "precision@18_mean": p18,
        "precision@18_std": p18_sd,
    }


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
        {"aggregate": {"auc_pr_mean": 0.4388, "auc_pr_std": 0.0505}},
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
        {"baselines": {"b1_rules": {"auc_pr": 0.3426, "precision@18": 0.4698}}},
    )
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/baselines_multiseed/baselines_multiseed.json",
        {"baselines": {"b2_xgb": _tree(0.3849, 0.0099, 0.2222, 0.0)}},
    )
    _write(
        tmp_path,
        "eval_outputs/mendeley_eu/baselines_screens_ablation_multiseed/baselines_multiseed.json",
        {"baselines": {"b2_xgb": _tree(0.4547, 0.0081, 0.6556, 0.0609)}},
    )
    return tmp_path


def revision_tree(tmp_path: Path) -> Path:
    """Artifacts of the journal-revision tables (items B1, B2, B5, B6, B7, B8)."""
    _write(
        tmp_path,
        "eval_outputs/derived/derived_numbers.json",
        {
            "items": {
                "gatv2_steps_35_42": {
                    "n_confirmed": 9983,
                    "prevalence": 0.0916,
                    "auc_pr_mean": 0.5737,
                    "auc_pr_std": 0.0623,
                },
                "b3_steps_35_42": {
                    "n_confirmed": 9983,
                    "prevalence": 0.0916,
                    "auc_pr_mean": 0.9259,
                    "auc_pr_std": 0.0011,
                },
                "gatv2_steps_43_49": {
                    "n_confirmed": 6687,
                    "prevalence": 0.0253,
                    "auc_pr_mean": 0.0391,
                    "auc_pr_std": 0.0041,
                },
                "b3_steps_43_49": {
                    "n_confirmed": 6687,
                    "prevalence": 0.0253,
                    "auc_pr_mean": 0.0567,
                    "auc_pr_std": 0.0034,
                },
            }
        },
    )
    _write(
        tmp_path,
        "eval_outputs/transfer_pooled/transfer_pooled.json",
        {
            "n_boot": 2000,
            "matrices": {
                "mendeley_loco": {
                    "folds": [
                        {
                            "test_group": "country_2",
                            "n_confirmed_test": 750,
                            "prevalence": 0.716,
                            "lift_mean": 0.903,
                            "lift_ci_low": 0.874,
                            "lift_ci_high": 0.939,
                        }
                    ],
                    "n_confirmed_pooled": 1001,
                    "pooled_prevalence": 0.689,
                    "pooled_lift_mean": 0.929,
                    "pooled_lift_std": 0.022,
                    "size_weighted_lift": 0.991,
                    "macro_lift": 1.170,
                }
            },
        },
    )
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/significance/significance_multiseed.json",
        {
            "n_boot": 2000,
            "comparisons": {
                "gatv2_vs_b3": {
                    "label_a": "GATv2",
                    "label_b": "B3",
                    "delta_min": -0.3908,
                    "delta_max": -0.2641,
                    "ci_low_min": -0.4156,
                    "ci_high_max": -0.2381,
                    "p_value_max": 0.0009995,
                    "seed_averaged": {
                        "delta": -0.3006,
                        "delta_ci_low": -0.3236,
                        "delta_ci_high": -0.2761,
                        "p_value": 0.0009995,
                    },
                }
            },
        },
    )
    _write(
        tmp_path,
        "eval_outputs/cross_domain/full_label_comparison/full_label_comparison.json",
        {
            "directions": {
                "proc2fin": {
                    "direction": "mendeley_eu -> elliptic_pp",
                    "prevalence_baseline": 0.065,
                    "comparators": {
                        "frozen_probe": {
                            "auc_pr_ci": {"auc_pr": 0.1502, "ci_low": 0.1354, "ci_high": 0.1686}
                        }
                    },
                    "in_domain_reference": {
                        "baseline": "b2_xgb",
                        "auc_pr_mean": 0.8039,
                        "auc_pr_std": 0.0017,
                    },
                }
            }
        },
    )
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/explainer_metrics/explainer_ablation.json",
        {
            "arms": {
                "pg_explainer": {
                    "n_nodes": 50,
                    "n_pyg_implausible": 1,
                    "n_hard_implausible": 25,
                    "hard_fidelity_plus_mean": 0.0525,
                    "hard_fidelity_minus_mean": -0.0063,
                    "sparsity_mean": 0.1198,
                    "seconds": 18.08,
                },
                "attention": {
                    "n_nodes": 50,
                    "n_hard_implausible": 28,
                    "hard_fidelity_plus_mean": 0.0486,
                    "hard_fidelity_minus_mean": -0.0005,
                    "sparsity_mean": 0.0052,
                    "seconds": 0.59,
                },
            }
        },
    )
    curve = {
        "seeds": [0, 1, 2],
        "curve": [
            {"rate": 0.0, "auc_pr_mean": 0.4827, "auc_pr_std": 0.0616, "val_auc_pr_mean": 0.9418}
        ],
    }
    _write(tmp_path, "eval_outputs/elliptic_pp/label_noise_curve/noise_curve.json", curve)
    return tmp_path


def test_ablation_deltas_are_formed_within_a_basis(tmp_path) -> None:
    ablation_tree(tmp_path)
    out = tmp_path / "paper" / "tables"
    report = build_paper_tables(root=tmp_path, out_dir=out)
    assert "ablations" in report["built"]
    md = (out / "ablations.md").read_text(encoding="utf-8")
    # multi-seed arm: Δ against the multi-seed reference, not the seed-0 one
    assert "| − focal loss (weighted CE) | 5 seeds | 0.4388 ± 0.0505 | -0.0341 |" in md
    # seed-0 arm: Δ against the seed-0 reference (the RT-1 separation)
    assert "| − bidirectional edges | seed 0 | 0.3549 | -0.1943 |" in md
    # ensemble composition: both operands copied from the one multiseed artifact
    assert "| − unsupervised members | 5 seeds | 0.4729 ± 0.0525 | +0.0295 |" in md
    # procurement arm: the five-seed tree rows (journal revision)
    assert "| + dataset screens | 5 seeds | 0.4547 ± 0.0081 | +0.0698 |" in md
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
    ablation_tree(tmp_path)  # supplies the deterministic and five-seed scoreboards
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
    assert "| b2_xgb +dataset screens | 0.4547 ± 0.0081 | 0.66 ± 0.06 |" in md
    assert "| b1_rules | 0.3426 (det.) | 0.47 |" in md
    assert "| b2_xgb | 0.3849 ± 0.0099 | 0.22 ± 0.00 |" in md
    assert "pc_* screen" in md  # the caption says what was added


def test_builds_available_and_skips_missing_with_reason(tmp_path) -> None:
    fixture_tree(tmp_path)
    report = build_paper_tables(root=tmp_path, out_dir=tmp_path / "paper" / "tables")
    assert set(report["built"]) == {"injection_ocds", "loco_mendeley", "significance_seed0"}
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
    sig_md = (out / "significance_seed0.md").read_text(encoding="utf-8")
    assert "| ensemble_calibrated vs ensemble_rank | +0.471 | [0.440, 0.499] | 0.001 |" in sig_md
    inj_md = (out / "injection_ocds.md").read_text(encoding="utf-8")
    assert "| cover_bid | 0.0000 ± 0.0000 | 0.2500 ± 0.0500 |" in inj_md
    assert "163,327" in inj_md


def test_revision_tables_copy_their_artifacts(tmp_path) -> None:
    revision_tree(tmp_path)
    out = tmp_path / "paper" / "tables"
    report = build_paper_tables(root=tmp_path, out_dir=out)
    for name in ("step43", "transfer_pooled", "significance", "full_label", "explainer_metrics"):
        assert name in report["built"], name
    step = (out / "step43.md").read_text(encoding="utf-8")
    assert "| 35–42 | 9983 | 0.092 | 0.5737 ± 0.0623 | 0.9259 ± 0.0011 |" in step
    assert "| 43–49 | 6687 | 0.025 | 0.0391 ± 0.0041 | 0.0567 ± 0.0034 |" in step
    pooled = (out / "transfer_pooled.md").read_text(encoding="utf-8")
    assert "| mendeley_loco: country_2 | 750 | 0.72 | 0.90 [0.87, 0.94] |" in pooled
    assert "| mendeley_loco: pooled | 1001 | 0.69 | 0.93 ± 0.02 |" in pooled
    assert "| mendeley_loco: size-weighted | — | — | 0.99 |" in pooled
    sig = (out / "significance.md").read_text(encoding="utf-8")
    assert "| GATv2 vs B3, seed pairs | -0.391 to -0.264 | [-0.416, -0.238] | ≤ 0.001 |" in sig
    assert "| GATv2 vs B3, seed-averaged | -0.301 | [-0.324, -0.276] | 0.001 |" in sig
    full = (out / "full_label.md").read_text(encoding="utf-8")
    assert "| mendeley_eu -> elliptic_pp | frozen_probe | 0.1502 [0.135, 0.169] | 0.065 |" in full
    assert "| mendeley_eu -> elliptic_pp | b2_xgb (5 seeds) | 0.8039 ± 0.0017 | 0.065 |" in full
    expl = (out / "explainer_metrics.md").read_text(encoding="utf-8")
    assert "| pg_explainer | 49/50 | 0.052 | -0.006 | 25/50 | 0.12 | 18.1 |" in expl
    assert "| attention | — | 0.049 | -0.001 | 22/50 | 0.01 | 0.6 |" in expl


def test_label_noise_prefers_the_five_seed_curve(tmp_path) -> None:
    revision_tree(tmp_path)
    out = tmp_path / "paper" / "tables"
    build_paper_tables(root=tmp_path, out_dir=out)
    assert "3 seeds per rate" in (out / "label_noise.md").read_text(encoding="utf-8")
    _write(
        tmp_path,
        "eval_outputs/elliptic_pp/label_noise_curve_5seed/noise_curve.json",
        {
            "seeds": [0, 1, 2, 3, 4],
            "curve": [
                {"rate": 0.0, "auc_pr_mean": 0.4729, "auc_pr_std": 0.0525, "val_auc_pr_mean": 0.94}
            ],
        },
    )
    build_paper_tables(root=tmp_path, out_dir=out)
    md = (out / "label_noise.md").read_text(encoding="utf-8")
    assert "5 seeds per rate" in md
    assert "| 0% | 0.4729 ± 0.0525 | 0.9400 |" in md


def test_regularisers_table_counts_seed_wins(tmp_path) -> None:
    base = "eval_outputs/elliptic_pp"
    clean = [0.50, 0.40, 0.45, 0.42, 0.48]

    def multiseed(tests, vals):
        return {
            "per_seed": [
                {"seed": s, "auc_pr": a, "best_val_auc_pr": v}
                for s, (a, v) in enumerate(zip(tests, vals, strict=True))
            ]
        }

    _write(
        tmp_path, f"{base}/gnn_gatv2_focal_multiseed/multiseed.json", multiseed(clean, [0.94] * 5)
    )
    _write(
        tmp_path,
        f"{base}/label_noise_curve_5seed/noise_curve.json",
        {
            "seeds": [0, 1, 2, 3, 4],
            "curve": [
                {"rate": r, "auc_pr_mean": 0.5, "auc_pr_std": 0.05, "val_auc_pr_mean": 0.9}
                for r in (0.0, 0.2)
            ],
        },
    )
    noisy = [0.60, 0.62, 0.58, 0.40, 0.61]
    for s, a in enumerate(noisy):
        _write(
            tmp_path,
            f"{base}/label_noise_curve_5seed/rate_0.2_seed_{s}/run.json",
            {"node_level": {"auc_pr": a}, "best_val_auc_pr": 0.57},
        )
    for folder in ("ls", "wd", "do", "es", "valwin"):
        _write(
            tmp_path,
            f"{base}/gnn_gatv2_focal_{folder}_multiseed/multiseed.json",
            multiseed([c - 0.01 for c in clean], [0.93] * 5),
        )
    # the builder alone: the minimal fixture does not feed the other tables
    md = to_markdown(*regularisers(tmp_path))
    assert "| Clean labels (headline) | 0.4500 ± 0.0412 | 0.9400 ± 0.0000 | — |" in md
    assert "| Label noise 20% | 0.5620 ± 0.0918 | 0.5700 ± 0.0000 | 4/5 |" in md
    assert "| Dropout 0.5 | 0.4400 ± 0.0412 | 0.9300 ± 0.0000 | 0/5 |" in md


def test_regularisers_table_skips_while_an_arm_is_missing(tmp_path) -> None:
    revision_tree(tmp_path)
    report = build_paper_tables(root=tmp_path, out_dir=tmp_path / "paper" / "tables")
    assert "regularisers" in report["skipped"]


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
