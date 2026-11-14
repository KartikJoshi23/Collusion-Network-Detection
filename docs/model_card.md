# Model Card — CollusionGraph Detection Stack

*Per Mitchell et al. (2019); §7 step 33, Milestone M8. Every number below is a
measured, ledger-recorded result (PROGRESS.md); multi-seed numbers are
mean ± std over 5 seeds unless stated. Last updated 2026-07-21.*

## Model details

One shared stack, two thin domain adapters (§3.2): unified graph IR →
supervised GNN + unsupervised anomaly arm + transparent structural floor →
per-member isotonic calibration → weighted fusion → community roll-up →
fixed-budget alert queue → explanation bundle per alert.

| Component | Financial anchor (Elliptic++) | Procurement anchor (Mendeley EU) |
|---|---|---|
| Supervised head | GATv2 (direction-flag edge features, focal loss) | R-GCN (relation-typed award graph, focal) |
| Unsupervised arm | DOMINANT-style + GAE-style GCN autoencoders | same (structural-template attributes) |
| Floor | mean positive per-graph z-score over the §4.2 structural template | same |
| Fusion | isotonic-calibrated weighted mean (rank fusion kept only as a measured ablation) | same |
| Explainer | PGExplainer (adopted §7 step 27: PyG sanity 49/50, fidelity-insane 1/50) + motif matcher + FATF flags | motif matcher + OECD flags (mask-based explainers are GATv2-only — R12 limitation) |

Developed as an academic capstone (TRL 3–4 validated prototype). Not a
production system.

## Intended use

**Screening signal only — no determination of guilt.** The system ranks
already-public, anonymized graph entities for *investigative prioritization
at a fixed alert budget*. Out of scope: any per-person output, any automated
adverse action, any use as evidence. The caveat is hard-coded into the API,
every explanation bundle, the UI footer, and the Copilot's release guard.

## Metrics & evaluation protocol

Precision@k / Recall@k / FPR@k at operational budgets, AUC-PR against the
prevalence baseline, alert-level queue metrics under an explicit alert unit
(hit rule + Jaccard-NMS dedup + size cap). Strict-inductive temporal splits,
as-of feature discipline, LOCO/LOMO entity isolation; leakage tests run in CI
(§9.1). Multi-seed (≥5) with paired-bootstrap significance for headline
comparisons.

## Results (headline, honest)

Values follow the journal revision (branch `paper/journal-revision`); each
comes from the config named in `docs/reproducibility.md`.

* **Elliptic++ (tx-level, test steps 35–49, prevalence 0.065):** GATv2-focal
  **0.4729 ± 0.0525** AUC-PR over five seeds (the seed-0 0.5492 is the best
  seed; tables quote the mean); queue head P@100 0.812 ± 0.238
  (seed-unstable). **XGB-Graph (B3) scores 0.8123 ± 0.0012 over five seeds**
  (subsample and colsample 0.8), far above the GNN mean: the GADBench
  finding, replicated and reported. Paired bootstrap per seed pair: Δ −0.264
  to −0.391, every p at the 0.001 floor (seed-0 paired bootstrap: Δ −0.264,
  95% CI [−0.288, −0.238]); on seed-averaged scores Δ −0.301
  [−0.324, −0.276]. The whole gap sits in steps 35–42 (B3 0.926 vs GATv2
  0.574); after the step-43 market closure both fall close to the base rate
  (0.057 vs 0.039 against 0.025).
* **Actor-level view:** seed-0 global AUC-PR 0.2473 with queue-head P@100
  0.98. A five-seed check is pending (`gnn_elliptic_actor_rgcn_multiseed.yaml`).
* **Calibrated fusion 0.4434 ± 0.0501** stays below its strongest member;
  naive rank fusion collapses to 0.0511 ± 0.0019 (seed-0 paired bootstrap:
  Δ +0.471, CI [0.441, 0.500]; seed-averaged Δ +0.444 [0.413, 0.474]).
  Calibrate-before-fusing is a measured requirement. Unsupervised members
  alone score at or below prevalence on Elliptic++ and cost 0.030 AUC-PR in
  the fusion. Adding B3 to a calibrated fusion does not help either (0.7760 ±
  0.0014 against 0.8012 ± 0.0034 for B3 trained on steps 1–29).
* **Mendeley EU (firm-level, within the case-control sample, prevalence
  0.358):** R-GCN **0.2808 ± 0.0087, below prevalence on every seed.** The
  diagnosis is a temporal reversal, not a bug: training firms are 87–89%
  cartel-linked against 36% in test, and the structural features rank licit
  firms higher before 2011 and cartel firms higher in test. The best
  firm-level tree is XGB + the dataset's own screens, **0.4547 ± 0.0081**; a
  linear probe on the award screens reaches 0.4752. Alert queues (seed 0):
  Elliptic 254 alerts, P@50 0.32; Mendeley 223 alerts, P@18 0.33. Both are
  NMS-invariant; the hit rule moves financial P@50 by 0.02.
* **Transfer:** García leave-one-market-out pools to lift 1.36 ± 0.15
  (size-weighted 1.53; every fold's 95% CI above 1). Mendeley
  leave-one-country-out pools to 0.93 ± 0.02 (size-weighted 0.99); its largest
  fold sits at 0.90 [0.87, 0.94]. Cross-domain transfer is asymmetric and
  weak: the procurement encoder reaches 0.1502 on Elliptic++ (2.3×
  prevalence), against 0.2991 for a probe on B2's inputs and 0.8039 for B2;
  financial→procurement reaches 0.2843, below prevalence. Below 1,000 target
  labels transfer never clearly helps (10 of 12 budgets negative).
* **Injection at scale (OCDS Georgia, 163k-node window):** structure-only
  unsupervised arms recover coordinated clusters at a 1.2% budget
  (0.92 ± 0.17 @2000 for the rank ensemble; common control 0.58 ± 0.04 for
  DOMINANT) and are nearly blind to award-pattern cartels (rotation,
  partition and cover bid ≤ 0.17 @2000).

## Ablations (component grid, §7 step 32)

Bidirectional edges are the strongest single component (−0.19 without them);
unsupervised members cost 0.030 in fusion; the focal-vs-weighted-CE choice is
**second-order on GATv2** (0.4729 ± 0.0525 vs 0.4388 ± 0.0505, within seed
noise; decisive on SAGE); screens-as-features is input-dependent (helps the
tabular learner by 0.070 over five seeds, harms the graph-feature learner,
wash for the unweighted composite); added input channels (context fusion,
line-graph) measurably hurt under the temporal shift and were not adopted.

## Known limitations

1. **Validation blindness under temporal shift (t43):** val AUC-PR spans
   0.93–0.95 across seeds while test spans 0.42–0.55; train-label noise up to
   20% *raises* test AUC-PR (0.5978 ± 0.0248) while val collapses — four
   independent measurements. Shift-aware selection is future work.
2. Seed variance (±0.05) dominates machine-class variance (±0.02); paper
   tables quote multi-seed means.
3. Elliptic features are anonymized — evidence narratives are structural or
   temporal there; amount narratives require AMLworld/procurement data.
4. Mendeley prevalences are case-control artifacts; only lift-style
   comparisons cross folds.
5. Explanation quality: PGExplainer fidelity is sane on 49/50 top alerts, but
   human validation (practitioner study, §10.3) is pending; R-GCN carries no
   mask-based explanation (R12).

## Ethics

See `docs/ethics_and_scope.md`. Public/anonymized research data only; no UAE
institutional or personal data; screening-not-accusation language propagated
through every output surface; EU AI Act high-risk obligations noted in the
paper's regulatory-alignment section.
