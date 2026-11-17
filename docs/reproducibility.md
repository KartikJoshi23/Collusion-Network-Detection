# Reproducibility Package (§7 step 33, M8)

*The paper's reproducibility statement, in executable form. Every published
number maps to exactly one committed config; a hygiene test enforces that this
map and `configs/experiment/` never drift apart (bidirectionally). Headline
values quoted below are the ledger-recorded measurements (PROGRESS.md is the
running record; multi-seed = mean ± std over 5 seeds unless stated).*

## 1. Environment (frozen)

- Python 3.11 (`.python-version`), dependencies pinned in `uv.lock` — `uv sync`
  recreates the exact venv. Node 20+ with `frontend/package-lock.json` for the
  console.
- **Deliberate exclusion:** pyg-lib / torch-sparse are not installed on the
  Windows dev machines — `NeighborLoader` minibatching work (AMLworld) runs on
  a GPU/Linux machine only. Everything published to date is CPU, full-batch.
- Bootstrap: `uv sync` → `uv run pre-commit install` → `copy .env.example .env`
  → `uv run poe data` → `uv run poe test`.

## 2. Data (never redistributed)

`uv run poe data` downloads every dataset from its canonical source and
verifies byte-exact checksums against the committed manifests
(`data/manifests/*.json`, which also record licenses). AMLworld requires
per-machine Kaggle credentials (README). Per-dataset provenance and caveats:
`docs/datasheets/`.

## 3. The number → config map

Run any row with `uv run collusiongraph <verb> -c <config>` (the `train` verb
auto-dispatches on config shape). Outputs land in the gitignored
`eval_outputs/`; the ledger records the measured values.

### Elliptic++ (financial anchor; prevalence 0.065)

| Config (`configs/experiment/`) | Produces |
|---|---|
| `baselines_elliptic_pp.yaml` | B1 0.0576 / B2 0.8076 / B3 0.8104 AUC-PR, deterministic trees (byte-reproduce cross-machine); the paper now quotes B1 from here and B2/B3 from `baselines_elliptic_pp_multiseed.yaml` |
| `baselines_amlworld.yaml` | AMLworld HI-Small tree baselines at 5M-edge scale (added 2026-07-25 to settle whether this machine can train on it at all — it can, in 52 s on CPU). **Honest negative: B2 0.0063 / B3 0.0062 against prevalence 0.0103 — below chance** (with the post-window fence set in the 2026-11 revision; before it, 0.0064 / 0.0062 against 0.0104). Diagnosed in `diagnose_below_chance.yaml`: the node-first-seen cut falls one hour into the data, and in that hour the money-flow features carry almost no label signal (ROC-AUC 0.49–0.54, against up to 0.74 over the full window). B1 omitted (no agreed rule thresholds) |
| `injection_recovery_amlworld.yaml` | AMLworld in its DESIGNED role (§4.3 D2, "validating that the detector recovers known injected patterns") — five financial motif families planted into the real 5M-edge graph, no labels needed, giving the RQ2 finding a financial counterpart to the OCDS procurement study |
| `gnn_elliptic_pp_gatv2_focal.yaml` | headline GATv2-focal single-seed run (seed-0 0.5492 on the master class) |
| `gnn_elliptic_pp_gatv2_focal_multiseed.yaml` | the paper number: **0.4729 ± 0.0525** (5 seeds) |
| `gnn_elliptic_pp_gatv2_wce.yaml` / `gnn_elliptic_pp_gatv2_wce_multiseed.yaml` | −focal ablation: 0.4869 seed-0; **0.4388 ± 0.0505** (master; laptop-B measured 0.4435 ± 0.0615) — second-order |
| `gnn_elliptic_pp_sage_focal.yaml` / `gnn_elliptic_pp_sage_wce.yaml` | SAGE loss pair: 0.4743 vs 0.3882 (focal decisive on SAGE) |
| `gnn_elliptic_pp_gatv2_focal_unidir.yaml` | −bidirectional edges: 0.3549 (the strongest component ablation) |
| `gnn_elliptic_pp_gatv2_focal_multi.yaml` | raw+structural channels: 0.3781 (added channels hurt) |
| `gnn_elliptic_pp_gatv2_focal_line.yaml` | raw+line channel: 0.4986 (B-LG, not adopted) |
| `gnn_elliptic_pp_gatv2_focal_cf.yaml` | context-fusion arm (B-CF, not adopted) |
| `ensemble_elliptic_pp.yaml` | calibrated fusion seed-0 + members (unsup members ≤ prevalence) |
| `ensemble_elliptic_pp_multiseed.yaml` | **calibrated 0.4434 ± 0.0501 vs rank 0.0511 ± 0.0019** |
| `alert_queue_elliptic_pp.yaml` | M2-era SAGE queue (historical first queue) |
| `alert_queue_elliptic_pp_ensemble.yaml` | the published queue: 254 alerts, P@50 0.32 |
| `gnn_elliptic_actor_rgcn.yaml` / `alert_queue_elliptic_actor.yaml` | seed-0 actor view: AUC-PR 0.2473, node P@100 0.98; its queue: 2,514 alerts, tie-aware P@50 0.08 |
| `explanations_elliptic_actor.yaml` | 20/20 matcher bundles over the actor queue — **15 with motif + FATF flags** (added 2026-07-25: the dashboard audit found the actor dataset served 50 alerts with zero bundles) |
| `injection_recovery_elliptic_pp.yaml` | M3 injection-recovery report (floor catches common_control 1.0) |
| `explanations_elliptic_pp.yaml` | 50/50 PGExplainer bundles |
| `explainer_ablation_elliptic_pp.yaml` | the §7-27 three-arm fidelity ablation (PGExplainer adopted) |
| `sensitivity_elliptic_pp.yaml` | NMS/hit-rule grid (queue protocol-robust) |
| `label_noise_elliptic_pp.yaml` | the three-seed noise curve: clean 0.4827 ± 0.0616 → 20% 0.5978 ± 0.0248 (seeds 0–2; the paper now uses the five-seed curve) |

