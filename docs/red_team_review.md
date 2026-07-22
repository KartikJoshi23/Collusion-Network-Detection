# Internal Red-Team Review (§7 step 33, §9.3 — M8)

*The pre-submission adversarial pass the plan mandates: every paper-bound
claim audited against the §4.5 evaluation protocol and the §9.1/§9.3
checklist, plus the reproduction-from-scratch check on a clean clone.
Conducted 2026-07-22 on a machine that had never held this repository
(fresh authenticated clone of `main` @ d02fbf0, bootstrapped from the
README only). Findings are numbered RT-1…; each carries a severity and a
disposition. This document records the review — the fixes it produced are
committed alongside it.*

## Verdict

**No finding invalidates a published number or a protocol guarantee.** Two
presentation defects were found and fixed (RT-1, RT-2), two reporting gaps
are recorded for the writing phase (RT-3, RT-4), and every checklist
dimension below otherwise passes. The clean-clone reproduction (section 3)
reproduced every cross-machine-deterministic headline byte-exactly.

## 1. Checklist dimensions (§9.3)

### 1.1 Leakage — PASS

- The dedicated leakage suite passes standalone on the clean clone
  (`uv run pytest backend/tests -m leakage` — 25 tests) and runs as its own
  CI step.
- Every data/feature/split module added since the 2026-07-16 audit carries
  its own leakage-marked coverage, verified present: the OCDS adapter
  (`time_first_seen` ≤ every incident-edge timestamp on the golden fixture),
  precomputed screens (future award attrs cannot enter as-of aggregates),
  label-noise injection (prevalence_baseline and n_confirmed pinned identical
  between clean and 40%-noised runs — noise cannot touch evaluation), the
  practitioner-study kit (ground-truth leak guard, poisoned-bundle test).
- Strict-inductive splits, as-of features, LOCO/LOMO entity isolation: all
  enforced by tests, not convention (§9.1b).

### 1.2 Imbalance reporting — PASS

- Every AUC-PR in the model card, ledger, and table builders is stated
  against its prevalence baseline; cross-fold procurement comparisons go
  through lift only (case-control prevalences are file-construction
  artifacts — Decision log 2026-07-19).
- Tie-aware P@k has been in force since the audit re-baseline (PR #7);
  queue metrics are measured NMS-invariant and hit-rule-robust.
- Paper numbers are multi-seed means; the ledger and model card explicitly
  flag that the published seed-0 runs are best-of-five (GATv2 0.5492 vs
  mean 0.4729 ± 0.0525; ensemble 0.5246 vs 0.4434 ± 0.0501).

### 1.3 Baseline fairness — PASS with a required statement (RT-3)

- B1–B4 run the identical split, label policy, feature discipline, and
  harness as the models they benchmark (verified in the configs — the
  ablation configs pin anchors byte-identical).
- **RT-3 (medium, recorded for the writing phase):** §4.5 promises
  baselines "the same tuning budget as our models." The measured reality is
  that *neither side received a hyperparameter search*: XGB runs fixed
  standard settings (400 trees, depth 6, lr 0.1); the GNNs run fixed
  hand-chosen settings with early stopping on val AUC-PR. The paper must
  state this no-search-on-either-side policy explicitly. The asymmetry risk
  is conservative in our disfavor: the tree baselines *win* every headline
  comparison they enter (Elliptic++ B3 0.8104 vs GNN 0.4729 ± 0.0525;
  Mendeley B2+screens 0.4558 vs R-GCN 0.2808 ± 0.0087), so no positive
  claim rests on beating an undertuned baseline. A val-selected GNN is
  additionally known to be shift-blind here (four independent
  measurements), so extra GNN tuning against val would not close the gap
  honestly.

### 1.4 Honest transfer reporting — PASS

- Transfer claims are matrix-level (7×5 LOCO, 4×5 LOMO), never single-fold;
  the single-fold country_5 story is explicitly demoted in the ledger
  ("does NOT generalize to the full matrix").
- Negative results are first-class: Mendeley's largest market fails (lift
  0.90); fin→proc is negative; label-scarce transfer "never pays at ≤500
  target labels in either direction"; the R-GCN honest negative is
  seed-stable and headlined as such.
- Lift is the only cross-fold comparator; per-fold n and prevalence ride
  every matrix row (table builders verified).

### 1.5 Number consistency (model card ↔ ledger ↔ repro map ↔ builders)

Every number in `docs/model_card.md` and `docs/reproducibility.md` was
traced to its ledger entry; the table builders copy from stored artifacts
only (pinned by test) and skip-with-named-path when an artifact is absent —
exercised live on this artifact-bare clone: `poe paper-tables` built 0 and
skipped all 9 with named paths, exit 0.
Two presentation defects found, both fixed in this review's commit:

- **RT-1 (medium, FIXED): seed-0 bootstrap deltas juxtaposed with
  multi-seed means.** The two paired-bootstrap comparisons (calibrated-vs-
  rank Δ +0.471 CI [0.440, 0.499]; GATv2-vs-B3 Δ −0.261 CI [−0.285,
  −0.235]) are computed over *seed-0 score files*, but the model card
  quoted them beside multi-seed means. A reviewer recomputing deltas from
  the quoted means gets +0.392 and −0.338 — outside the quoted CIs — and
  would reasonably suspect an error. Fix: model card and the significance
  table caption now label the comparisons seed-0 paired-bootstrap and state
  the multi-seed mean differences alongside (both of which are *larger*,
  so no claim weakens).
