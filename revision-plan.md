# Revision Plan — "One Stack, Two Ledgers" (journal revision)

Prepared 14 November 2026 for Kartik Joshi. Phase 2 deliverable.

**Update after your answers (14 November).** Your decisions are recorded in Section 7. An audit of this plan against the code and the artifacts found 21 errors or gaps; all are fixed, and Section 10 lists each one. You authorised implementation without a further approval step.

The single source of truth is `Research Paper/Revision Brief One Stack, Two Ledgers.md`. It has 19 items (13 P1, 6 P2) and Parts A to H. Every brief item appears in the traceability table in Section 9.

---

## 0. Starting point

### 0.1 What this plan relies on

| Fact | Evidence |
|---|---|
| The root is a git checkout of `main` at `3f5188d`. Your two items are untracked and untouched. | `git status` |
| The repository passes all checks. | Backend 391 passed; leakage step 25 passed; ruff, black and mypy clean; frontend 53 passed |
| The provided LaTeX source matches the provided PDF. | Compiled in scratch: 12 pages, identical text (8,797 words), 0 errors |
| All five datasets are downloaded and checksum-verified. | Elliptic++ 9/9, Mendeley 2/2, García 11/11, OCDS Georgia 16/16, AMLworld 3/3 files match `data/manifests/` |
| The artifacts you supplied are the ones behind the paper. | I checked 184 quoted numbers against `eval_outputs/eval_outputs/`: 182 match exactly. The two mismatches are the Appendix A coordinated-cluster entry the brief already flags. |
| The artifacts came from another machine (the ledger's "master"). | Its audit script points at `D:/MAIB/...`, which does not exist here. File dates run from 17 July to 19 August 2026. |
| Torch results are machine-dependent. | The repository measured about ±0.02 AUC-PR between machines. Other results reproduced exactly on another machine: byte for byte for the trees, the LOCO country_5 fold, the probes and the OCDS ingest; at the recorded precision for the LOMO matrix (`docs/reproducibility.md` §4, `docs/red_team_review.md` §2). |
| This machine | Intel i5-11300H, 4 cores, 15.8 GB RAM, no GPU, MiKTeX installed |

### 0.2 A defect found while checking the artifacts (not in the brief)

The stored alert queues were not built by the configs the paper names.

- `eval_outputs/elliptic_pp/alert_queue_ensemble/alerts.parquet` (254 alerts) carries `model_run_id = gatv2_multi_s0`. `scripts/build_demo_artifacts.py` rebuilds this folder from `gnn_gatv2_focal_multi`. That is the raw-plus-structural arm (0.3781) which Table VII says was not adopted. The paper and Appendix A attribute the queue to `alert_queue_elliptic_pp_ensemble`, the calibrated ensemble.
- `eval_outputs/mendeley_eu/alert_queue/alerts.parquet` (223 alerts) carries `model_run_id = sage_struct_s0`. It was built from the structural GraphSAGE encoder used as the probe source. `alert_queue_mendeley_eu.yaml` names the seed-0 R-GCN, and that run (`gnn_rgcn_focal`) is not in the artifacts.
- Leiden builds communities from graph structure only, and the alert count depends only on those communities and the size cap. So the alert counts (254 and 223) and community counts (318 and 1,283) should not change; R6 checks this rather than assuming it. The ranking can change, and with it precision@k, coverage, and which alerts were explained.
- Numbers that rest on these two queues:
  - Section V-B: P@50/100/200 of 0.32/0.23/0.135, 7.8% coverage, and procurement P@4 of 0.50.
  - Section V-E: the sensitivity grid.
  - Section VI: the financial bundle counts (15 of 50 with a motif, 1 of 50 implausible) and the Mendeley bundles (0 motifs), plus the explainer ablation (49/50 against 12/50), whose 50 nodes come from the queue's top alerts. The actor queue and the García Italy queue were built from the right models and are not affected.
  - Fig. 2's "254 financial + 223 procurement alerts".
- Plan: step R6 (Section 4) rebuilds both queues from the named configs, using the stored scores, with no retraining. I report the result before touching any text. I also change the demo script so it cannot overwrite a published queue folder.

---

## 1. Classification of the 19 items

| # | Item | Part | Priority | Type |
|---|---|---|---|---|
| 1 | Correct the EU AI Act / AML argument | A1 | P1 | Content; needs external verification |
| 2 | Narrow the scope; fix RQ-to-section mapping; reframe RQ3 | A2 | P1 | Content |
| 3 | Cut Section VII to one Future Work paragraph | A2 | P2 | Content (also removes Fig. 7) |
| 4 | Tone down overstated claims | A3 | P1 | Content; three rows take numbers from B2, B5, B6 |
| 5 | Add the B3 per-step curve to Fig. 3 | B1 | P1 | Both |
| 6 | Run XGBoost over five seeds | B2 | P1 | Both |
| 7 | Run B2 on local features only | B3 | P1 | Both |
| 8 | Diagnose the below-chance results | B4 | P1 | Both |
| 9 | Pooled lift and per-fold CIs for transfer folds | B5 | P1 | Both |
| 10 | Frozen probe vs raw-feature model at full labels | B6 | P2 | Both |
| 11 | Temporal validation; label noise vs explicit regularisers | B7 | P2 | Both |
| 12 | Standard explainer metrics | B8 | P2 | Both |
| 13 | Add the missing methods details | C | P1 | Content, sourced from configs and code |
| 14 | Fix internal inconsistencies | D | P1 | Both: numbers are re-copied from runs; some need reruns |
| 15 | Fix and extend the references | E | P1 | Content; needs external verification |
| 16 | Rewrite the abstract; language pass on Sections I–II | F | P1 | Content |
| 17 | Fix Figs. 6 and 7 | F | P2 | Technical (figure script) and content (captions) |
| 18 | Move to the Springer template; add declarations | G | P2 | Both |
| 19 | Disclose any earlier version of these results | G | P1 | Content; decision for you and Dr. Garg |

---

## 2. Execution order

### 2.1 Reconciling "fix Part A first" with "reruns may change headlines"

Part A contains two kinds of change, and I treat them differently.

1. **Number-free changes come first, before any run, as the brief asks:**
   - A1, the legal framing.
   - A2: contributions, RQ labels, RQ2 wording, the RQ3 reframe, the RQ1 answer and the Section VII cut.
   - Three A3 rows that change wording only: "all four evaluated markets", the copilot metric, and "luck as much as skill".
2. **Number-bearing rows are reframed in Part A, but their numbers come only from runs:**
   - A3, transfer 2.31× (B6).
   - A3, Mendeley macro lift 1.17 (B5).
   - A3, the bootstrap gap −0.261 (B2).
   - A3, "four measurements" (B7).
   - A3, the calibration claim, which says fusion did not beat its best member. Adding B3 to the fusion can change that.
   - A2, the RQ3 answer. Its fidelity and coverage numbers come from the rebuilt queue (R6) and B8.
   - The copilot interval (24/26, Wilson 95% CI). It is computed by a committed config, not by hand.

   Each open number is written as a placeholder macro, for example `\PENDING{B5}`. The macro prints a visible red marker, and the final audit fails while any marker remains.
3. **A headline pass follows Part B.** It re-reads the abstract, the RQ answers, the A3 rows and the conclusion against the new results. If B1 shows the trees also collapse at step 43, RQ1 is reframed at this point, as the brief requires.

So no number is typed twice, Part A still precedes every run, and every headline change traces to a run.

### 2.2 Order of the Phase 3 parts

Each part ends with a report and a stop for your "continue".

| Step | Part | Type | Needs |
|---|---|---|---|
| 3.1 | Setup: revision branch, manuscript into the repo, artifact working copy, dataset ingest | Technical | — |
| 3.2 | Part A: A1, A2 (incl. item 3), number-free A3 rows | Content | 3.1 |
| 3.3 | Reproducibility check R1–R7, incl. the queue rebuild (Section 4) | Technical | 3.1 |
| 3.4 | Code changes for Part B, each with tests; CI must stay green. Also a numbers manifest and a checker that every result number in the `.tex` matches its artifact (Section 2.4) | Technical | 3.3 |
| 3.5 | P1 runs in the order B2, B1, B3, B4, B5; raw results shown next to current claims | Technical | 3.4 |
| 3.6 | Text for B1–B5; number-bearing A3 rows; the Part D rows they settle | Content | 3.5 |
| 3.7 | P2 runs: B6, B8 (fast), B7 (long, in the background) | Technical | 3.4; B8 also needs R6 |
| 3.8 | Text for B6–B8; Part C methods details; remaining Part D | Content | 3.7 |
| 3.9 | Part E references (can run while B7 computes) | Content | — |
| 3.10 | Part F: abstract, language pass, all figures | Both | 3.6, 3.8, 3.9 |
| 3.11 | Appendix A, `docs/reproducibility.md`, model card, CI guard, full number audit | Technical | all above |
| Phase 4 | Part G, after you confirm the journal | Both | 3.11 |
| Phase 5 | Final audit and delivery | Both | Phase 4 |

**Where this departs from strict A→G order, and why:**
- Part C follows Part B, because the methods must describe the new runs: seeded XGBoost, the local feature set, and the regulariser arms.
- Part E runs alongside B7, because it needs no results and B7 needs many CPU hours.
- Part B order puts B2 first, because B1's per-step curve should use the seeded B3 that Table II will report.

### 2.3 Dependency map

```
R6 queue rebuild ─► V-B queue numbers, V-E sensitivity, VI bundle counts, B8, Fig. 2 text
B2 seeded trees  ─► Tables II and IV; Table III; B1; A3 bootstrap row; abstract RQ1 sentence
B3 in fusion     ─► A3 calibration row ("fusion did not beat its best member"); V-A fusion text
B1 per-step      ─► Fig. 3; pre/post-43 table; RQ1 framing (A2, A3); conclusion
B3 local         ─► Table II rows; V-A paragraph (D9); Part C feature lists
B4 diagnosis     ─► Table IV note; V-D, V-E text; procurement queue if a bug is found
B5 pooled lift   ─► Table VI; Fig. 4; A3 LOCO row; abstract transfer sentence
B6 full-label    ─► Fig. 5; A3 transfer row; abstract cross-domain sentence; Part C probe text
B7 noise vs reg. ─► Fig. 6; new comparison table; D6; Limitations; A3 "four measurements"
B8 explainers    ─► new Section VI table; D22
Part C           ◄─ configs and every new run
Part D           ◄─ all runs
Part E           independent
Part F           ◄─ Parts A–E
Part G           ◄─ journal decision (Dr. Garg)
```

### 2.4 How the protocol guarantees are kept

| Guarantee | How the plan keeps it |
|---|---|
| Strict inductive splits | No split changes. The optional B7 validation window still ends at step 34. |
| Frozen train-time normalisation | Untouched. New feature subsets use the same fit-on-train statistics. |
| Five seeds with dispersion | Extended to the trees (B2, B3) and to B7 (three seeds become five). |
| Paired bootstrap | Extended to every seed pair. It gets a committed config; today none exists. |
| Leakage suite | New feature-selection code gets a leakage test. Diagnostics read stored scores only. |
| Number-to-config map and its CI guard | Every new config is added to Appendix A and to `docs/reproducibility.md`. The guard reads the latter, so CI fails if one is missing. The guard is extended to the paper's Appendix A (Q13). |
| Never retyping a number | `paper/numbers_manifest.yaml` names, for each result number in the paper, its artifact, its JSON key and its rounding. `scripts/audit/verify_numbers.py` is rewritten to read that manifest and fail on any mismatch, and on any unlisted result number in the `.tex`. It replaces today's version, which hard-codes master's `D:` path. Derived numbers (differences, ratios, lifts, confidence intervals) are produced by committed configs, never by hand. |
| Honest negative results | B4 diagnoses and every rerun are reported as they come out. |
| Cross-domain framing | Kept as one of the two lead contributions (A2). |

**Working rules.**
- All work happens on branch `paper/journal-revision`, with small conventional commits and the full test suite run before each commit. Nothing is pushed or merged without your approval.
- The ledger's three git prohibitions hold: do not delete the five old branches, do not force-push, do not run `gc --prune`.
- The change log lives in `paper/revision-changelog.md`, in the brief's Part H format, and is updated after every part.

---

## 3. Part B runs

**Runtime estimates.** They use master's recorded training times, read from the artifacts: GATv2 14–37 min per run, R-GCN about 3 s per seed, LOMO about 17 s per fold. This 4-core laptop may be slower. I time one GATv2 run here in R7 and re-estimate before any long run starts.

**Runs on stored master artifacts.** These need no retraining: B1 (GATv2 part), the B2 bootstrap's GATv2 side, B4, B5, and B8's model checkpoint.

### B1. Per-step curve for the tree baseline (P1)

- **Config:** no new training config. The seeded baseline runs of B2 emit per-step metrics through `per_time_step: true`. This needs a small change: `training/baseline_run.py` must pass the flag to the harness.
- **Code:** a table builder `per_step_split` in `eval/tables.py`. For steps 35–42 and 43–49 it gives AUC-PR over the pooled confirmed nodes of the window, and the mean of the per-step values. Both are reported, labelled.
- **Command:** part of B2.
- **Runtime:** seconds.
- **Outputs:** `per_time_step` blocks in each seed's `metrics.json`; the `per_step_split` table.
- **Feeds:**
  - Fig. 3: a B3 line (5-seed mean ± 1 s.d.) next to GATv2.
  - A new small table of pre-43 and post-43 AUC-PR for B3 and GATv2. The GATv2 values come from the stored per-step metrics.
  - The V-A step-43 paragraph, the RQ1 answer and the conclusion.
- **Brief rule:** if B3 also collapses at step 43, RQ1 is reframed.

### B2. Trees over five seeds (P1)

- **Configs:**
  - `baselines_elliptic_pp_multiseed.yaml`: B2 and B3; seeds 0–4; `subsample: 0.8`, `colsample_bytree: 0.8`; `per_time_step: true`.
  - `baselines_mendeley_eu_multiseed.yaml`: B2 and B3, same settings.
  - `baselines_mendeley_screens_ablation_multiseed.yaml`: B2+screens and B3+screens, only if you agree (Q5).
  - `significance_elliptic_pp.yaml`: recreates today's seed-0 Table III from the stored scores, so Table III gets a committed source (D15).
  - `significance_elliptic_pp_multiseed.yaml`: paired bootstrap per seed pair (GATv2 seed s vs B3 seed s; calibrated seed s vs rank seed s), plus the same comparisons on seed-averaged scores.
- **Code:** a multi-seed wrapper for baselines (today's wrapper handles GNNs only); a significance runner with a CLI dispatch (today nothing writes `significance.json`). Both get unit tests.
- **Commands:** `uv run collusiongraph train -c configs/experiment/baselines_elliptic_pp_multiseed.yaml`, then `uv run collusiongraph eval -c configs/experiment/significance_elliptic_pp_multiseed.yaml`.
- **Runtime:** Elliptic trees 20–40 min; Mendeley about 2 min; bootstrap 5–10 min (2,000 resamples, 12 comparisons, 16,670 nodes).
- **Outputs:** `baselines_multiseed.json` (mean ± SD), per-seed score files, `significance_multiseed.json`.
- **Feeds:**
  - Tables II and IV: B2 and B3 rows become mean ± SD.
  - Table III: the range of the five deltas and CIs, plus a seed-averaged row.
  - Table VII's Mendeley block, the abstract's RQ1 sentence, the V-A text and the A3 bootstrap row.
- **Validity:** the GATv2 side uses the stored per-seed scores.
  - R1 confirms that the unsubsampled XGBoost runs reproduce across machines.
  - The subsampled runs use XGBoost's own seeded generator. Master has no reference for them, so they are simply recorded as run here.
  - The deterministic tree configs stay as reproducibility anchors in Appendix A. Tables II and IV report the seeded runs, as the brief asks.
- **Optional item, now included (Q6): "add B3 to the calibrated fusion".**
  - The stored ensemble keeps only test-window scores for its unsupervised members. Retraining those members here would put two machines into one fusion.
  - So the clean version is a two-member calibrated fusion of GATv2 and B3. GATv2 uses the stored per-seed validation and test scores. B3 is retrained on steps 1–29 so it can be calibrated out of sample on steps 30–34.
  - Configs: `baselines_elliptic_pp_calib_multiseed.yaml` (B3, `train_end: 29`, seeds 0–4) and `fusion_gatv2_b3_multiseed.yaml`.
  - Reported against both members alone, labelled as a supervised-member fusion.
  - Runtime: about 30 min.

### B3. B2 on local features only (P1)

- **Config:** `baselines_elliptic_pp_local_multiseed.yaml`: B2-local and B3-local, seeds 0–4, same XGBoost settings as B2.
- **Code:** a `feature_set` option in `assemble_features`, so a config can select named column groups. A test asserts that the local set contains no `Aggregate_feature_*` column and no edge-derived column.
- **Proposed definition (Q4):**
  - **B2-local** = Weber et al.'s local set: the time step plus `Local_feature_1`–`93` (94 columns). It drops the 72 aggregates, Elliptic++'s 17 added columns (two of them are degree counts) and the edge-derived money-flow pack (in/out counts, velocity, burstiness, holding time).
  - **B3-local** = B2-local plus the structural template, the neighbour means of the local columns, and the money-flow pack.
- **Command:** `uv run collusiongraph train -c configs/experiment/baselines_elliptic_pp_local_multiseed.yaml`
- **Runtime:** 20–40 min.
- **Outputs:** `eval_outputs/elliptic_pp/baselines_local_multiseed/`: per-seed score files and metrics, plus `baselines_multiseed.json` (mean ± SD).
- **Feeds:** new Table II rows; the rewrite of the V-A paragraph that begins "The tree baseline is not winning as…" (D9); the Part C feature lists; possibly the RQ1 framing.

### B4. Diagnose the below-chance results (P1)

- **Config:** `diagnose_below_chance.yaml`, one block per case.
- **Code:** `eval/diagnostics.py` computes four checks:
  - AUC-PR on 1 − score, per seed.
  - A label-encoding trace: raw value → IR label → y, with counts per split.
  - Train-versus-test feature distributions: KS statistic and standardised mean difference per feature, plus degree distributions.
  - Score ties.
- **Cases:**
  - (a) Mendeley R-GCN at 0.2808, from the stored 5-seed scores.
  - (b) AMLworld B2/B3 at 0.0064/0.0062, from the stored scores plus the AMLworld ingest.
  - (c) The financial-to-procurement probe at 0.2841, from the stored scores.
  - (d) **Added by me:** the procurement-to-financial source encoder scores 0.2884 against 0.358 on its own Mendeley test set. I found this in the artifacts; the brief does not list it.
- **Command:** `uv run collusiongraph eval -c configs/experiment/diagnose_below_chance.yaml` (new `eval` dispatch).
- **Runtime:** about 15 min, plus about 10 min for the AMLworld ingest.
- **Outputs:** `diagnostics.json`.
- **Feeds:** one short diagnosis per case in V-A, V-D and V-E, and a Table IV note. If a bug is found, I fix it, rerun every affected config (including the procurement queue) and report every number that moves, before any text is edited.

### B5. Pooled lift and per-fold CIs for transfer (P1)

- **Config:** `transfer_pooled_lift.yaml`. Its inputs are the stored LOCO and LOMO matrix folders.
- **Code:** `eval/transfer_summary.py` computes, per seed:
  - pooled AUC-PR over all held-out firms divided by pooled prevalence;
  - size-weighted lift;
  - a per-fold stratified bootstrap 95% CI (2,000 resamples) on the seed-averaged fold scores.
  It then averages across seeds.
- **Command:** `uv run collusiongraph eval -c configs/experiment/transfer_pooled_lift.yaml` (new `eval` dispatch).
- **Runtime:** under 5 min.
- **Outputs:** `transfer_pooled.json`.
- **Feeds:** new Table VI columns, with macro lift moved to a footnote; CI whiskers on Fig. 4; the A3 LOCO row; the abstract's transfer sentence; the V-D text.
- **Caveat for the text:** pooled AUC-PR ranks scores from seven different fold models together. It is reported as the brief asks, next to size-weighted lift, which has no such problem.
- **Country names (Q8):** the public Mendeley file contains only `country_1`…`country_7`; I checked the downloaded file. I will look for a published mapping in the Mendeley record and the companion paper. Without one, the item stays open with that reason.

### B6. Frozen probe against the raw-feature model (P2)

- **Config:** `cross_domain_full_label_comparison.yaml`.
- **Code:** a full-label comparator in `training/transfer_run.py`. It fits a logistic probe on the target's raw features (Elliptic's 183 columns; Mendeley's tabular screens), with the same split, class weights and scaling as the frozen probe. It also gets an option to load the stored source encoder instead of retraining it.
- **Comparators at full labels:**
  - the frozen probe (stored: 0.1502 procurement→financial; 0.2841 financial→procurement);
  - the structural-feature probe (stored: 0.1084 and 0.2705). This is what the paper now calls the "raw-feature probe".
  - the new raw-feature logistic probe;
  - in-domain XGBoost (B2: 0.8076 and 0.3925, or the B2 5-seed mean).
- **Command:** `uv run collusiongraph train -c configs/experiment/cross_domain_full_label_comparison.yaml` (new `train` dispatch).
- **Runtime:** under 10 min.
- **Outputs:** `eval_outputs/cross_domain/full_label_comparison/full_label_comparison.json`, with all four comparators for both directions, plus their score files.
- **Feeds:** the full-label point on Fig. 5; the abstract's cross-domain sentence; the A3 transfer row; V-D.
- **Part C answer to "how encoders handle different feature spaces":** they never ingest the raw features. Both domains are mapped to the same structural template, z-scored within each graph.

### B7. Temporal validation and the label-noise result (P2)

- **Configs:** `label_noise_elliptic_pp_5seed.yaml`; `gnn_elliptic_pp_gatv2_focal_{ls,wd,do,es}_multiseed.yaml`; optionally `gnn_elliptic_pp_gatv2_focal_valwin_multiseed.yaml`. Details in steps 2 and 3 below.

1. **State the current split (no run).**
   - Validation is already temporal. Training loss uses steps 1–29; early stopping uses validation AUC-PR on steps 30–34 (`training/trainer.py`), never random nodes.
   - The clean value of 0.4827 is the mean of seeds 0–2 of the headline campaign. The headline 0.4729 is the mean of seeds 0–4. The stored per-seed values are 0.5492, 0.4712, 0.4276, 0.4213 and 0.4951.
2. **Temporal window rerun.** The current design already satisfies this. As a sensitivity check (Q10), I propose one alternative window: loss on steps 1–31, validation on 32–34, 5 seeds (`gnn_elliptic_pp_gatv2_focal_valwin_multiseed.yaml`).
3. **Noise versus regularisers.**
   - `label_noise_elliptic_pp_5seed.yaml`: rates 0, 0.05, 0.10 and 0.20, seeds 0–4.
   - Four regulariser arms on clean labels, 5 seeds each, values fixed now before any result (Q10):
     - label smoothing, ε = 0.1 (new code in `losses.py`, with a test);
     - weight decay 5e-3 (10×);
     - dropout 0.5;
     - early-stopping patience 5.
   - Configs: `gnn_elliptic_pp_gatv2_focal_{ls,wd,do,es}_multiseed.yaml`.
4. **Five seeds instead of three:** covered by item 3.

- **Commands:** `uv run collusiongraph train -c configs/experiment/label_noise_elliptic_pp_5seed.yaml`, then the same verb for each `gnn_elliptic_pp_gatv2_focal_{ls,wd,do,es}_multiseed.yaml` (and `…_valwin_multiseed.yaml` if approved).
- **Runtime:** 40 GATv2 trainings, or 45 with the window check. That is about 15–30 CPU hours here. Runs go in the background and can resume, because completed seeds are skipped.
- **Outputs:** `eval_outputs/elliptic_pp/label_noise_curve_5seed/noise_curve.json` (4 rates × 5 seeds) and one `multiseed.json` per regulariser arm, each with per-seed validation and test AUC-PR.
- **Machine note (Q2):** if B7 runs here, its clean 5-seed mean will differ from the headline 0.4729 by machine variance. The comparison table stays internally consistent, since every arm runs on one machine, and the text says so. Running B7 on the master machine would avoid this.
- **Feeds:** a 5-seed Fig. 6; a short comparison table; the V-E text; D6; Limitations; the A3 "four measurements" row.

### B8. Standard explainer metrics (P2)

- **Config:** `explainer_metrics_elliptic_pp.yaml`: the same three arms on the same 50 alerts, the stored seed-0 GATv2 checkpoint, and sparsity switched on.
- **Code:** add sparsity (1 − kept edges / ego-window edges) and per-arm Fidelity+ and Fidelity− summaries to `explain/explainer_ablation.py`. The hard-mask fidelity definitions already exist.
- **Check first:** the stored file gives GNNExplainer and attention exactly the same mean hard Fidelity+ (−0.000365). I will check whether the two arms select the same edges before reporting anything.
- **Definitions to write:**
  - "Sane attribution" = PyG Fidelity+ ≥ Fidelity− for the node.
  - "Implausible fidelity" = the bundle flag `fidelity_sane = false`, which is the same test.
  - The current sentence mixes hard sanity (attention 0.36) with PyG sanity (GNNExplainer 0.24 = 12/50). The table will show both, labelled.
- **Depends on R6:** the 50 nodes come from the queue's top alerts.
- **Command:** `uv run collusiongraph explain -c configs/experiment/explainer_metrics_elliptic_pp.yaml`
- **Runtime:** about 5 min.
- **Outputs:** `eval_outputs/elliptic_pp/explainer_metrics/explainer_metrics.json`, with per-node rows and per-arm summaries (Fidelity+, Fidelity−, sparsity, both sanity rates, time).
- **Feeds:** a small new table in Section VI; the VI text; Appendix A.

---

## 4. Reproducibility check (step 3.3, before any new experiment)

**Artifacts.** Per your answer (Q3), master's artifacts are moved, not copied, from `eval_outputs/eval_outputs/` up into `eval_outputs/`, so there is one copy. That copy must never be overwritten by accident:
- **Reruns of existing configs for this check (R1–R5, R7)** write to `eval_outputs/_repro/<id>/`. They use run-time copies of the committed configs with only `output_dir` (and `source.output_dir`) changed. These copies live in the scratch folder and produce no paper number.
- **Planned replacements back up first.** These are the two queues (R6) and the outputs that depend on them (sensitivity, explanation bundles). Each folder is copied to `eval_outputs/_superseded/<path>/` before it is rebuilt.
- Both folders sit inside the git-ignored `eval_outputs/`.

**Ingest check first.** The node and edge counts must match the ledger: Elliptic++ 203,769 / 234,355; Mendeley 14,555 / 24,251; OCDS 488,300 / 1,449,077.

| ID | What I rerun | Expected | Pass rule |
|---|---|---|---|
| R1 | `baselines_elliptic_pp.yaml` | B1/B2/B3 = 0.05757541 / 0.80763262 / 0.81043146 | score files byte-identical |
| R2 | `baselines_mendeley_eu.yaml`, `baselines_mendeley_screens_ablation.yaml`, `baselines_mendeley_b4_precomputed.yaml` | 0.3426 / 0.3925 / 0.3775 / 0.3811; 0.4558 / 0.3450; 0.3874 | byte-identical |
| R3 | `transfer_loco_mendeley.yaml` (country_5 fold) | 0.8025340470101002 | exact |
| R4 | `cross_domain_probe_proc2fin.yaml`, `cross_domain_probe_fin2proc.yaml` | 0.15022049218819097 and the stored financial→procurement value | exact |
| R5 | `transfer_lomo_matrix_garcia.yaml` | macro lift 1.5720; fold values as stored | exact |
| R6 | `alert_queue_elliptic_pp_ensemble.yaml`; `alert_queue_mendeley_eu.yaml` (pointed at the stored R-GCN multiseed `seed_0`, which uses the same protocol); both sensitivity configs | the paper's queue numbers | reported as found (Section 0.2) |
| R7 | `gnn_elliptic_pp_gatv2_focal.yaml` (one seed-0 GATv2 run) | 0.5492089151328867 on master | machine-class probe: byte-identical means torch reruns here can mix with master's |
| R8 | After step 3.4: `significance_elliptic_pp.yaml`, the new committed source for today's Table III | −0.26122254914158083, CI [−0.28470783, −0.23477059]; +0.47099307, CI [0.44042282, 0.49943009] | exact. The bootstrap is seeded and uses no torch, so the new runner must reproduce the stored `significance.json`. |

**What is not expected to reproduce.** GNN numbers (GATv2, R-GCN, the ensemble's torch members) are not expected to match byte for byte on a new machine; R7 measures this instead of assuming it. Total time is about 1.5–2 h, mostly R7.

---

## 5. Plans for Parts C, D, E and F

### 5.1 Part C — methods checklist

Each value is re-read from its source before it is written into the paper.

| Detail | Source in the repository | Value to report |
|---|---|---|
| Elliptic++ split | `training/trainer.py`, GATv2 configs | Train graph ≤ step 34; loss steps 1–29; validation 30–34 (early stopping on validation AUC-PR, patience 20, at most 200 epochs); test 35–49 |
| Mendeley split | `gnn_mendeley_rgcn*.yaml`, `baselines_mendeley_eu.yaml` | Train ≤ 2013 (R-GCN loss ≤ 2010, validation 2011–2013); test ≥ 2014; firm level; 363 test firms; as-of training labels (`mendeley_as_of`) |
| LOCO / LOMO folds | `training/transfer_run.py` (`_pick_val_group`), `matrix.json` | One country or market held out; validation = smallest other group with ≥ 3 confirmed firms per class; fold sizes from `matrix.json` |
| B2 features | `training/baseline_run.py` (`assemble_features`) | Elliptic++: 183 columns + money-flow pack. Mendeley: award screens |
| B3 features | same | B2 + structural template (degrees, triangles, mutual dyads, clustering, k-core, burstiness, community statistics) + neighbour means |
| B1 rules | `baselines_*.yaml` | Elliptic: P99 in-degree, P99 out-degree, P95 velocity, P5 holding time, P99 mutual degree. Mendeley: P95 of awards, market share, buyer HHI. Thresholds fit on train only |
| Hyperparameters | configs | GATv2: 2 layers, 64 hidden, 4 heads, dropout 0.3, lr 0.005, weight decay 5e-4. R-GCN: 2 layers, 64 hidden, dropout 0.3, lr 0.01, ≤ 300 epochs, patience 30. Focal γ = 2.0, α unused. XGBoost: 400 trees, depth 6, lr 0.1, hist, scale_pos_weight = negatives/positives. DOMINANT/GAE: hidden 32, 50 epochs |
| Tuning | `docs/red_team_review.md` (RT-3) | No hyperparameter search for any model, so the budgets are equal (none). The paper says so explicitly. |
| Unlabelled nodes | `trainer.py`, `eval/metrics.py`, `eval/alert_unit.py` | Used in message passing, never in the loss; excluded from every metric; in queues they are neither illicit nor confirmed, and a hit needs ≥ 1 illicit member |
| Fusion | `models/ensemble.py`, `training/ensemble_run.py`, configs | Members: GATv2 (the only supervised member), DOMINANT, GAE, structural floor. Each member is isotonic-calibrated on validation steps 30–34. The fused score is the equal-weight mean of the calibrated scores (no `weights` are set in the configs). Rank fusion is the mean of rank percentiles. |
| Alert queue | `training/alert_queue.py`, `models/rollup.py`, `configs/eval/*` | Leiden resolution 1.0, seed 0, on the test-window subgraph; minimum community size 2; group score = mean of the member maximum and the top-25% member mean; size cap 100; Jaccard NMS at 0.5; budgets 50/100/200 for financial (the problem statement's "top 100" ± one step) and 4/18/36 for procurement (top 1/5/10% of 363 firms) |
| Cross-domain probe | `training/transfer_run.py` | Frozen GraphSAGE encoder trained on the source's structural template (no raw features); logistic regression (balanced, max_iter 2000) fit on the target's training period |
| Copilot | `backend/copilot/config.py`, `agent.py`, `goldens.json` | `nvidia/nemotron-3-super-120b-a12b` via NVIDIA NIM; validator `nvidia/nemotron-3-nano-30b-a3b`; temperature 0; max_tokens 4096; prompts in `backend/copilot/agent.py`; 26 goldens (SQL 8, RAG 4, bundle 3, guardrail 3, honesty 3, metrics 2, stress test 2, alert tools 1). The gate ran on 19 August 2026 against the serving artifacts of that date. It cannot be rerun here (no NVIDIA key), so the paper gives the date. |
| Compute | artifacts' `train_seconds`; this machine | CPU, full batch. Master: GATv2 14–37 min per run; master's hardware is needed from you (Q2). New runs: i5-11300H, 4 cores, 15.8 GB |
| Code and data availability | — | Repository URL; wording decided by you and Dr. Garg (L3) |

### 5.2 Part D — each inconsistency and its source run

The brief's twelve:

| ID | Where | Fix | Source |
|---|---|---|---|
| D1 | Table V vs Appendix A (0.92 ± 0.17 against 0.923 ± 0.162) | Both from one file: the stored value is 0.9225 ± 0.1733, so print "0.92 ± 0.17" everywhere. The repo docs' 0.9275 ± 0.162 came from another machine and are updated. | `injection_recovery_ocds_georgia_multiseed` |
| D2 | III-B "0.29–0.89" vs V-D "0.25–0.89" | Both are correct for their scope: Mendeley 0.286–0.889; García 0.250–0.548. Name the scope in each place. | both transfer matrices |
| D3 | "USA" vs "America" | Use one name. The data files say "America"; I check what García Rodríguez et al. use and follow it. | García adapter |
| D4 | "Every García market beats its base rate" | "All four evaluated markets" (abstract, Fig. 4 caption, V-D) | LOMO matrix |
| D5 | Procurement queue at P@4 (0.50) and P@18 (0.33) | Use P@18 (top 5%) throughout; it matches Table IV (Q11) | rebuilt queue (R6) |
| D6 | Clean 0.4827 vs headline 0.4729 | Explain (three seeds vs five), then the B7 5-seed curve | label-noise curve; B7 |
| D7 | Table VII "− unsup. members" equals the GATv2 headline | State that GATv2 is the only supervised member; the stored ensemble confirms this | ensemble multiseed |
| D8 | "Our own previously published" 0.5492 | The figure appears in the course report (`Report.pdf`, August 2026), the public repository's docs and the earlier draft; I found no peer-reviewed publication. Wording decided by you and Dr. Garg (L4). | `gnn_elliptic_pp_gatv2_focal` |
| D9 | V-A "not winning as…" reverses its own logic | Rewrite after B3 | B3 |
| D10 | Fig. 2 "~2% positives" vs prevalence 0.065 | Label the denominator. Also fix "6 public datasets" (the paper says five datasets in six views) and the text that overflows a box. | figure script |
| D11 | Abstract promises code but gives no link | Add the URL (L3) | — |
| D12 | Acknowledgements placeholder | Fill in from your content | — |

Found during Phases 1 and 2, proposed for the same pass:

| ID | Issue | Fix | Source |
|---|---|---|---|
| D13 | The stored queues come from other models (Section 0.2) | Rebuild; re-copy the V-B, V-E and VI numbers | R6 |
| D14 | Repo docs disagree with the paper: weighted CE 0.4435 vs 0.4388; injection 0.9275 vs 0.92; probes 0.1501/0.2843 vs 0.1502/0.2841; "never pays at ≤ 500 labels" | Update `docs/reproducibility.md` and the model card to the artifacts (Q12) | artifacts |
| D15 | Table III has no committed config or script | `significance_elliptic_pp.yaml` | B2 |
| D16 | Appendix A lists 20 configs; 24 are missing, and 15 of those produce numbers the paper quotes: the four seed-0 GATv2 arms, `ensemble_elliptic_pp`, `baselines_mendeley_b4_precomputed`, the actor model and queue, the procurement and García Italy queues, `sensitivity_mendeley_eu`, and the four `explanations_*` runs | Complete Appendix A for every quoted number | all |
| D17 | The paper says the CI guard protects Appendix A; it actually protects `docs/reproducibility.md`, and checks names only | Extend the test to the paper (Q13), or reword | — |
| D18 | The queues, bundles and explainer ablation are seed-0 results but are not labelled | Label them as seed 0 | R6 |
| D19 | The label-efficiency wording | "Almost every budget below 1,000 labels is negative." The exceptions are +0.002 at k = 100 (procurement→financial) and +0.002 at k = 500 (financial→procurement, whose label pool is 638). | label-efficiency artifacts |
| D20 | Fig. 3's band uses the population SD; the tables use the sample SD | Use the sample SD in the figure | figure script |
| D21 | Table I's actor row gives test-window counts and test prevalence | Label them as test-window values | actor queue |
| D22 | The Section VI sanity sentence mixes two measures | B8 definitions | B8 |
| D23 | "Calibration … roughly an order of magnitude more than any architectural decision": 0.471 against 0.194 is 2.4× | Drop "order of magnitude"; this is part of the A3 calibration row | significance; ablations |
| D24 | Found during the revision. III-F says removing test-time re-normalisation moved GATv2 from 0.693 to 0.532. Both figures come from the July ledger, the drop came from a 30-finding fix pass, and the isolating ablation was never run | Add a `normalisation: per_graph` measurement switch to the trainer and run `gnn_elliptic_pp_gatv2_focal_pergraphnorm_multiseed.yaml` (5 seeds); report its result against the 5-seed headline, whatever it is. **Done 2026-11-15, method changed:** the switch reaches only the test graph, so the arm trains the frozen run's weights. Seed 0 was trained end to end as a cross-check; the five seeds come from re-scoring the stored checkpoints (`normalisation_rescore_elliptic_pp.yaml`), with guards that reproduce every stored validation and test value exactly. Result: 0.4729 ± 0.0525 → 0.6853 ± 0.0052 | new run |
| D25 | Found during the revision. V-B calls the actor head "stable across seeds" and quotes seed-0 AUC-PR 0.2473. The only multi-seed evidence is a three-seed laptop-C run (0.326 ± 0.078) with no committed config or artifact | Run `gnn_elliptic_actor_rgcn_multiseed.yaml` (5 seeds); quote mean ± SD and the P@100 range | new run |
| D26 | Found during the revision. IV-A describes B4 as the bid-price screens (coefficient of variation, spread, kurtosis, relative distance), but the committed B4 is a composite of award screens (awards, market share, buyer HHI); bid-price screens need losing bids, which Mendeley lacks, and no config uses them | Describe B4 as it runs | `baselines_mendeley_eu`, `baselines_mendeley_b4_precomputed` |
| D27 | Found during the revision. Table I gave AMLworld 515,080 accounts, the number of distinct account IDs; the IR (and every experiment) uses 515,088 accounts, each an ID paired with its bank | Use 515,088 and explain the difference in the datasheet | AMLworld ingest |

### 5.3 Part E — reference verification

- **Method.** Each reference is checked against its publisher page (DOI landing page, journal or proceedings site) or the official text (EUR-Lex, the UAE legislation portal, the OECD library). For each, I record authors, title, venue, volume, issue, pages or article number, year, DOI and the URL checked. The record goes in `paper/references_check.md` on the branch. Verified entries are stored as BibTeX now, so the Springer move in Phase 4 is mechanical.
- **Fixes to the existing list:**
  - [3]: volume and article number.
  - [8]: the KDD 2023 paper.
  - [11] and [14]: authors, volume and pages.
  - [12] and [13]: published versions, if they exist.
  - [22]: replace it with a citable source for the 90–95% figure.
  - [28]: retitle it as draft guidelines, dated 19 May 2026.
  - [4]: keep only if no stronger source makes the same point.
  - [26] and [27]: Official Journal citations.
  - [29]: the official text of Federal Decree-Law No. 6 of 2025, Article 149.
  - [25]: the OECD 2025 guidelines, with page numbers for the 13% and 20% figures.
- **Additions:**
  - Wachs, Fazekas and Kertész (2021).
  - Huber and Imhof (2019).
  - Agarwal et al. (2023).
  - Weber et al. cited a second time, for random forest beating GCN.
  - Two to four citations each for the three uncited Section II paragraphs. The arXiv IDs listed in `docs/paper_blueprint.md` are checked first, and nothing goes in without a verified record.
  - Target: 45–60 references.
- **Disagreements are reported, not resolved silently.** A first look today used secondary sources only:
  - Regulation (EU) 2026/1744 matches the brief: published in the OJ on 24 July 2026, in force on 27 July 2026, Annex III from 2 December 2027 ([White & Case](https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act), [Cuatrecasas](https://www.cuatrecasas.com/en/portugal/intellectual-property/art/digital-omnibus-ai-has-been-published)).
  - The draft guidelines date from 19 May 2026. Sources give the consultation close as 23 June 2026, later extended to 23 July 2026 ([William Fry](https://www.williamfry.com/knowledge/eu-publishes-draft-guidelines-on-classification-of-high-risk-ai-systems/), [Jones Day](https://jonesday.com/en/insights/2026/06/draft-eu-guidelines-clarify-when-ai-systems-are-highrisk-under-the-ai-act)). I found no final version yet.
  - All of this is re-checked against EUR-Lex and the Commission's page in Part A1.

### 5.4 Part F — abstract, sentences, figures

- **Abstract.** 200–250 words (or the journal's limit), in the brief's order: problem, what was built, three findings with numbers, what is released. All numbers come from the final runs. The copilot gets one clause or none. The repository URL follows L3.
- **Sentence fixes.** All eleven rows of the brief's table. In the missing-spaces row, "settings.The" and "run.We" are real, but "therules" is not in the `.tex`; it is an artifact of extracting text from the PDF at a page break. Every other row is real. A check script then flags contractions, sentences over 25 words, double spaces and stray punctuation in the `.tex`.
- **Figures.** All are regenerated by `scripts/paper_figures.py` from the artifacts.
  - **Format (Q14):** vector PDF with TrueType fonts embedded, sized to the template's column width. Every text element is at least 8 pt at print size. An earlier team decision preferred PNG so the figures could be edited in Canva.
  - **Greyscale:** distinct line styles and markers, hatching where colour separates categories, and colours that differ in lightness. Each figure is converted to greyscale and checked.
  - **Per figure:**
    - Fig. 1: font size only.
    - Fig. 2: denominator label, "five datasets, six views", box overflow.
    - Fig. 3: the B3 line.
    - Fig. 4: the "no transfer" label now overlaps the Japan bar; CI whiskers; country names per Q8.
    - Fig. 5: the full-label point.
    - Fig. 6: the "(%)" escaping, the annotation moved off the curve, the 5-seed curve.
    - Fig. 7: removed with the Section VII cut.
  - **File names and location:** the PDFs go to `paper/figures/`, named by their printed number (e.g. `fig1_two_ledgers.pdf`). The seven root PNGs belong to the old manuscript. They are removed in the final clean-up commit, after the README's Overleaf note is updated; git keeps the history.

---

## 6. Part G — now, and after the journal is confirmed

**Now (no journal needed):**
- **Data availability text:** the five datasets with canonical links and the licences recorded in the manifests (each licence text checked in Part E).
- **Licence check of released artifacts:**
  - The repository does not commit `eval_outputs/` (alerts, bundles, `serving.json`); the `.gitignore` and the hygiene tests both enforce this.
  - I will also check the docs, notebooks, frontend fixtures, `Report.pdf` and any public deployment for redistributed García rows. García is CC BY-NC-ND 4.0, which forbids sharing modified material. Findings will be reported.
- **AI-use disclosure, drafted for your confirmation:**
  - It names the copilot's LLM.
  - It states the AI help used in writing, including this revision, which used Claude, an AI model by Anthropic.
  - The repository's working files (`PROGRESS.md`, `handoff-prompt.md`, `.claude/`) suggest AI coding assistants also helped build the system and draft the first manuscript. Please confirm what to disclose.
- **Facts for item 19:**
  - `Report.pdf`: an SP Jain Deep Learning course report, August 2026, 63 pages, quoting 0.5492 and 0.4729.
  - The GitHub repository: created 13 July 2026 and public today. Internal notes say it was private from 19 July. It holds the earlier paper draft and docs with the numbers.
  - Anything else you know of (preprint, conference).
  - The wording, and what goes in the cover letter, are decided by you and Dr. Garg (L4).

**After the journal is confirmed (Phase 4):**
- Download the Springer Nature LaTeX template (`sn-jnl`) from Springer, with your OK.
- Numbered references, 4–6 keywords, the journal's abstract limit.
- A Declarations section: Funding, Competing interests, Data availability, Code availability, Author contributions (CRediT), Ethics approval ("not applicable": public data, no personal data). Placeholders wherever content is missing.
- Re-size the figures to the template's column width.

---

## 7. Questions and decisions

**Your decisions (14 November).** Q1–Q5 and Q10 are your answers. For the others you asked me to proceed without further approval, so the recommended option applies, with one change: Q6, explained below.

| Q | Decision | Status |
|---|---|---|
| Q1 | Rebuild both queues from the configs the paper names, report what comes out, and fix the demo script | **Yes** ("whatever it takes") |
| Q2 | Torch runs (B7; B8's explainer training; B6 only if the stored encoder cannot be reused) | **Run on this machine.** The main machine can send anything needed. |
| Q3 | Nested artifacts | **Move**, do not copy. Overwrite protection is in Section 4. |
| Q4 | B3 local features | **Fixed:** Weber et al.'s 94 local columns, time step included |
| Q5 | XGBoost settings | **Fixed:** subsample 0.8 and colsample_bytree 0.8, set in advance; applied to every XGBoost row in Tables II and IV, including +screens |
| Q6 | B3 in the fusion | **Included** as a two-member calibrated fusion, GATv2 + B3 (Section 3, B2). I changed this from "skip" because you asked for whatever makes the paper ready, and the brief expects reviewers to ask. |
| Q7 | Bootstrap | Per seed pair plus seed-averaged scores; keep the seed-0 rows for continuity |
| Q8 | Country names | Search for a published mapping. If none exists, keep `country_1`…`country_7` and mark the item open. |
| Q9 | B6 comparators | All four, with in-domain XGBoost as the main one |
| Q10 | B7 settings | **Fixed:** alternative validation window (steps 32–34) included; ε = 0.1, weight decay 5e-3, dropout 0.5, patience 5 |
| Q11 | Procurement budget | P@18 throughout |
| Q12 | Repo docs | Update `docs/reproducibility.md` and the model card to the revised numbers |
| Q13 | CI guard | Extend it to the config names in the paper's Appendix A |
| Q14 | Figures | Vector PDF |
| Q15 | Ledger | One `PROGRESS.md` entry per part |
| Q16 | Branch | `paper/journal-revision` |

**Still needed from the main machine** (does not block any run): its CPU model, RAM and OS, for the Part C compute statement.

**For Dr. Garg** (lead author). I will not decide these:

| L | Decision |
|---|---|
| L1 | Target journal: IJDSA, with SNAM as backup. This gates Phase 4. |
| L2 | Whether to run the fallback rater study. Raters must not be co-authors. |
| L3 | Repository availability wording. The repo is public today; archive it with a DOI? |
| L4 | Disclosure of earlier versions (course report, public repository, any preprint) and the cover-letter text |
| L5 | The authors' stance in the A1 legal framing. I verify the sources; the position is yours. |
| L6 | Approval of the revised version by all five co-authors |

**Placeholders unless you supply content:** Funding, Competing interests, Author contributions (CRediT) and Acknowledgements.

---

## 8. Risks

1. **The queue defect (0.2).** P@k, coverage, sensitivity, bundle counts and explainer numbers may change, and so may Fig. 2's text.
2. **B1.** If the trees also collapse at step 43, RQ1 must be reframed: the gap then sits in steps 35–42.
3. **B3.** B2-local may fall well below 0.81. "Trees win" would then become "trees with neighbourhood aggregates win", which is a different claim but still reportable.
4. **B4.** A label or score inversion would change the R-GCN numbers, Table IV and the procurement queue.
5. **B5.** The pooled or size-weighted Mendeley lift may be about 1; weighting Table VI by size gives 0.99. "Transfer works" would then hold for García only.
6. **B6.** The probe will fall far short of the in-domain models, and the abstract's transfer claim shrinks accordingly.
7. **Compute.** B7 takes about 15–30 CPU hours here. Sleep or updates can interrupt it; runs resume from the last finished seed. I will ask you to keep the laptop awake for that stretch.
8. **Machine class.** Torch reruns here may not match master. Mixed-machine comparisons are either avoided or labelled.
9. **External sources may disagree with the brief.** Examples: the consultation date; a final version of the Commission guidelines; OECD page numbers that do not show the exact figures.
10. **References.** Growing to 45–60 verified entries takes time, and nothing is added without verification.
11. **Country names** may be impossible, which would leave that part of B5 open.
12. **The copilot gate cannot be rerun here** (no NVIDIA key). The brief only asks for a wording change, so the risk is low.
13. **Figure format** conflicts with the earlier Canva workflow (Q14).
14. **Length grows** with the new tables (B1, B7, B8, Part C). The Section VII cut offsets part of it.
15. **Single copy of the artifacts.** The artifacts were moved, so an overwrite would lose master's outputs. Section 4's redirection and backups prevent this, and nothing writes into an existing folder without a backup.
16. **The copilot gate is from 19 August.** It ran against the serving artifacts of that date, and the queue rebuild changes those artifacts. It cannot be rerun here, so the paper states its date. The main machine could rerun it later with its NVIDIA key.
17. **The explanation history sentence may lose its basis.** "38 of 50 down to 1" compared old GNNExplainer bundles with PGExplainer bundles from the old queue. After the rebuild, B8 compares both explainers on the same 50 alerts, and that comparison replaces the history sentence.

### 8.1 Brief items that cannot be done exactly as written

These stay in the plan. Each is either done in the nearest honest form or marked open with its reason.

| Brief item | Why not as written | What I do instead |
|---|---|---|
| B5: "Replace country_1 to country_7 with the real country names, since the data are public" | The public Mendeley file contains only `country_1`…`country_7` (checked in the downloaded file). | Look for a published mapping (Mendeley record, companion paper). Without one, keep the labels and mark the item open (Q8). |
| B6: "Document how an encoder trained on procurement features ingests Elliptic's 166 anonymised features" | No encoder ingests the raw features. Both domains pass through the shared structural template. | Document the shared template, and add a raw-feature comparator so the requested comparison exists. |
| B7 step 2: "Rerun with a temporal validation window" | Validation is already the temporal window of steps 30–34. | State the split. Offer one alternative window as a sensitivity check (Q10). |
| Part F: "therules" | Not in the source; it is an artifact of extracting text from the PDF at a page break. | No change needed. The other ten sentence fixes are real and will be made. |
| Part D: fold prevalence "0.25–0.89 … Table VI implies 0.29–0.89" | Both ranges are correct: 0.29–0.89 is Mendeley alone; 0.25–0.89 includes García America (0.250). | Name the scope at each place instead of changing a number. |
| Part B: "all runnable from the existing configs" | B1, B2, B3, B4, B5, B6, B7 and B8 each need new configs, and most need small code changes (Section 3). | Make the code changes, with tests, in step 3.4. |

---

## 9. Traceability

Every new config also gets a row in Appendix A and in `docs/reproducibility.md`; the CI guard requires the latter.

| # | Planned change | Files touched | Configs added | Change-log line (draft) |
|---|---|---|---|---|
| 1 | Open Section I with the problem; present AI Act logging, oversight and explanation as a standard to meet; remove the 5(b) claim; verify CBUAE Art. 149; cite [28] as non-binding draft guidelines; OECD page numbers | `paper/collusiongraph_paper.tex` (I, VIII, references) | — | Rewrote the openings of Sections I and VIII; removed the 5(b) claim; cited the OJ text, the draft guidelines and Art. 149 |
| 2 | Two lead contributions; LOCO/LOMO under RQ2; RQ2 wording matched to what was run; RQ3 rebuilt on fidelity and coverage; RQ1 answered "no"; unsupervised cost +0.0295 | `.tex` (I, V, VI, IX) | — | Narrowed the contributions to two; moved LOCO/LOMO to RQ2; reworded RQ2 and RQ3; stated the RQ1 answer |
| 3 | Section VII becomes two sentences in Future Work; Fig. 7 removed | `.tex`, `scripts/paper_figures.py` | — | Cut Section VII to one Future Work paragraph; removed Fig. 7 |
| 4 | The eight A3 claims rewritten; number rows filled from B2, B5, B6 and B7 | `.tex` (abstract, V, IX, conclusion) | — | Rewrote eight overstated claims; numbers from B2, B5, B6 and B7 |
| 5 | B3 line in Fig. 3; pre/post-step-43 table | `baseline_run.py`, `eval/tables.py`, figure script, `.tex` | (shares B2's config) | Added the B3 per-step curve and a pre/post-step-43 table |
| 6 | Seeded XGBoost; Tables II and IV as mean ± SD; per-seed-pair bootstrap; GATv2 + B3 calibrated fusion | `training/multiseed.py`, new significance and fusion runners, `cli.py`, `eval/tables.py`, `.tex` | `baselines_elliptic_pp_multiseed`, `baselines_mendeley_eu_multiseed`, `baselines_mendeley_screens_ablation_multiseed`, `significance_elliptic_pp`, `significance_elliptic_pp_multiseed`, `baselines_elliptic_pp_calib_multiseed`, `fusion_gatv2_b3_multiseed` | Ran XGBoost over five seeds; redid the paired bootstrap for every seed pair; added B3 to a calibrated fusion |
| 7 | Local-feature B2/B3 rows; V-A paragraph rewritten | `baseline_run.py`, `.tex` | `baselines_elliptic_pp_local_multiseed` | Added local-feature-only B2/B3 rows; rewrote the V-A paragraph |
| 8 | One diagnosis per below-chance case; fixes and reruns if a bug is found | `eval/diagnostics.py`, `.tex` | `diagnose_below_chance` | Diagnosed the four below-chance results |
| 9 | Pooled and size-weighted lift; per-fold CIs; country names if a source exists | `eval/transfer_summary.py`, `eval/tables.py`, figure script, `.tex` | `transfer_pooled_lift` | Added pooled and size-weighted lift with per-fold 95% CIs |
| 10 | Full-label comparison; Fig. 5 point; abstract sentence | `training/transfer_run.py`, figure script, `.tex` | `cross_domain_full_label_comparison` | Compared the frozen probe with raw-feature models at full labels |
| 11 | Validation split stated; 5-seed noise curve; four-regulariser table | `training/losses.py`, figure script, `.tex` | `label_noise_elliptic_pp_5seed`, `gnn_elliptic_pp_gatv2_focal_{ls,wd,do,es}_multiseed`, (`…_valwin_multiseed`) | Stated the temporal validation split; reran the noise curve on five seeds; compared it with four regularisers |
| 12 | Fidelity+, Fidelity− and sparsity table; definitions | `explain/explainer_ablation.py`, `.tex` | `explainer_metrics_elliptic_pp` | Added Fidelity+, Fidelity− and sparsity for three explainers |
| 13 | Methods details per Section 5.1 | `.tex` (Section IV or a methods appendix) | — | Added the methods details a reviewer needs to judge fairness |
| 14 | D1–D23 | `.tex`, `docs/reproducibility.md`, `docs/model_card.md`, figure script, `scripts/build_demo_artifacts.py`, `configs/experiment/alert_queue_mendeley_eu.yaml` (`scores_dir` pointed at the stored R-GCN `seed_0`), `backend/tests/unit/test_repo_hygiene.py`, `paper/numbers_manifest.yaml`, `scripts/audit/verify_numbers.py` | from the B runs and R6 | Fixed the 12 listed inconsistencies and 11 more found during the checks |
| 15 | Verified and extended references (45–60) | `.tex` / `.bib`, `paper/references_check.md` | — | Fixed and extended the references to N verified entries |
| 16 | Abstract of 200–250 words; language pass on Sections I–II | `.tex` | — | Rewrote the abstract; language pass on Sections I–II |
| 17 | Fig. 6 fixed and Fig. 7 removed; all figures vector, ≥ 8 pt, readable in greyscale | figure script, `.tex` | — | Fixed Fig. 6 and removed Fig. 7; all figures vector, at least 8 pt, greyscale-safe |
| 18 | Springer `sn-jnl` template; declarations with placeholders | new manuscript files under `paper/` | — | Moved to the Springer template; added the declarations |
| 19 | Disclosure text in the declarations and the cover-letter note | `.tex`, cover-letter note | — | Disclosed the earlier course report and the public repository numbers (wording per L4) |

---

## 10. Audit log (14 November, after your answers)

I checked every claim in this plan against the code and the stored artifacts. These 21 errors or gaps were found and fixed.

| # | Section | What was wrong | Fix |
|---|---|---|---|
| 1 | 0.1 | Said the LOMO matrix reproduced "byte for byte" across machines | The record says "exact at recorded precision"; the wording now says so |
| 2 | 0.2 | Said the alert counts "cannot change" after the rebuild | The counts depend only on Leiden and the size cap, which is checked rather than assumed: "should not change; R6 checks" |
| 3 | 2.1 | Listed the calibration claim as number-free | The B3-in-fusion run can change it; moved to the number-bearing rows |
| 4 | 2.1 | Listed the RQ3 answer as number-free | Its fidelity and coverage numbers come from R6 and B8; now marked pending |
| 5 | 2.1 | The copilot interval (Wilson 95% CI) would have been computed by hand | Now produced by a committed config |
| 6 | 2.2, 2.4 | The "never retype" check came only at the end | A numbers manifest and checker are built in step 3.4 and used in every content part |
| 7 | 2.4 | Planned to reuse `scripts/audit/verify_numbers.py` | It hard-codes master's `D:` path; it is rewritten to read the manifest |
| 8 | 3, B1 | The "pre/post-43 AUC-PR" was undefined | Defined: pooled-window AUC-PR, and the mean of the per-step values, both labelled |
| 9 | 3, B2 | Said R1 confirms all XGBoost runs are machine-independent | R1 covers only the unsubsampled runs; the seeded runs are recorded as run here |
| 10 | 3, B2 | The role of the existing deterministic tree configs was unstated | They stay as reproducibility anchors in Appendix A; the tables report seeded runs |
| 11 | 3, B2 | The B3-in-fusion design assumed stored member validation scores | The ensemble stores test scores only; the design is now a two-member GATv2 + B3 fusion, with no machine mixing |
| 12 | 4 | Assumed a copied reference set | You chose a move; reruns are redirected to `_repro/`, and replacements are backed up to `_superseded/` first |
| 13 | 4 | No check for the new significance runner | Added R8: it must reproduce today's `significance.json` exactly |
| 14 | 5.1 | Fusion described as a plain "calibrated mean" | Equal-weight mean of isotonic-calibrated members (`models/ensemble.py`) |
| 15 | 5.1, 8 | The copilot gate's dependence on old artifacts was not mentioned | The gate's date is stated; it cannot be rerun here |
| 16 | 5.2, D16 | Said "at least 9" quoted runs are missing from Appendix A | The count is 15, now listed by name |
| 17 | 5.4 | Said "ten" of the brief's sentence fixes are real | The missing-spaces row holds two real fixes and one non-issue; every other row is real |
| 18 | 5.4 | The figures' file location and the root PNGs were unaddressed | Figures go to `paper/figures/*.pdf`; the root PNGs are removed at clean-up |
| 19 | 8 | The "38 of 50 down to 1" history depended on the old queue | B8's same-alerts comparison replaces it |
| 20 | 8.1 | The brief's "all runnable from the existing configs" was not flagged | Added: B1–B8 all need new configs, and most need small code changes |
| 21 | 9 | The Mendeley queue config change was missing from the files touched | Added, with the hygiene test, the manifest and the checker |