Paired-bootstrap significance rows of the first version (calibrated-vs-rank
Δ +0.471 CI [0.440, 0.499]; GATv2-vs-B3 Δ −0.261 CI [−0.285, −0.235]; the
revision's per-seed rows come from `significance_elliptic_pp_multiseed.yaml`)
regenerate with `uv run collusiongraph eval -c
configs/experiment/significance_elliptic_pp.yaml`, which runs
`collusiongraph.eval.significance.compare_score_files` over the stored score
parquets. (Until the revision, no committed config produced them, and the
demo script only links the stored file.)

### Mendeley EU (procurement anchor; within-sample prevalence 0.358)

| Config | Produces |
|---|---|
| `baselines_mendeley_eu.yaml` | B1 0.3426 / B2 0.3925 / B3 0.3775 / B4 0.3811 (deterministic trees; the paper quotes B2/B3 from `baselines_mendeley_eu_multiseed.yaml`) |
| `baselines_mendeley_b4_precomputed.yaml` | B4 + dataset screens: 0.3874 (wash-to-negative at the queue head) |
| `baselines_mendeley_screens_ablation.yaml` | B2+screens 0.4558; B3+screens 0.3450 (deterministic; the paper quotes `baselines_mendeley_screens_ablation_multiseed.yaml`) |
| `gnn_mendeley_rgcn.yaml` / `gnn_mendeley_rgcn_multiseed.yaml` | the honest negative: 0.2731 seed-0; **0.2808 ± 0.0087, seed-stable below prevalence** |
| `transfer_loco_mendeley.yaml` | single-fold LOCO (country_5: 0.8025…, byte-reproduces cross-machine) |
| `transfer_loco_matrix_mendeley.yaml` | full 7×5 LOCO matrix: macro lift 1.17, largest market fails (0.90); pooled lift in `transfer_pooled_lift.yaml` |
| `alert_queue_mendeley_eu.yaml` | the published queue: 223 alerts; the top 129 tie at calibrated risk 1.0, so tie-aware P@18 is 0.40 against 0.39 for a random order (item D28) |
| `explanations_mendeley_eu.yaml` | 20/20 matcher bundles (no learned attribution — R12) |
| `sensitivity_mendeley_eu.yaml` | protocol-sensitivity grid: flat under NMS; the hit rule moves P@18 from 0.40 to 0.39 and 0.37 |

### García Rodríguez / cross-domain / OCDS

| Config | Produces |
|---|---|
| `transfer_lomo_matrix_garcia.yaml` | 4×5 LOMO matrix: macro lift 1.57, positive on every market (Italy P@10 1.00); pooled lift in `transfer_pooled_lift.yaml` |
| `alert_queue_garcia_italy.yaml` | dashboard queue over the Italy LOMO fold (market-based `test_group`, precalibrated): 3 alerts, all confirmed cartels |
| `explanations_garcia_italy.yaml` | 3/3 matcher bundles over that queue — 0 motifs (its communities are 2-firm, too small to contain a shape; honest, not a failure). Added 2026-07-25 by the dashboard audit |
| `cross_domain_probe_proc2fin.yaml` | frozen-probe proc→fin: 0.1502 vs 0.065 prevalence (reproduces exactly with the stored encoder) |
| `cross_domain_probe_fin2proc.yaml` | frozen-probe fin→proc: 0.2841 on master, 0.2843 on laptop-B and the revision laptop, < 0.358 prevalence (negative) |
| `label_efficiency_proc2fin.yaml` / `label_efficiency_fin2proc.yaml` | label-efficiency curves: transfer never pays at ≤500 target labels, either direction |
| `injection_recovery_ocds_georgia.yaml` | at-scale injection, seed 0 (163,327-node window) |
| `injection_recovery_ocds_georgia_multiseed.yaml` | the paper verdict: coordinated_cluster **0.9225 ± 0.1733 @2000** (printed 0.92 ± 0.17; laptop-B measured 0.9275 ± 0.162); award-pattern motifs evade |

### Studies & serving

| Config | Produces |
|---|---|
| `practitioner_study.yaml` | §10.3 rater packets + manifest (runbook: `docs/practitioner_study.md`) |

Demo/serving artifacts rebuild with `uv run poe demo-artifacts` (twice — the
second pass wires explanations into `serving.json`); the Copilot goldens gate
is `uv run poe copilot-goldens` (needs `NVIDIA_API_KEY`).

### Journal revision (2026-11, branch `paper/journal-revision`)

Added for the revision brief (`revision-plan.md`). Values are filled in from
the run outputs once each run completes; nothing here is typed from memory.

| Config | Produces |
|---|---|
| `baselines_elliptic_pp_multiseed.yaml` | B2, B3 over seeds 0–4 (subsample/colsample 0.8) with per-step metrics: Tables II, III; Fig. 3 (items B1, B2) |
| `baselines_elliptic_pp_local_multiseed.yaml` | B2-local, B3-local (94 local columns): Table II rows (item B3) |
| `baselines_mendeley_eu_multiseed.yaml` | Mendeley B2, B3 over seeds 0–4: Table IV (item B2) |
| `baselines_mendeley_screens_ablation_multiseed.yaml` | Mendeley B2+screens, B3+screens over seeds 0–4: Table IV (item B2) |
| `baselines_elliptic_pp_calib_multiseed.yaml` | B3 trained on steps 1–29, input to the fusion below (item B2) |
| `fusion_gatv2_b3_multiseed.yaml` | GATv2 + B3 calibrated fusion vs each member (item B2) |
| `significance_elliptic_pp.yaml` | Table III seed-0 bootstrap, the committed source of the stored `significance.json` |
| `significance_elliptic_pp_multiseed.yaml` | paired bootstrap for every seed pair, plus seed-averaged scores (item B2) |
| `diagnose_below_chance.yaml` | below-chance diagnostics: inverted-score AUC-PR, label encoding, split facts, feature shift, and per-window feature-label ROC-AUC (item B4) |
| `gnn_mendeley_rgcn_nocomm_multiseed.yaml` | diagnostic ablation: the Mendeley R-GCN without the two component features, a test of the component-size explanation (item B4; not in the brief) |
| `transfer_pooled_lift.yaml` | pooled and size-weighted lift, per-fold 95% CIs (item B5) |
| `derived_numbers.yaml` | copilot grounding Wilson CI, probe lift, pre/post-step-43 AUC-PR (items A3, B1), and the same windows for the per-graph pass (D24), each noise rate and each regulariser arm (B7) |
| `label_noise_elliptic_pp_5seed.yaml` | label-noise curve on seeds 0–4 (item B7): test 0.4729 ± 0.0525 clean → 0.5646 ± 0.0456 at 10% → 0.5507 ± 0.0690 at 20%; validation 0.9380 → 0.5642. The clean runs are the headline runs. Seeds 0–2 reuse the stored master runs, since this machine reproduces master's GATv2 bit for bit (check R7); seeds 3–4 are new |
| `gnn_elliptic_pp_gatv2_focal_ls_multiseed.yaml` | regulariser arm: label smoothing ε = 0.1 (item B7): test 0.4585 ± 0.0344, validation 0.9387, 2/5 seeds above clean |
| `gnn_elliptic_pp_gatv2_focal_wd_multiseed.yaml` | regulariser arm: weight decay 5e-3, ten times the headline (item B7): test 0.5403 ± 0.0286, validation 0.8996, 5/5 seeds above clean; steps 35–42 0.6588. Seeds 4 to 0 were trained by a scratchpad copy of this config with the seed list reversed, in a second process; this config then rewrote `multiseed.json` in seed order, skipping every trained seed (per-seed records identical; aggregates within 2.2e-16) |
| `gnn_elliptic_pp_gatv2_focal_do_multiseed.yaml` | regulariser arm: dropout 0.5 (item B7): test 0.4874 ± 0.0362, validation 0.9419, 4/5 seeds above clean |
| `gnn_elliptic_pp_gatv2_focal_es_multiseed.yaml` | regulariser arm: early-stopping patience 5 (item B7): test 0.4224 ± 0.0589, validation 0.8913, 0/5 seeds above clean |
| `gnn_elliptic_pp_gatv2_focal_valwin_multiseed.yaml` | alternative temporal validation window (item B7): loss on steps 1–31, validation on 32–34; test 0.4772 ± 0.0468, validation 0.9583, 2/5 seeds above clean (validation not comparable) |
| `explainer_metrics_elliptic_pp.yaml` | Fidelity+, Fidelity−, sparsity and arm overlap for three explainers on the rebuilt queue (item B8) |
| `cross_domain_full_label_comparison.yaml` | full-label comparison of the frozen probe (stored encoders), a structural probe, a probe on B2's inputs, and five-seed B2 (item B6) |
| `gnn_elliptic_pp_gatv2_focal_pergraphnorm_multiseed.yaml` | per-graph normalisation trained end to end, seed 0 only: the cross-check of the re-scoring runner (identical test scores, 0.6919; item D24; not in the brief) |
| `normalisation_rescore_elliptic_pp.yaml` | re-scores the five stored GATv2 checkpoints with frozen and with test-graph statistics: 0.4729 ± 0.0525 → 0.6853 ± 0.0052, p ≤ 0.001 on every seed; the gain lies in steps 35–42 (item D24; not in the brief) |
| `gnn_elliptic_actor_rgcn_multiseed.yaml` | actor-graph R-GCN over seeds 0–4: AUC-PR 0.3400 ± 0.0632 (0.2473 to 0.4033); node P@100 0.98 for seed 0 and 1.00 for seeds 1–4 (item D25; not in the brief) |
| `alert_queue_elliptic_actor_multiseed.yaml` | the actor queue rebuilt from each seed's scores over the same communities: tie-aware P@50 0.14 ± 0.03; seed 0 reproduces the stored queue alert for alert (item D25) |

## 4. Seeds & determinism (measured, not assumed)

- Every config carries an explicit `seed:`; multi-seed campaigns run seeds
  0–4 and are resumable (completed seeds are never retrained).
- **Byte-reproducible cross-machine (verified):** XGBoost baselines; the LOCO
  country_5 R-GCN fold; the García LOMO matrix (revision checks R1–R3, R5).
- **Frozen-encoder probes (revision check R4, corrected 2026-11):** with the
  stored encoder weights, procurement→financial reproduces exactly (0.1502),
  while financial→procurement gives 0.2843 against 0.2841 on master. The
  difference persists with identical weights and does not depend on the
  torch thread count, so it is CPU-level floating-point variation in the
  probe pipeline, not encoder retraining.
- **Torch GNN training is machine-class dependent:** measured GATv2 seed-0
  0.5492 (master class) vs 0.5318 (laptop-C), a ±0.02 machine-class
  variance. The revision laptop (Intel Core i5-11300H, 4 cores / 8
  threads, 16 GB, CPU only) reproduces master's GATv2 bit for bit: seed 0
  in check R7 (test AUC-PR 0.5492089151328867, best epoch 121), and seeds 3
  and 4 as the rate-0 points of `label_noise_elliptic_pp_5seed.yaml`
  (identical test scores, maximum difference 0.0), while two other trainings
  ran in parallel. Re-scoring the five stored master checkpoints here
  (`normalisation_rescore_elliptic_pp.yaml`) reproduces every seed's
  validation and test AUC-PR exactly. The actor R-GCN reproduces too: seed 0
  of `gnn_elliptic_actor_rgcn_multiseed.yaml` matches the stored master run of
  `gnn_elliptic_actor_rgcn.yaml` in every test score (292,102 wallets; AUC-PR
  0.2472721036304367, best epoch 13). The main machine reported by the user is an Intel Core
  i7-1195G7 (4 cores / 8 threads, 16 GB). Both are 11th-generation Intel
  Core (Tiger Lake) parts, which is consistent with the bit-identical
  results. Its NVIDIA MX450 is not used: every published number is a CPU
  run, and GPU arithmetic would not match.
- **Seed variance (±0.05) dominates machine variance (±0.02)** — the paper
  quotes multi-seed means with stds, never a best seed. Where a comparison
  crosses machines (the wce campaign), the ledger records the confound.

## 5. Protocol guarantees

Strict-inductive temporal splits, as-of feature computation, LOCO/LOMO entity
isolation, and the alert-unit rules are enforced by the §9.1 leakage suite —
run standalone with `uv run pytest backend/tests -m leakage` and as a
dedicated CI step on every push. One YAML = one experiment: no published
number exists without a committed config, and the repo-hygiene test
`test_repro_map_matches_configs` fails CI if this document and
`configs/experiment/` ever disagree in either direction.

## 6. Building the paper (two versions)

The paper exists in two versions with one source of content:

- `paper/collusiongraph_paper.tex` (IEEEtran) is the source. Edit only this file.
- `paper/collusiongraph_paper_springer.tex` is generated from it for the
  International Journal of Data Science and Analytics (Springer Nature `sn-jnl`
  class, two-column `iicol` layout, numbered `sn-mathphys-num` references,
  BibTeX from `paper/references.bib`, a Statements and Declarations section).
  Regenerate it with `uv run python scripts/paper_to_springer.py`; the hygiene
  test `test_springer_version_is_generated_from_the_ieee_source` fails if the
  two drift. The iicol column is narrower than an IEEE column, so in the
  Springer version every table spans the page and is scaled down only if it is
  still wider than the text; URLs may break at hyphens.
- `uv run python scripts/paper_to_springer.py --bundle` builds
  `paper/build/springer_upload/`, a flat folder (IJDSA accepts no subfolders)
  with the .tex, `references.bib`, the class, style and `cuted.sty` files and the
  figures, compiles it there with latexmk, and zips the sources with the .bbl
  into `paper/build/springer_upload.zip`.
- `sn-jnl.cls` and `sn-mathphys-num.bst` come unchanged from Springer Nature's
  journal-article template package (December 2024 version, LPPL 1.3c).
  `cuted.sty` (sttools v3.5, LPPL 1.3) was generated with docstrip from
  `cuted.dtx` on CTAN; the class needs it and MiKTeX did not have it.
- `uv run python scripts/audit/verify_numbers.py --strict` checks every printed
  number in both versions against its artifact.
