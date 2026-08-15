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

* **Elliptic++ (tx-level, test steps 35–49, prevalence 0.065):** GATv2-focal
  **0.4729 ± 0.0525** AUC-PR (the published seed-0 0.5492 is the best seed —
  tables must quote the mean); queue head P@100 0.812 ± 0.238 (seed-unstable).
  **XGB-Graph baseline 0.8104 (deterministic) sits ~6σ above the GNN mean** —
  the GADBench finding, replicated and reported, not hidden
  (seed-0 paired bootstrap: Δ −0.261, 95% CI [−0.285, −0.235], p ≈ 0.001;
  the multi-seed mean difference is larger still, −0.338).
* **Actor-level view:** global AUC-PR 0.2473 but queue-head P@100 ≥ 0.98
  seed-stable — served as a node-triage surface alongside the tx-level queue.
* **Calibrated fusion 0.4434 ± 0.0501** tracks its strongest member; naive
  rank fusion collapses to 0.0511 ± 0.0019 (seed-0 paired bootstrap:
  Δ +0.471, CI [0.440, 0.499]; the multi-seed mean difference is +0.392) —
  calibrate-before-fusing is a measured requirement, not a preference.
  Unsupervised members alone score at/below prevalence on Elliptic++
  (their value is coverage, and they cost −0.030 AUC-PR in the fusion).
* **Mendeley EU (firm-level, within case-control sample, prevalence 0.358):**
  R-GCN **0.2808 ± 0.0087 — below prevalence, seed-stable**: an honest
  negative (era shift + weak award-tier signal). The best firm-level signal is
  tabular: XGB + the dataset's own screens **0.4558**. Alert queues: Elliptic
  254 alerts P@50 0.32; Mendeley 223 alerts P@4 0.50 — both NMS-invariant and
  hit-rule-robust.
* **Transfer (RQ4):** within-procurement LOCO/LOMO is market-dependent
  (Mendeley macro lift 1.17 with its largest market failing at 0.90; García
  lift 1.57, positive on every market). Cross-domain transfer is asymmetric
  and weak (proc→fin ~2.3× prevalence; fin→proc negative) and **never pays at
  ≤500 target labels in either direction**.
* **Injection at scale (OCDS Georgia, 163k-node window):** structure-only
  unsupervised arms recover clique-type coordination near-completely at 1.2%
  budget (coordinated_cluster 0.9275 ± 0.162 @2000; common_control clique
  firms 100% via the floor) and are blind to award-pattern cartels
  (rotation / partition / cover-bid ≈ 0–0.24, seed-invariant).

## Ablations (component grid, §7 step 32)

Bidirectional edges are the strongest single component (−0.19 without them);
unsupervised members cost −0.030 in fusion; the focal-vs-weighted-CE choice is
**second-order on GATv2** (0.4729 ± 0.0525 vs 0.4435 ± 0.0615, within seed
noise; decisive on SAGE); screens-as-features is input-dependent (helps the
tabular learner +0.063, harms the graph-feature learner, wash for the
unweighted composite); added input channels (context fusion, line-graph)
measurably hurt under the temporal shift and were not adopted.

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
