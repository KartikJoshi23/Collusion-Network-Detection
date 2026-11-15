"""Paper tables from harness artifacts (§7 step 33, M8; journal revision).

Every table is COPIED from a stored eval artifact — the harness is the single
source of truth; nothing here re-derives a number (the same rule the frontend
rigor panel follows). A table whose source artifact is absent on this machine
is SKIPPED with the missing path recorded in the build report — never rendered
from partial data, never faked.

Run: ``uv run poe paper-tables`` (writes ``paper/tables/<name>.{md,tex}`` +
``BUILD_REPORT.json``; the directory is gitignored — artifacts are per-machine,
so the run for the paper happens on the machine holding the current campaign
artifacts).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

Row = list[str]
Table = tuple[list[str], list[Row], str]  # headers, rows, caption


def _load(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(rel)
    return json.loads(path.read_text(encoding="utf-8"))


def _ms(mean: float, std: float) -> str:
    return f"{mean:.4f} ± {std:.4f}"


def _ms2(mean: float, std: float) -> str:
    return f"{mean:.2f} ± {std:.2f}"


def _multiseed_row(payload: dict[str, Any], label: str, k: int) -> Row:
    agg = payload["aggregate"]
    return [
        label,
        _ms(agg["auc_pr_mean"], agg["auc_pr_std"]),
        _ms(agg[f"precision@{k}_mean"], agg[f"precision@{k}_std"]),
    ]


def _tree_rows(payload: dict[str, Any], suffix: str, k: int) -> list[Row]:
    """Five-seed tree rows from a baselines_multiseed artifact."""
    return [
        [
            name + suffix,
            _ms(m["auc_pr_mean"], m["auc_pr_std"]),
            _ms2(m[f"precision@{k}_mean"], m[f"precision@{k}_std"]),
        ]
        for name, m in sorted(payload["baselines"].items())
    ]


def elliptic_headline(root: Path) -> Table:
    sb = _load(root, "eval_outputs/elliptic_pp/baselines/scoreboard.json")["baselines"]
    b1 = sb["b1_rules"]
    rows: list[Row] = [["b1_rules", f"{b1['auc_pr']:.4f} (det.)", f"{b1['precision@100']:.2f}"]]
    rows += _tree_rows(
        _load(root, "eval_outputs/elliptic_pp/baselines_local_multiseed/baselines_multiseed.json"),
        ", local",
        100,
    )
    rows += _tree_rows(
        _load(root, "eval_outputs/elliptic_pp/baselines_multiseed/baselines_multiseed.json"),
        "",
        100,
    )
    rows.append(
        _multiseed_row(
            _load(root, "eval_outputs/elliptic_pp/gnn_gatv2_focal_multiseed/multiseed.json"),
            "gatv2_focal (5 seeds)",
            100,
        )
    )
    rows.append(
        _multiseed_row(
            _load(root, "eval_outputs/elliptic_pp/gnn_gatv2_wce_multiseed/multiseed.json"),
            "gatv2_weighted_ce (5 seeds)",
            100,
        )
    )
    ens = _load(root, "eval_outputs/elliptic_pp/ensemble_multiseed/ensemble_multiseed.json")
    for name, m in sorted(ens["members"].items()):
        rows.append([f"{name} (5 seeds)", _ms(m["auc_pr_mean"], m["auc_pr_std"]), "—"])
    return (
        ["Model", "AUC-PR", "P@100"],
        rows,
        "Elliptic++ node-level results (test steps 35–49, prevalence 0.065). The rule "
        "baseline is deterministic; tree, GNN and ensemble rows are 5-seed mean ± std. "
        "'local' rows use only the 94 local columns.",
    )


def mendeley_headline(root: Path) -> Table:
    # " +dataset screens" = the publisher's OWN precomputed pc_* screens added to
    # that baseline's inputs. Not to be confused with b4_screens, whose name refers
    # to its structural screen composite (n_awards / market_share / buyer_hhi) —
    # "b4_screens +screens" would read as a duplication.
    sb = _load(root, "eval_outputs/mendeley_eu/baselines/scoreboard.json")["baselines"]
    rows: list[Row] = [
        [name, f"{sb[name]['auc_pr']:.4f} (det.)", f"{sb[name]['precision@18']:.2f}"]
        for name in ("b1_rules", "b4_screens")
        if name in sb
    ]
    rows += _tree_rows(
        _load(root, "eval_outputs/mendeley_eu/baselines_multiseed/baselines_multiseed.json"),
        "",
        18,
    )
    rows += _tree_rows(
        _load(
            root,
            "eval_outputs/mendeley_eu/baselines_screens_ablation_multiseed/baselines_multiseed.json",
        ),
        " +dataset screens",
        18,
    )
    b4s = _load(root, "eval_outputs/mendeley_eu/baselines_b4_precomputed/scoreboard.json")[
        "baselines"
    ]
    rows += [
        [name + " +dataset screens", f"{m['auc_pr']:.4f} (det.)", f"{m['precision@18']:.2f}"]
        for name, m in sorted(b4s.items())
    ]
    rows.append(
        _multiseed_row(
            _load(root, "eval_outputs/mendeley_eu/gnn_rgcn_focal_multiseed/multiseed.json"),
            "rgcn_focal (5 seeds)",
            18,
        )
    )
    return (
        ["Model", "AUC-PR", "P@18"],
        rows,
        "Mendeley EU firm-level results (within case-control sample, prevalence 0.358). "
        "Lift-style reading applies; see the datasheet for the sample caveat. Rule and "
        "screen rows are deterministic; tree and R-GCN rows are 5-seed mean ± std. "
        "'+dataset screens' rows add the publisher's own precomputed pc_* screen "
        "columns to that baseline's inputs.",
    )


def _matrix_table(root: Path, rel: str, caption: str) -> Table:
    payload = _load(root, rel)
    rows: list[Row] = []
    for f in payload["folds"]:
        if f.get("status") != "completed":
            rows.append([str(f.get("test_group", "?")), "—", "—", "—", str(f.get("status"))])
            continue
        rows.append(
            [
                str(f["test_group"]),
                str(f.get("n_confirmed_test", "?")),
                f"{f['prevalence_baseline']:.3f}",
                _ms(f["auc_pr_mean"], f.get("auc_pr_std", 0.0)),
                f"{f['lift_mean']:.2f}",
            ]
        )
    macro = payload.get("summary", {}).get("macro_lift_mean")
    if macro is not None:
        caption += f" Macro lift {macro:.2f}."
    return (["Held-out fold", "n", "Prevalence", "AUC-PR", "Lift"], rows, caption)


def loco_mendeley(root: Path) -> Table:
    return _matrix_table(
        root,
        "eval_outputs/mendeley_eu/transfer_loco_matrix/matrix.json",
        "Mendeley LOCO transfer matrix (7 folds × 5 seeds).",
    )


def lomo_garcia(root: Path) -> Table:
    return _matrix_table(
        root,
        "eval_outputs/garcia_rodriguez/transfer_lomo_matrix/matrix.json",
        "García LOMO transfer matrix (4 markets × 5 seeds).",
    )


def transfer_pooled(root: Path) -> Table:
    """Revision item B5: per-fold lift with bootstrap CIs, pooled and size-weighted."""
    payload = _load(root, "eval_outputs/transfer_pooled/transfer_pooled.json")
    rows: list[Row] = []
    for key, matrix in payload["matrices"].items():
        for f in matrix["folds"]:
            rows.append(
                [
                    f"{key}: {f['test_group']}",
                    str(f["n_confirmed_test"]),
                    f"{f['prevalence']:.2f}",
                    f"{f['lift_mean']:.2f} [{f['lift_ci_low']:.2f}, {f['lift_ci_high']:.2f}]",
                ]
            )
        rows.append(
            [
                f"{key}: pooled",
                str(matrix["n_confirmed_pooled"]),
                f"{matrix['pooled_prevalence']:.2f}",
                _ms2(matrix["pooled_lift_mean"], matrix["pooled_lift_std"]),
            ]
        )
        rows.append([f"{key}: size-weighted", "—", "—", f"{matrix['size_weighted_lift']:.2f}"])
        rows.append([f"{key}: macro", "—", "—", f"{matrix['macro_lift']:.2f}"])
    return (
        ["Fold", "n", "Prevalence", "Lift [95% CI]"],
        rows,
        "Transfer lift by held-out fold with stratified bootstrap 95% CIs on the "
        f"seed-averaged scores ({payload['n_boot']} resamples); pooled rows score all "
        "held-out firms together (mean ± std over seeds).",
    )


def significance(root: Path) -> Table:
    """Revision item B2: per-seed-pair range and seed-averaged comparison."""
    payload = _load(root, "eval_outputs/elliptic_pp/significance/significance_multiseed.json")
    rows: list[Row] = []
    for c in payload["comparisons"].values():
        name = f"{c['label_a']} vs {c['label_b']}"
        rows.append(
            [
                f"{name}, seed pairs",
                f"{c['delta_min']:+.3f} to {c['delta_max']:+.3f}",
                f"[{c['ci_low_min']:.3f}, {c['ci_high_max']:.3f}]",
                f"≤ {c['p_value_max']:.3f}",
            ]
        )
        avg = c["seed_averaged"]
        rows.append(
            [
                f"{name}, seed-averaged",
                f"{avg['delta']:+.3f}",
                f"[{avg['delta_ci_low']:.3f}, {avg['delta_ci_high']:.3f}]",
                f"{avg['p_value']:.3f}",
            ]
        )
    return (
        ["Comparison", "Δ AUC-PR", "95% CI", "p"],
        rows,
        "Paired-bootstrap comparisons over identical confirmed test nodes "
        f"({payload['n_boot']} resamples, stratified). 'Seed pairs' rows give the range of "
        "the per-seed deltas and the envelope of their intervals; 'seed-averaged' rows "
        "compare scores averaged over the seeds.",
    )


def significance_seed0(root: Path) -> Table:
    payload = _load(root, "eval_outputs/elliptic_pp/significance/significance.json")
    rows = [
        [
            f"{c['label_a']} vs {c['label_b']}",
            f"{c['delta']:+.3f}",
            f"[{c['delta_ci_low']:.3f}, {c['delta_ci_high']:.3f}]",
            f"{c['p_value']:.3f}",
        ]
        for c in payload["comparisons"].values()
    ]
    return (
        ["Comparison", "Δ AUC-PR", "95% CI", "p"],
        rows,
        "Paired-bootstrap comparisons over identical confirmed test nodes "
        "(2,000 resamples, stratified; seed-0 score files — deltas measure "
        "sampling uncertainty at fixed seed and do not equal differences of "
        "multi-seed means).",
    )


def step43(root: Path) -> Table:
    """Revision item B1: AUC-PR before and after the step-43 market closure."""
    items = _load(root, "eval_outputs/derived/derived_numbers.json")["items"]
    rows: list[Row] = []
    for window in ("35_42", "43_49"):
        g, b = items[f"gatv2_steps_{window}"], items[f"b3_steps_{window}"]
        rows.append(
            [
                window.replace("_", "–"),
                str(g["n_confirmed"]),
                f"{g['prevalence']:.3f}",
                _ms(g["auc_pr_mean"], g["auc_pr_std"]),
                _ms(b["auc_pr_mean"], b["auc_pr_std"]),
            ]
        )
    return (
        ["Steps", "n", "Prevalence", "GATv2-focal", "B3"],
        rows,
        "AUC-PR before and after the step-43 market closure (5 seeds, mean ± std).",
    )


def full_label(root: Path) -> Table:
    """Revision item B6: cross-domain probes at full labels."""
    payload = _load(
        root, "eval_outputs/cross_domain/full_label_comparison/full_label_comparison.json"
    )
    rows: list[Row] = []
    for d in payload["directions"].values():
        for comp, c in d["comparators"].items():
            ci = c["auc_pr_ci"]
            rows.append(
                [
                    d["direction"],
                    comp,
                    f"{ci['auc_pr']:.4f} [{ci['ci_low']:.3f}, {ci['ci_high']:.3f}]",
                    f"{d['prevalence_baseline']:.3f}",
                ]
            )
        ref = d.get("in_domain_reference")
        if ref:
            rows.append(
                [
                    d["direction"],
                    f"{ref['baseline']} (5 seeds)",
                    _ms(ref["auc_pr_mean"], ref["auc_pr_std"]),
                    f"{d['prevalence_baseline']:.3f}",
                ]
            )
    return (
        ["Direction", "Model", "AUC-PR [95% CI]", "Prevalence"],
        rows,
        "Cross-domain probes at full labels, on the published probe pools; frozen "
        "probes use the stored source encoders.",
    )


def explainer_metrics(root: Path) -> Table:
    """Revision item B8: standard explainer metrics on the rebuilt queue."""
    payload = _load(root, "eval_outputs/elliptic_pp/explainer_metrics/explainer_ablation.json")
    rows: list[Row] = []
    for arm, s in payload["arms"].items():
        n = s["n_nodes"]
        pyg = f"{n - s['n_pyg_implausible']}/{n}" if "n_pyg_implausible" in s else "—"
        rows.append(
            [
                arm,
                pyg,
                f"{s['hard_fidelity_plus_mean']:.3f}",
                f"{s['hard_fidelity_minus_mean']:.3f}",
                f"{n - s['n_hard_implausible']}/{n}",
                f"{s['sparsity_mean']:.2f}",
                f"{s['seconds']:.1f}",
            ]
        )
    return (
        ["Arm", "PyG sane", "Fid+", "Fid−", "Hard sane", "Sparsity", "Seconds"],
        rows,
        "Explainer metrics on the top members of the highest-ranked financial alerts.",
    )


def label_noise(root: Path) -> Table:
    """The five-seed curve once its run has finished; the three-seed curve until then."""
    try:
        payload = _load(root, "eval_outputs/elliptic_pp/label_noise_curve_5seed/noise_curve.json")
    except FileNotFoundError:
        payload = _load(root, "eval_outputs/elliptic_pp/label_noise_curve/noise_curve.json")
    rows = [
        [
            f"{c['rate']:.0%}",
            _ms(c["auc_pr_mean"], c["auc_pr_std"]),
            f"{c['val_auc_pr_mean']:.4f}",
        ]
        for c in sorted(payload["curve"], key=lambda c: c["rate"])
    ]
    return (
        ["Train-label flip rate", "Test AUC-PR", "Validation AUC-PR"],
        rows,
        f"Label-noise robustness (GATv2-focal, {len(payload['seeds'])} seeds per rate).",
    )


_REGULARISER_ARMS = (
    ("Label smoothing, ε = 0.1", "gnn_gatv2_focal_ls_multiseed"),
    ("Weight decay 5e-3", "gnn_gatv2_focal_wd_multiseed"),
    ("Dropout 0.5", "gnn_gatv2_focal_do_multiseed"),
    ("Early-stopping patience 5", "gnn_gatv2_focal_es_multiseed"),
    ("Validation on steps 32–34", "gnn_gatv2_focal_valwin_multiseed"),
)


def regularisers(root: Path) -> Table:
    """Revision item B7: label noise against explicit regularisers, five seeds each.

    The clean row is the headline campaign. Every other row changes one
    setting; the last column counts seeds whose test AUC-PR beats the clean
    run of the same seed."""
    from statistics import mean, stdev

    base = "eval_outputs/elliptic_pp"
    # load every artifact first, so a missing one skips the table before any row
    clean = _load(root, f"{base}/gnn_gatv2_focal_multiseed/multiseed.json")
    curve = _load(root, f"{base}/label_noise_curve_5seed/noise_curve.json")
    noisy = {
        point["rate"]: [
            (
                s,
                _load(
                    root, f"{base}/label_noise_curve_5seed/rate_{point['rate']}_seed_{s}/run.json"
                ),
            )
            for s in curve["seeds"]
        ]
        for point in curve["curve"]
        if point["rate"] != 0.0
    }
    arms = [(label, _load(root, f"{base}/{d}/multiseed.json")) for label, d in _REGULARISER_ARMS]
    clean_test = {r["seed"]: r["auc_pr"] for r in clean["per_seed"]}

    def row(label: str, runs: list[tuple[int, float, float]], compare: bool = True) -> Row:
        tests = [t for _, t, _ in runs]
        vals = [v for _, _, v in runs]
        above = sum(t > clean_test[s] for s, t, _ in runs)
        return [
            label,
            _ms(mean(tests), stdev(tests)),
            _ms(mean(vals), stdev(vals)),
            f"{above}/{len(runs)}" if compare else "—",
        ]

    def per_seed(payload: dict[str, Any]) -> list[tuple[int, float, float]]:
        return [(r["seed"], r["auc_pr"], r["best_val_auc_pr"]) for r in payload["per_seed"]]

    rows = [row("Clean labels (headline)", per_seed(clean), compare=False)]
    for rate in sorted(noisy):
        runs = [(s, r["node_level"]["auc_pr"], r["best_val_auc_pr"]) for s, r in noisy[rate]]
        rows.append(row(f"Label noise {rate:.0%}", runs))
    rows += [row(label, per_seed(payload)) for label, payload in arms]
    return (
        ["Arm", "Test AUC-PR", "Validation AUC-PR", "Seeds above clean"],
        rows,
        "Label noise against explicit regularisers (GATv2-focal on Elliptic++, five seeds, "
        "mean ± SD). Each arm changes one setting of the headline run. The last column counts "
        "seeds whose test AUC-PR beats the clean run of the same seed. The window arm "
        "validates on steps 32–34, so its validation column is not comparable.",
    )


def injection_ocds(root: Path) -> Table:
    payload = _load(
        root, "eval_outputs/ocds_georgia/injection_recovery_multiseed/injection_multiseed.json"
    )
    recovery = payload["recovery_multiseed"]
    arms = sorted(recovery)
    motifs = sorted({m for arm in arms for m in recovery[arm]})
    rows = []
    for motif in motifs:
        row = [motif]
        for arm in arms:
            entry = recovery[arm].get(motif, {}).get("recall@2000")
            row.append(_ms(entry["mean"], entry["std"]) if entry else "—")
        rows.append(row)
    return (
        ["Motif family", *arms],
        rows,
        f"Injected-member recall@2000 on OCDS Georgia (population {payload['population']:,}; "
        f"{len(payload['seeds'])} seeds; fusion mode {payload['fusion_mode']}).",
    )


def _label_efficiency_table(root: Path, rel: str, caption: str) -> Table:
    payload = _load(root, rel)
    rows = [
        [
            str(c["k"]),
            f"{c['source_probe_auc_pr_mean']:.4f}",
            f"{c['transfer_gain_mean']:+.4f}",
        ]
        for c in payload["curve"]
        if c.get("status", "completed") == "completed"
    ]
    ref = payload.get("full_label_reference")
    if ref:
        caption += (
            f" Full-pool reference: source probe {ref['source_probe_auc_pr']:.4f} "
            f"vs raw probe {ref['raw_probe_auc_pr']:.4f}."
        )
    return (["Target labels k", "Source-probe AUC-PR", "Transfer gain"], rows, caption)


def label_efficiency_proc2fin(root: Path) -> Table:
    return _label_efficiency_table(
        root,
        "eval_outputs/cross_domain/label_efficiency_proc2fin/label_efficiency.json",
        "Cross-domain label efficiency, procurement→financial.",
    )


_SEED0_ARMS = [
    ("gnn_gatv2_focal_unidir", "− bidirectional edges"),
    ("gnn_gatv2_focal_multi", "+ raw+structural channels"),
    ("gnn_gatv2_focal_line", "+ line-graph channel"),
    ("gnn_gatv2_focal_cf", "+ context-fusion arm"),
]


def _run_auc_pr(root: Path, run_dir: str) -> float:
    payload = _load(root, f"eval_outputs/elliptic_pp/{run_dir}/run.json")
    return float(payload["node_level"]["auc_pr"])


def ablations(root: Path) -> Table:
    """The component-ablation table (§7 step 32).

    Each block opens with its own reference row and every Δ is formed against
    THAT reference — never across bases. This is the RT-1 discipline applied
    structurally: a seed-0 delta is a single-seed comparison and is not the
    difference of two multi-seed means, so the two never share a reference.
    Both operands of every Δ are printed in the table, so each one is
    checkable against the artifacts it was copied from.
    """
    rows: list[Row] = []

    ref_ms = _load(root, "eval_outputs/elliptic_pp/gnn_gatv2_focal_multiseed/multiseed.json")[
        "aggregate"
    ]
    ref_mean = ref_ms["auc_pr_mean"]
    rows.append(
        ["GATv2-focal (headline)", "5 seeds", _ms(ref_mean, ref_ms["auc_pr_std"]), "reference"]
    )
    wce = _load(root, "eval_outputs/elliptic_pp/gnn_gatv2_wce_multiseed/multiseed.json")[
        "aggregate"
    ]
    rows.append(
        [
            "− focal loss (weighted CE)",
            "5 seeds",
            _ms(wce["auc_pr_mean"], wce["auc_pr_std"]),
            f"{wce['auc_pr_mean'] - ref_mean:+.4f}",
        ]
    )

    # Ensemble composition — both operands live in the one multiseed artifact.
    ens = _load(root, "eval_outputs/elliptic_pp/ensemble_multiseed/ensemble_multiseed.json")[
        "members"
    ]
    cal, sup = ens["ensemble_calibrated"], ens["supervised"]
    rows.append(
        [
            "Calibrated ensemble",
            "5 seeds",
            _ms(cal["auc_pr_mean"], cal["auc_pr_std"]),
            "reference",
        ]
    )
    rows.append(
        [
            "− unsupervised members",
            "5 seeds",
            _ms(sup["auc_pr_mean"], sup["auc_pr_std"]),
            f"{sup['auc_pr_mean'] - cal['auc_pr_mean']:+.4f}",
        ]
    )

    ref0 = _run_auc_pr(root, "gnn_gatv2_focal")
    rows.append(["GATv2-focal (headline)", "seed 0", f"{ref0:.4f}", "reference"])
    for run_dir, label in _SEED0_ARMS:
        value = _run_auc_pr(root, run_dir)
        rows.append([label, "seed 0", f"{value:.4f}", f"{value - ref0:+.4f}"])

    # journal revision: the procurement arm compares the five-seed tree rows
    b2 = _load(root, "eval_outputs/mendeley_eu/baselines_multiseed/baselines_multiseed.json")[
        "baselines"
    ]["b2_xgb"]
    b2s = _load(
        root,
        "eval_outputs/mendeley_eu/baselines_screens_ablation_multiseed/baselines_multiseed.json",
    )["baselines"]["b2_xgb"]
    rows.append(
        ["Mendeley B2 XGBoost", "5 seeds", _ms(b2["auc_pr_mean"], b2["auc_pr_std"]), "reference"]
    )
    rows.append(
        [
            "+ dataset screens",
            "5 seeds",
            _ms(b2s["auc_pr_mean"], b2s["auc_pr_std"]),
            f"{b2s['auc_pr_mean'] - b2['auc_pr_mean']:+.4f}",
        ]
    )

    return (
        ["Ablation arm", "Basis", "AUC-PR", "Δ vs reference"],
        rows,
        "Component ablations on Elliptic++ (test steps 35–49) plus the Mendeley EU "
        "feature arm. A '−' row REMOVES a component of the adopted model, so its Δ is an "
        "ablation cost; a '+' row ADDS a variant that was evaluated and NOT adopted, so "
        "its Δ is a rejection margin — the two are not comparable, and only '−' rows "
        "support a 'strongest component' claim. Δ is measured against the reference row "
        "of the SAME basis: seed-0 deltas are single-seed comparisons and are NOT "
        "differences of multi-seed means. Ensemble rows read both operands from the "
        "multi-seed ensemble artifact, where removing the unsupervised members leaves the "
        "supervised member's ranking (per-member isotonic calibration is monotone).",
    )


def label_efficiency_fin2proc(root: Path) -> Table:
    return _label_efficiency_table(
        root,
        "eval_outputs/cross_domain/label_efficiency_fin2proc/label_efficiency.json",
        "Cross-domain label efficiency, financial→procurement.",
    )


TABLES: dict[str, Callable[[Path], Table]] = {
    "elliptic_headline": elliptic_headline,
    "mendeley_headline": mendeley_headline,
    "loco_mendeley": loco_mendeley,
    "lomo_garcia": lomo_garcia,
    "transfer_pooled": transfer_pooled,
    "significance": significance,
    "significance_seed0": significance_seed0,
    "step43": step43,
    "full_label": full_label,
    "explainer_metrics": explainer_metrics,
    "label_noise": label_noise,
    "regularisers": regularisers,
    "injection_ocds": injection_ocds,
    "label_efficiency_proc2fin": label_efficiency_proc2fin,
    "label_efficiency_fin2proc": label_efficiency_fin2proc,
    "ablations": ablations,
}

_TEX_ESCAPE = str.maketrans(
    {
        "_": r"\_",
        "%": r"\%",
        "±": r"$\pm$",
        "Δ": r"$\Delta$",
        "→": r"$\to$",
        "−": r"$-$",  # U+2212, the ablation arms' minus sign
        "–": "--",
        "≤": r"$\leq$",
    }
)


def to_markdown(headers: list[str], rows: list[Row], caption: str) -> str:
    lines = [f"*{caption}*", "", "| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def to_latex(headers: list[str], rows: list[Row], caption: str) -> str:
    esc = lambda s: s.translate(_TEX_ESCAPE)  # noqa: E731
    lines = [
        r"\begin{table}[t]",
        rf"\caption{{{esc(caption)}}}",
        r"\centering",
        r"\begin{tabular}{" + "l" * len(headers) + "}",
        r"\toprule",
        " & ".join(esc(h) for h in headers) + r" \\",
        r"\midrule",
    ]
    lines += [" & ".join(esc(c) for c in r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def build_paper_tables(
    root: Path | str = ".", out_dir: Path | str = "paper/tables"
) -> dict[str, Any]:
    """Build every table whose source artifacts exist; skip the rest with the
    missing path recorded. Returns the build report (also written to disk)."""
    root, out = Path(root), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"built": [], "skipped": {}}
    for name, builder in TABLES.items():
        try:
            headers, rows, caption = builder(root)
        except FileNotFoundError as missing:
            report["skipped"][name] = f"missing artifact: {missing}"
            continue
        (out / f"{name}.md").write_text(to_markdown(headers, rows, caption), encoding="utf-8")
        (out / f"{name}.tex").write_text(to_latex(headers, rows, caption), encoding="utf-8")
        report["built"].append(name)
    (out / "BUILD_REPORT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":  # pragma: no cover — poe paper-tables
    print(json.dumps(build_paper_tables(), indent=2))
