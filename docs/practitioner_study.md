# Practitioner Rubric Study — Protocol (§7 step 31, §10.3, RQ3)

**Research question (RQ3):** do the system's subgraph explanations map to
practitioner red-flag vocabularies and get judged verifiable and useful?

**Status:** instrument, packets, and analysis are built and tested
(`backend/collusiongraph/eval/study.py`); this document is the runbook for the
human phase. Ethics note: all evidence comes from public, anonymized research
datasets; no real person or firm is identified; every packet carries the
project's screening-only caveat verbatim. Check your institution's capstone
rules before recruiting (lightweight review expected — no sensitive data).

## 1. Design

- **Cases:** 20 alerts sampled across both domains and strata
  (`configs/experiment/practitioner_study.yaml`, seeded — the manifest records
  the draw). Elliptic++ is stratified by motif coverage (5 motif-flagged /
  5 unflagged); Mendeley by queue position (5 top-10 / 5 below), since its
  recalibrated top-20 carries no motif matches (measured 2026-07-16).
- **Arms (§10.3, MC passed):** each case is pre-assigned 50/50 in randomized
  order — **Arm A (bundle-only):** rate from the packet alone; **Arm B
  (bundle+Copilot):** the rater may additionally query the Investigator
  Copilot dock seeded with the packet's alert id (a keyed, serving machine is
  required for Arm B sessions). The arm is printed at the top of each packet.
- **Raters:** ≥5 with AML-compliance or audit familiarity. **Fallback (R14):**
  rubric-trained graduate raters plus at least one domain expert; report the
  substitution as a limitation.
- **Blinding:** packets contain evidence only — no ground-truth labels exist
  in any bundle, and the renderer refuses to emit label vocabulary (tested).
  Raters must not be told which alerts are confirmed cases.

## 2. Instrument (per case, 5-point Likert + free text)

| # | Dimension | Question (verbatim from §10.3) | 1 | 5 |
|---|---|---|---|---|
| 1 | Verifiability | Could you confirm this from the evidence shown? | not at all | fully, from this packet |
| 2 | Red-flag alignment | Does the cited indicator match the evidence? | mismatch | exact match |
| 3 | Actionability | Would this justify escalation? | never | clearly |

Free text: anything notable — missing evidence, misleading framing, what you
would need next. (For Arm B: note whether the Copilot changed your rating.)

## 3. Procedure per rater (~60–90 min)

1. Receive: the 20 packets (`case_01.md` … `case_20.md`) and a personal copy
   of `ratings_template.csv` renamed `ratings_<rater_id>.csv`.
2. Read the caveat and instructions; rate cases **in packet order**; do not
   discuss cases with other raters until all sheets are submitted.
3. Arm B cases only: open the console's Copilot dock, seed it with the
   packet's alert id, ask what you need; the dock's answers carry their own
   AI-generated label and caveat.
4. Fill every Likert cell with 1–5 (leave blank only if you must skip a
   case); free text in `notes`.

## 4. Build & analysis (maintainer side)

```bash
# 1. build packets (regenerate bundles first if eval_outputs are stale):
uv run collusiongraph eval -c configs/experiment/practitioner_study.yaml

# 2. after collecting ratings_<rater>.csv files:
uv run python -c "from collusiongraph.eval.study import summarize_study; \
import json, glob; print(json.dumps(summarize_study( \
sorted(glob.glob('eval_outputs/practitioner_study/ratings_*.csv'))), indent=2))"
```

Reported per §10.3: per-dimension means ± sd, **Krippendorff's α (ordinal)**
per dimension (implementation hand-verified in `test_study.py`), per-arm means
(bundle vs bundle+Copilot), and qualitative themes coded manually from the
free text. Interpretation guardrails: α ≥ 0.8 reliable, 0.667–0.8 tentative
(Krippendorff's own thresholds); report n per cell; the arm comparison is
between-case, not within-case — say so in the paper.

## 5. Outputs

`eval_outputs/practitioner_study/`: `case_NN.md` packets, `ratings_template.csv`,
`study_manifest.json` (the seeded draw: dataset, alert id, stratum, arm per
case — the de-anonymization key; keep it away from raters), and, after
analysis, the summary JSON for the paper's explanation-study section.
