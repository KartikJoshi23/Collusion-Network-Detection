"""Paper tables from harness artifacts (§7 step 33, M8).

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


def _multiseed_row(payload: dict[str, Any], label: str, k: int) -> Row:
    agg = payload["aggregate"]
    return [
        label,
        _ms(agg["auc_pr_mean"], agg["auc_pr_std"]),
        _ms(agg[f"precision@{k}_mean"], agg[f"precision@{k}_std"]),
    ]


def elliptic_headline(root: Path) -> Table:
    sb = _load(root, "eval_outputs/elliptic_pp/baselines/scoreboard.json")["baselines"]
    rows: list[Row] = [
        [name, f"{m['auc_pr']:.4f} (det.)", f"{m['precision@100']:.2f}"]
        for name, m in sorted(sb.items())
    ]
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
        "Elliptic++ node-level results (test steps 35–49, prevalence 0.065). "
        "Tree baselines are deterministic; GNN/ensemble rows are 5-seed mean ± std.",
    )


def mendeley_headline(root: Path) -> Table:
    rows: list[Row] = []
    for rel, suffix in [
        ("eval_outputs/mendeley_eu/baselines/scoreboard.json", ""),
        ("eval_outputs/mendeley_eu/baselines_screens_ablation/scoreboard.json", " +screens"),
        ("eval_outputs/mendeley_eu/baselines_b4_precomputed/scoreboard.json", " +screens"),
    ]:
        sb = _load(root, rel)["baselines"]
        rows += [
            [name + suffix, f"{m['auc_pr']:.4f} (det.)", f"{m['precision@18']:.2f}"]
            for name, m in sorted(sb.items())
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
        "Lift-style reading applies; see the datasheet for the sample caveat.",
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


def significance(root: Path) -> Table:
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
        "(2,000 resamples, stratified).",
    )


def label_noise(root: Path) -> Table:
    payload = _load(root, "eval_outputs/elliptic_pp/label_noise_curve/noise_curve.json")
    rows = [
        [f"{c['rate']:.0%}", _ms(c["auc_pr_mean"], c["auc_pr_std"])]
        for c in sorted(payload["curve"], key=lambda c: c["rate"])
    ]
    return (
        ["Train-label flip rate", "Test AUC-PR"],
        rows,
        "Label-noise robustness (GATv2-focal, 3 seeds per rate). Test AUC-PR RISES "
        "with train noise while validation collapses — the val-blindness diagnostic.",
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
    "significance": significance,
    "label_noise": label_noise,
    "injection_ocds": injection_ocds,
    "label_efficiency_proc2fin": label_efficiency_proc2fin,
    "label_efficiency_fin2proc": label_efficiency_fin2proc,
}

_TEX_ESCAPE = str.maketrans(
    {"_": r"\_", "%": r"\%", "±": r"$\pm$", "Δ": r"$\Delta$", "→": r"$\to$"}
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