- **RT-2 (low, FIXED): README determinism line contradicted the measured
  statement.** The README claimed reproducibility is same-machine only;
  `docs/reproducibility.md` §4 (and the ledger) measured that XGB
  baselines, the LOCO country_5 fold, and the frozen-encoder probes
  byte-reproduce cross-machine. The README now matches the measured
  statement. (Also: the Elliptic headline caption called B1 a "tree"
  baseline — now "rule/tree".)

### 1.6 Ablation-grid completeness — PASS

All §7 step-32 arms are either measured (−bidirectional, −unsupervised,
−focal, −screens-as-features three-way, plus the B-CF/B-LG channel
verdicts) or recorded N/A-by-construction with reasoning (−injection,
−temporal-encodings) — nothing silently skipped.

### 1.7 Explanation validity — PASS with known limitation

PGExplainer adoption is evidence-based (three-arm fidelity ablation, PyG
sanity 49/50, fidelity-insane 38/50 → 1/50); bundle invariants are
tested (§9.1). The R-GCN's absent mask-based explanation (R12) and the
pending human validation (step 31's human phase) are recorded limitations,
not gaps this review can close.

### 1.8 Ethics propagation — PASS

The screening-only caveat is enforced per surface (API field, bundle
validator, UI footer, Copilot guard with 0 released violations, study-packet
leak guard) and pinned by hygiene tests. Repo visibility re-verified
**private** from this machine via an unauthenticated API call (404).

### 1.9 Queue-claim scope — RT-4 (medium, recorded)

- **RT-4:** no baseline-scored alert queue exists — every published queue
  is GNN/ensemble-scored. The current claims are safe (absolute values with
  robustness statements; no queue-level superiority claim over baselines),
  but the paper must *not* imply the learned scorer is necessary for queue
  quality without a comparator. Cheap follow-up if the writing wants the
  claim: baselines already persist per-model score parquets
  (`training/baseline_run.py`), so a B3-scored queue is one config away
  (clone `alert_queue_elliptic_pp_ensemble.yaml`, point `scores_dir`/
  `scores_file` at the B3 parquet). Queued as a Next action, not run here.

## 2. Reproduction-from-scratch on a clean clone (§9.3)

Machine: Windows 11, Python 3.11.9, this repository cloned fresh 2026-07-22
(no prior artifacts, no `.env` keys). Bootstrap followed the README
Quickstart verbatim: `uv sync` → `copy .env.example .env` → `uv run poe
data` → `uv run poe test`.

| Gate | Result |
|---|---|
| Backend suite | **371/371 pass** (matches ledger) |
| Leakage suite standalone | 25/25 pass |
| ruff / mypy | clean |
| Frontend `npm install` + build + vitest | build green, **31/31** |
| Dataset download + checksums | elliptic_pp 9, elliptic 3, mendeley_eu 2, garcia_rodriguez 11, ocds_georgia 16 files — **all verified against the committed manifests**; amlworld_hi_small `blocked` (no Kaggle credentials — the designed path) |

Headline reproductions (README/`docs/reproducibility.md` commands verbatim;
"exact" = every decimal the ledger records):

| Claim | Ledger | This machine | Verdict |
|---|---|---|---|
| Mendeley B1/B2/B3/B4 AUC-PR | 0.3426 / 0.3925 / 0.3775 / 0.3811 | 0.34262906 / 0.39253928 / 0.37747900 / 0.38113548 | **exact** |
| Elliptic++ B1/B2/B3 AUC-PR | 0.0576 / 0.8076 / 0.8104 | 0.05757541 / 0.80763262 / 0.81043146 | **exact** |
| LOCO country_5 R-GCN fold (torch) | 0.8025340470101002 | 0.8025340470101002 | **byte-exact** — the §4 cross-machine claim verified on a third machine class |
| García LOMO matrix (torch, 4×5) | macro lift 1.57; folds 0.389 / 0.506 / 0.786 / 0.430; Italy P@10=P@25=1.00 | 1.5720; 0.3894 / 0.5063 / 0.7858 / 0.4295; Italy 1.00/1.00 | **exact at recorded precision** |
| OCDS ingest | 451,346 releases → 488,300 nodes / 1,449,077 edges / 687,336 bids_on / 0 skipped | identical | **byte-exact** |
| OCDS injection seed-0, deterministic parts | floor/common_control 0.4286 flat; cover_bid 0.0 every arm; coordinated_cluster ensemble_rank 1.00@2000 | 0.429 / 0.0 / 1.00 | **exact** |
| OCDS injection seed-0, torch members | e.g. dominant/common_control 0.59@2000; ensemble_rank/coordinated_cluster 0.74@1000 | 0.536; 0.675 | **shifted** — expected: torch is same-machine-only (§4); every shifted value stays inside the multi-seed campaign's spread and the RQ2 verdict is unchanged (clique-type recoverable, award-pattern motifs evade: rotation ≤0.092, partition ≤0.211, cover_bid 0) |

The reproduction confirms the repro package's own determinism taxonomy:
everything it claims byte-reproduces cross-machine did; everything it
scopes to same-machine shifted within the recorded variance without moving
any verdict. Not reproduced here (out of scope, GPU/key-gated or
multi-hour): the Elliptic++ GNN multi-seed campaigns (same-machine torch),
AMLworld (Kaggle-gated), Copilot goldens (key-gated).

## 3. Out-of-scope for this review

The GPU-gated AMLworld set (M6 remainder), the practitioner study's human
phase (step 31, [user]), and the paper's prose (§10.4, [user]) — each
tracked in PROGRESS.md Next actions.
