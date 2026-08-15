"""Practitioner-study kit (§7 step 31, §10.3, RQ3).

Everything the human study needs except the humans: seeded stratified case
sampling from real explanation bundles, blinded rater packets, the ratings
template, Krippendorff's α (ordinal, missing-data tolerant), and the
per-dimension / per-arm summary. The study protocol itself lives in
``docs/practitioner_study.md``.

Design invariants:
* Packets NEVER contain ground truth — bundles carry none by construction,
  and the renderer additionally refuses to emit text containing label
  vocabulary (belt and braces; a leaked label would invalidate the study).
* Sampling is seeded and quota-strict: an unmeetable stratum raises, it is
  never silently short-filled.
* Arms (§10.3: bundle-only vs bundle+Copilot — MC passed) are assigned
  50/50 in randomized case order.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from collusiongraph import SCREENING_CAVEAT
from collusiongraph.eval import load_config

ARMS = ("bundle_only", "bundle_plus_copilot")
DIMENSIONS = ("verifiability", "red_flag_alignment", "actionability")
# ground-truth vocabulary that must never reach a rater packet
_LEAK_TOKENS = ("is_cartel", '"label"', "ground_truth", "illicit", "licit")


def _load_bundles(explanations_dir: Path) -> list[dict[str, Any]]:
    bundles = []
    for path in sorted(explanations_dir.glob("*.json")):
        if path.name == "explanations_summary.json":
            continue
        bundles.append(json.loads(path.read_text(encoding="utf-8")))
    if not bundles:
        raise FileNotFoundError(f"no explanation bundles under {explanations_dir}")
    return bundles


def _stratum_filter(bundles: list[dict[str, Any]], rule: str) -> list[dict[str, Any]]:
    if rule == "motif_flagged":
        return [b for b in bundles if b.get("motif") is not None]
    if rule == "motif_unflagged":
        return [b for b in bundles if b.get("motif") is None]
    if rule.startswith("rank_le_"):
        return [b for b in bundles if b["rank"] <= int(rule.removeprefix("rank_le_"))]
    if rule.startswith("rank_gt_"):
        return [b for b in bundles if b["rank"] > int(rule.removeprefix("rank_gt_"))]
    raise ValueError(f"unknown stratum rule {rule!r}")


def sample_study_cases(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Seeded stratified sample → the study manifest (one dict per case).

    Config shape::

        datasets:
          - dataset: elliptic_pp
            explanations_dir: eval_outputs/elliptic_pp/explanations
            strata:
              - {rule: motif_flagged, n: 5}
              - {rule: motif_unflagged, n: 5}
        seed: 0
    """
    rng = np.random.default_rng(cfg.get("seed", 0))
    chosen: list[dict[str, Any]] = []
    for spec in cfg["datasets"]:
        bundles = _load_bundles(Path(spec["explanations_dir"]))
        taken: set[str] = set()
        for stratum in spec["strata"]:
            pool = [
                b for b in _stratum_filter(bundles, stratum["rule"]) if b["alert_id"] not in taken
            ]
            if len(pool) < stratum["n"]:
                raise ValueError(
                    f"{spec['dataset']}: stratum {stratum['rule']!r} needs "
                    f"{stratum['n']} cases but only {len(pool)} are available — "
                    "fix the quota or regenerate bundles; never short-fill silently"
                )
            pool.sort(key=lambda b: b["alert_id"])  # deterministic before the draw
            picks = rng.choice(len(pool), size=stratum["n"], replace=False)
            for i in sorted(int(p) for p in picks):
                bundle = pool[i]
                taken.add(bundle["alert_id"])
                chosen.append(
                    {
                        "dataset": spec["dataset"],
                        "alert_id": bundle["alert_id"],
                        "stratum": stratum["rule"],
                        "bundle": bundle,
                    }
                )

    order = rng.permutation(len(chosen))
    manifest = []
    for case_number, idx in enumerate(order, start=1):
        case = chosen[int(idx)]
        case["case_number"] = case_number
        case["arm"] = ARMS[(case_number - 1) % 2]
        manifest.append(case)
    return manifest


_ARM_TEXT = {
    "bundle_only": "A — rate from this packet alone",
    "bundle_plus_copilot": (
        "B — you may also consult the Investigator Copilot dock "
        "(seed it with the alert id below)"
    ),
}


def _render_case(case: dict[str, Any]) -> str:
    b = case["bundle"]
    lines = [
        f"# Case {case['case_number']:02d}",
        "",
        f"*Arm: {_ARM_TEXT[case['arm']]}*",
        "",
        f"- Alert id: `{b['alert_id']}` (domain: {b['domain']})",
        f"- Queue rank: {b['rank']} · budget position: {b['budget_position']}"
        f" · risk score: {b['risk_score']:.3f}",
        "",
        "## Evidence",
        "",
    ]
    ev = b.get("evidence", {})
    for key in sorted(ev):
        lines.append(f"- {key}: {ev[key]}")
    sub = b.get("minimal_subgraph") or {}
    fidelity = b.get("fidelity")
    lines += [
        "",
        "## Learned-explainer minimal subgraph",
        "",
        f"- nodes: {len(sub.get('nodes', []))} · edges: {len(sub.get('edges', []))}",
        (
            f"- fidelity: {fidelity} (sane: {b.get('fidelity_sane')})"
            if fidelity is not None
            else "- fidelity: not computed for this model class (a recorded limitation)"
        ),
    ]
    motif = b.get("motif")
    lines += ["", "## Motif & red flags", ""]
    if motif is None:
        lines.append("- no structural motif matched for this alert")
    else:
        lines.append(f"- motif: {motif.get('type')} (params: {motif.get('params')})")
    for flag in b.get("red_flags", []):
        lines.append(
            f"- [{flag['framework']}] {flag['indicator_id']}: {flag['indicator_text']}"
            f" — matched because: {flag['matched_because']}"
        )
    sources = b.get("evidence_sources", {})
    lines += ["", "## Evidence sources", ""]
    for source, fields in sorted(sources.items()):
        lines.append(f"- {source}: {', '.join(fields) if fields else '(none)'}")
    lines += ["", "---", "", f"**{SCREENING_CAVEAT}**", ""]
    text = "\n".join(lines)

    leaked = [t for t in _LEAK_TOKENS if t in text.lower()]
    if leaked:
        raise ValueError(
            f"case {case['case_number']}: packet text contains ground-truth "
            f"vocabulary {leaked} — refusing to render (study validity)"
        )
    return text


def build_study_packets(cfg: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Sample cases, render packets + ratings template + manifest to
    ``output_dir``. Returns a small summary dict."""
    cfg = load_config(cfg)
    manifest = sample_study_cases(cfg)
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    for case in manifest:
        (out_dir / f"case_{case['case_number']:02d}.md").write_text(
            _render_case(case), encoding="utf-8"
        )

    with (out_dir / "ratings_template.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rater_id", "case", "arm", *DIMENSIONS, "notes"])
        for case in manifest:
            writer.writerow(["", f"{case['case_number']:02d}", case["arm"], "", "", "", ""])

    slim = [
        {k: v for k, v in case.items() if k != "bundle"} | {"alert_id": case["alert_id"]}
        for case in manifest
    ]
    (out_dir / "study_manifest.json").write_text(
        json.dumps({"seed": cfg.get("seed", 0), "cases": slim}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    per_arm = {arm: sum(1 for c in manifest if c["arm"] == arm) for arm in ARMS}
    return {"n_cases": len(manifest), "per_arm": per_arm, "output_dir": str(out_dir)}


def krippendorff_alpha(ratings: pl.DataFrame, level: str = "ordinal") -> float:
    """Krippendorff's α over a units×raters frame (columns = raters, one row
    per unit; nulls = missing ratings). ``level``: ``ordinal`` (the §10.3
    Likert instrument) or ``nominal``.

    Coincidence-matrix formulation (Krippendorff 2019 §12): units with fewer
    than two ratings drop out; α = 1 − D_o/D_e.
    """
    if level not in ("ordinal", "nominal"):
        raise ValueError(f"unknown level {level!r}")
    rows = [[v for v in row if v is not None] for row in ratings.rows()]
    rows = [r for r in rows if len(r) >= 2]
    if not rows:
        raise ValueError("no unit carries two or more ratings — α is undefined")

    values = sorted({v for row in rows for v in row})
    index = {v: i for i, v in enumerate(values)}
    k = len(values)
    o = np.zeros((k, k))
    for row in rows:
        m = len(row)
        for a in range(m):
            for c in range(m):
                if a != c:
                    o[index[row[a]], index[row[c]]] += 1.0 / (m - 1)
    n_c = o.sum(axis=1)
    n = n_c.sum()

    delta = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            if level == "nominal":
                delta[i, j] = 1.0
            else:
                lo, hi = min(i, j), max(i, j)
                delta[i, j] = (n_c[lo : hi + 1].sum() - (n_c[lo] + n_c[hi]) / 2) ** 2

    d_o = (o * delta).sum() / n
    d_e = sum(n_c[i] * n_c[j] * delta[i, j] for i in range(k) for j in range(k) if i != j) / (
        n * (n - 1)
    )
    if d_e == 0:
        return 1.0  # no variation anywhere: perfect (if degenerate) agreement
    return float(1.0 - d_o / d_e)


def summarize_study(ratings_csvs: list[Path | str]) -> dict[str, Any]:
    """Filled rating sheets → per-dimension means±sd, ordinal α, per-arm means.

    Each CSV is one rater's copy of ``ratings_template.csv`` with ``rater_id``
    and the three Likert columns filled (1–5; blanks = skipped case).
    """
    frames = []
    for path in ratings_csvs:
        df = pl.read_csv(path, infer_schema_length=1000)
        frames.append(df)
    ratings = pl.concat(frames)
    for dim in DIMENSIONS:
        ratings = ratings.with_columns(pl.col(dim).cast(pl.Int64, strict=False))

    report: dict[str, Any] = {
        "n_raters": ratings["rater_id"].n_unique(),
        "n_cases": ratings["case"].n_unique(),
        "dimensions": {},
        "per_arm": {},
    }
    for dim in DIMENSIONS:
        valid = ratings.drop_nulls(dim)
        units = valid.pivot(on="rater_id", index="case", values=dim).drop("case")
        report["dimensions"][dim] = {
            "mean": valid[dim].mean(),
            "std": valid[dim].std(ddof=1),
            "n": valid.height,
            "krippendorff_alpha_ordinal": krippendorff_alpha(units, level="ordinal"),
        }
    for arm in ARMS:
        arm_rows = ratings.filter(pl.col("arm") == arm)
        report["per_arm"][arm] = {dim: arm_rows.drop_nulls(dim)[dim].mean() for dim in DIMENSIONS}
    return report
