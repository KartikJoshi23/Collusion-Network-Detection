# Part B results against the current claims

Branch `paper/journal-revision`, 2026-11-14. Every value below is read from
the named artifact, which a committed config produces. Values from this
machine (Intel i5-11300H) are marked "here"; values from the original
machine are marked "master". The trees, LOCO, LOMO and GATv2 seed 0
reproduce master bit for bit (checks R1–R3, R5, R7). B7 is still running and
is reported separately when it finishes.

## B2. Trees over five seeds

Config: `baselines_elliptic_pp_multiseed.yaml`, `baselines_mendeley_eu_multiseed.yaml`,
`baselines_mendeley_screens_ablation_multiseed.yaml` (XGBoost subsample and
colsample_bytree 0.8, seeds 0–4).

| Row | Paper now | New (mean ± SD, 5 seeds) |
|---|---|---|
| Elliptic B2, AUC-PR | 0.8076 (det.) | 0.8039 ± 0.0017 |
| Elliptic B3, AUC-PR | 0.8104 (det.) | 0.8123 ± 0.0012 |
| Elliptic B2, B3, P@50/100/200 | 1.00 | 1.00 ± 0.00 |
| Mendeley B2, AUC-PR / P@18 | 0.3925 / 0.22 | 0.3849 ± 0.0099 / 0.222 ± 0.000 |
| Mendeley B3, AUC-PR / P@18 | 0.3775 / 0.56 | 0.3749 ± 0.0092 / 0.567 ± 0.061 |
| Mendeley B2 + screens | 0.4558 / 0.61 | 0.4547 ± 0.0081 / 0.656 ± 0.061 |
| Mendeley B3 + screens | 0.3450 / 0.39 | 0.3509 ± 0.0058 / 0.200 ± 0.030 |

B3 beats B2 on every Elliptic seed, by about 0.008.

**Paired bootstrap** (`significance_elliptic_pp_multiseed.yaml`; 2,000
resamples, n = 16,670):

| Comparison | Paper now (seed 0) | New |
|---|---|---|
| GATv2 vs B3 | −0.261 [−0.285, −0.235] | per seed pair −0.264 to −0.391; CI bounds −0.416 to −0.238; every p at the 0.001 floor; seed-averaged scores −0.301 [−0.324, −0.276] |
| Calibrated vs rank fusion | +0.471 [0.440, 0.499] | per seed +0.342 to +0.471; CI bounds 0.314 to 0.500; seed-averaged +0.444 [0.413, 0.474] |

**B3 in the calibrated fusion** (`fusion_gatv2_b3_multiseed.yaml`; B3
trained on steps 1–29 so that steps 30–34 can fit the calibrator):
GATv2 0.4729 ± 0.0525; B3 (≤ 29) 0.8012 ± 0.0034; fused 0.7760 ± 0.0014.
The fusion again falls below its best member.

## B1. Before and after step 43

Config: `derived_numbers.yaml` (per-window AUC-PR over the five seeds).

| Window | Prevalence | GATv2 | B3 |
|---|---|---|---|
| Steps 35–42 (n = 9,983) | 0.0916 | 0.5737 ± 0.0623 | 0.9259 ± 0.0011 |
| Steps 43–49 (n = 6,687) | 0.0253 | 0.0391 ± 0.0041 | 0.0567 ± 0.0034 |

The paper says the graph model "drops to the floor" from step 43. That holds,
but the trees collapse too. **Effect on the text:** the gap between trees and
GNNs sits in steps 35–42. After step 43 both models sit near the floor
(lift 1.5 for GATv2, 2.2 for B3). RQ1 and the Fig. 3 caption must say so.

## B3. Local features only

Config: `baselines_elliptic_pp_local_multiseed.yaml` (94 local columns:
the time step and the 93 local features).

| Row | AUC-PR (5 seeds) |
|---|---|
| B2-local | 0.7879 ± 0.0011 |
| B3-local (local + graph) | 0.7959 ± 0.0014 |
| B2 (all 183 raw columns) | 0.8039 ± 0.0017 |
| B3 (all raw + graph) | 0.8123 ± 0.0012 |

The paper says B3 adds only 0.003 over B2 "so most of its strength sits in
the node features". With seeded trees the graph features add about 0.008,
with or without the aggregates. The 72 neighbourhood aggregates and the 17
Elliptic++ additions (which include in- and out-degree and BTC flows) add
0.016. **Effect on the text:** most of the trees'
strength sits in the 94 local columns (0.7879 alone).

## B4. Below-chance results

Config: `diagnose_below_chance.yaml` (artifact
`eval_outputs/diagnostics/below_chance/diagnostics.json`), plus
`gnn_mendeley_rgcn_nocomm_multiseed.yaml`. No label or score bug was found:
y = 1 only for "illicit" in every case, and the stored labels match.

| Case | Score | 1 − score | Prevalence | Diagnosis |
|---|---|---|---|---|
| Mendeley R-GCN | 0.2808 ± 0.0087 | 0.433–0.470 on every seed | 0.358 | Temporal reversal of the structural signal (below) |
| AMLworld B2 / B3 | 0.0063 / 0.0062 (fenced) | 0.0211 / 0.0239 | 0.0103 | Training window holds almost no label signal (below) |
| Financial → procurement probe | 0.2841 (master) | 0.4325 | 0.358 | Same Mendeley reversal |
| Procurement source encoder (added) | 0.2884 | 0.4584 | 0.358 | Same Mendeley reversal |

**Mendeley.** The training firms are 87–89% cartel-linked (loss window
≤ 2010: 0.871, n = 380; validation 2011–2013: 0.888, n = 258) against 0.358
in test. In the loss window every usable structural feature ranks licit firms
higher, the opposite of the test window: degree ROC-AUC 0.382 against 0.612,
k-core 0.376 against 0.631, burstiness 0.388 against 0.599. A model fit on the
loss window therefore ranks test firms backwards. The validation AUC-PR of
0.943–0.952 sits only just above the validation prevalence of 0.888. A first
hypothesis, a shift in the component-size feature (median 447 in train
against 6,642 in test), did not hold: without the two component features the
R-GCN still scores 0.2997 ± 0.0015.

**AMLworld.** Training featurises accounts on the first hour only (344,747 of
5,078,345 transactions). In that window the money-flow features carry almost
no label signal (ROC-AUC 0.488–0.541); over the full window the same features
carry a strong one (0.559–0.736 on the informative features). No feature
changes sign beyond 0.02. The paper's current explanation, a test median
degree of 3 against 13 in train, compares full-window degrees. The models saw
a median of 2 in train. **A bug was found and fixed:** the paper says the
splitter fences off the post-window tail, but `baselines_amlworld.yaml` never
set the fence. With the fence (10 accounts and 1,108 transactions removed),
B2 moves from 0.00639 to 0.00635 and B3 from 0.00623 to 0.00618; prevalence
moves from 0.01038 to 0.01034. The text must change 0.0064 to 0.0063 and
0.0104 to 0.0103.

## B5. Pooled lift for transfer

Config: `transfer_pooled_lift.yaml` (2,000 resamples per fold).

| Matrix | Macro lift (paper now) | Pooled lift | Size-weighted lift |
|---|---|---|---|
| Mendeley LOCO (7 folds, 1,001 firms) | 1.17 | 0.929 ± 0.022 | 0.991 |
| García LOMO (4 folds, 2,878 firms) | 1.57 | 1.355 ± 0.153 | 1.527 |

Mendeley folds with a lift CI above 1: country_1, country_3, country_5,
country_6. country_2 holds 750 of the 1,001 firms and its lift is 0.903
[0.874, 0.939], below 1. Every García fold's CI lies above 1 (America 1.56,
Brazil 1.77, Italy 1.43, Japan 1.53). **Effect on the text:** "transfer works"
holds for García only. On Mendeley the macro lift comes from small folds.

**Country names: open.** The Mendeley record (DOI 10.17632/f3y4nrn3s6.2)
names the seven countries (Bulgaria, France, Hungary, Latvia, Portugal,
Spain, Sweden), but the data code them country_1 to country_7 and publish no
key. The per-code case counts in the data (2, 15, 7, 14, 14, 2, 5) do not
match the per-country counts in the publisher's working paper (10, 2, 8, 19,
11, 17, 23), so the codes cannot be mapped without guessing.

## B6. Frozen probe at full labels

Config: `cross_domain_full_label_comparison.yaml` (stored encoders, here).

| Direction | Prevalence | Frozen probe | Structural probe | Probe on B2 inputs | B2 XGBoost (5 seeds) |
|---|---|---|---|---|---|
| Financial → procurement (n = 363) | 0.358 | 0.2843 [0.268, 0.311] | 0.2705 | 0.4752 [0.421, 0.545] | 0.3849 ± 0.0099 |
| Procurement → financial (n = 16,670) | 0.065 | 0.1502 [0.135, 0.169] | 0.1084 | 0.2991 [0.280, 0.322] | 0.8039 ± 0.0017 |

Paired bootstrap: the frozen probe beats the structural probe only for
procurement → financial (+0.042 [0.026, 0.059]); the financial → procurement
difference is +0.014 [−0.004, 0.037]. It trails the probe on B2's inputs by
0.191 and 0.149 (both p at the 0.001 floor). Encoders never ingest raw
features: both domains enter through the same 10-column structural template,
z-scored within each graph. **Effect on the text:** the transfer claim shrinks
to "the procurement encoder carries some structural signal into the financial
domain, far below models that use the target's own inputs".

Reproducibility note: with the stored weights, procurement → financial
reproduces master exactly (0.15022049218819097). Financial → procurement gives
0.2843 here against 0.2841 on master. The difference persists with identical
weights and any torch thread count, so it is CPU-level floating-point
variation in the probe pipeline.

## R6 and B8. Explanations on the rebuilt queue

The published explanation bundles were built from the drifted demo queues
(`gatv2_multi_s0` for Elliptic++, `sage_struct_s0` for Mendeley), the defect
in revision-plan.md, Section 0.2. Rebuilt from the committed queues
(`explanations_elliptic_pp.yaml`, `explanations_mendeley_eu.yaml`), the counts
do not change: 15 of 50 Elliptic++ bundles carry a proven motif with red
flags, 1 of 50 has implausible fidelity, and 0 of 20 Mendeley bundles carry a
motif. The actor bundles already matched their committed queue.

Config: `explainer_metrics_elliptic_pp.yaml` (here), on the rebuilt queue.

| Arm | PyG sane | Hard fid+ | Hard fid− | Hard sane | Sparsity | Seconds (here) |
|---|---|---|---|---|---|---|
| PGExplainer | 49/50 | 0.0525 | −0.0063 | 0.50 | 0.120 | 18.1 |
| GNNExplainer | 10/50 | 0.0486 | 0.0000 | 0.44 | 0.291 | 57.8 |
| Attention | — | 0.0486 | −0.0005 | 0.44 | 0.005 | 0.6 |

The paper says GNNExplainer reached 12 of 50 and took 122.9 s against
51.3 s; on the rebuilt queue it reaches 10 of 50, and PGExplainer still takes
under a third of the time. Sparsity is low because most 2-hop ego windows
hold barely more than the 20 kept edges; attention keeps almost the whole
window. Mean Jaccard overlap of the kept edges: PGExplainer–attention 0.88,
GNNExplainer–attention 0.70, GNNExplainer–PGExplainer 0.65. The explanations
are therefore not sparse, and the three arms largely agree on which edges
matter.

## D24. Test-time re-normalisation, five seeds

The paper said that removing test-time re-normalisation moved GATv2 from 0.693
to 0.532. Both figures came from the July ledger and from a fix pass that
changed many things at once.

Method. Validation runs on the train graph with the frozen train statistics,
so a per-graph run trains exactly the weights of the frozen run. The seed-0
per-graph training run (`gnn_elliptic_pp_gatv2_focal_pergraphnorm_multiseed.yaml`,
here) confirms it: best epoch 121 and validation AUC-PR 0.9497, as in the
headline seed 0. The five-seed measurement therefore re-scores the five stored
master checkpoints with frozen and with test-graph statistics
(`normalisation_rescore_elliptic_pp.yaml`, here). Guards: every checkpoint
reproduces its validation AUC-PR and its frozen test AUC-PR exactly
(difference 0.0 on all five seeds). Cross-check: the re-scored seed-0
per-graph scores equal the end-to-end per-graph run's scores row for row
(67,504 nodes; AUC-PR 0.691923063606791 in both). The trained route was
stopped during seed 1 once the cross-check had passed.

| Seed | Frozen (published) | Test-graph statistics | Paired Δ [95% CI] | p |
|---|---|---|---|---|
| 0 | 0.5492 | 0.6919 | +0.1427 [0.1260, 0.1594] | 0.001 |
| 1 | 0.4712 | 0.6891 | +0.2178 [0.1958, 0.2374] | 0.001 |
| 2 | 0.4276 | 0.6823 | +0.2547 [0.2346, 0.2736] | 0.001 |
| 3 | 0.4213 | 0.6840 | +0.2628 [0.2381, 0.2846] | 0.001 |
| 4 | 0.4951 | 0.6789 | +0.1838 [0.1662, 0.2012] | 0.001 |
| Mean ± SD | 0.4729 ± 0.0525 | 0.6853 ± 0.0052 | +0.2124 ± 0.0501 | |

Steps 35–42 against 43–49 (`derived_numbers.yaml`): frozen 0.5737 ± 0.0623
and 0.0391 ± 0.0041; test-graph statistics 0.8038 ± 0.0068 and
0.0378 ± 0.0039. The whole gain lies before the step-43 closure, where the
trees reach 0.9259. The tree baselines read raw features and never normalise,
so the RQ1 comparison does not rest on this protocol choice: the adapted
GATv2 (0.6853) still falls short of B3 (0.8123).

Verdict. The direction of the old claim holds, and the effect is larger than
stated: re-normalising on the test graph adds 0.21 AUC-PR and cuts the seed
SD tenfold. The paper now quotes the five-seed measurement and drops the
ledger figures.

## D25. Actor R-GCN over five seeds

The paper quoted the seed-0 actor R-GCN (0.2473 AUC-PR, precision@100 0.98)
and called the head of its ranking "stable across seeds". The only evidence
for that phrase was a three-seed check on another laptop in July 2026, with no
committed config or artifact (ledger: 0.326 ± 0.078; P@100 0.98, 1.00, 1.00).

Run. `gnn_elliptic_actor_rgcn_multiseed.yaml` (here), identical to
`gnn_elliptic_actor_rgcn.yaml` except for the seeds. Seed 0 reproduces the
stored single-seed run in every validation and test score (56,720 and 292,102
wallets).

| Seed | Test AUC-PR | Validation AUC-PR | Best epoch / epochs run | P@50 | P@100 | P@200 |
|---|---|---|---|---|---|---|
| 0 | 0.2473 | 0.5087 | 13 / 29 | 0.96 | 0.98 | 0.98 |
| 1 | 0.3286 | 0.5247 | 20 / 36 | 1.00 | 1.00 | 1.00 |
| 2 | 0.4033 | 0.7601 | 119 / 120 | 1.00 | 1.00 | 0.945 |
| 3 | 0.3950 | 0.7400 | 111 / 120 | 1.00 | 1.00 | 0.99 |
| 4 | 0.3258 | 0.5797 | 22 / 38 | 1.00 | 1.00 | 1.00 |
| Mean ± SD | 0.3400 ± 0.0632 | | | 0.992 ± 0.018 | 0.996 ± 0.009 | 0.983 ± 0.023 |

Prevalence in the test window is 0.0529, so the mean lift is 6.4× (seed 0
alone: 4.7×). Seeds 0–2 alone give 0.3264 ± 0.0780, the July ledger value, so
the two laptops agree.

Observations, not claims. Seed 0 is the weakest seed. Its deficit sits in
steps 35 and 36 (AUC-PR 0.089 and 0.050, against 0.63–0.81 and 0.94–0.96 for
the other seeds). Seeds 0, 1 and 4 stop early (best epochs 13–22); seeds 2
and 3 train all 120 epochs and score highest. On this graph, validation
AUC-PR tracks test AUC-PR across the five seeds (Spearman 0.90; with five
points the exact two-sided permutation p is 0.083). That differs from the
transaction graph, where validation sits near 0.94 on every seed. Five points
cannot carry a claim, so the paper does not state it.

Queue across seeds (`alert_queue_elliptic_actor_multiseed.yaml`, here). The
paper's queue sentence used seed 0, the weakest seed, so the actor queue was
rebuilt from every seed's scores over the same Leiden communities (Leiden
seed 0). Seed 0 reproduces the stored queue alert for alert. Precision is
tie-aware (item D28):

| Seed | P@50 | P@100 | P@200 |
|---|---|---|---|
| 0 | 0.0846 | 0.0538 | 0.0384 |
| 1 | 0.1538 | 0.1538 | 0.1956 |
| 2 | 0.1538 | 0.1538 | 0.1950 |
| 3 | 0.1538 | 0.1538 | 0.1950 |
| 4 | 0.1538 | 0.1538 | 0.2007 |
| Mean ± SD | 0.1400 ± 0.0310 | 0.1338 ± 0.0447 | 0.1649 ± 0.0708 |

In seeds 1–4 the calibrated scores saturate, and the top 130 alerts all
score 1.0; 20 of them are hits. A random order of the 2,514 alerts gives
48/2,514 = 0.0191. The node ranking gives P@50 0.992 ± 0.018. The queue
collapse therefore holds on every seed.

Verdict. The single-seed AUC-PR understated the model: the five-seed mean is
0.3400, not 0.2473. The head-of-ranking claim holds on five seeds
(precision@100 0.98 to 1.00). The queue sentence holds too, and now carries
the five-seed queue figure. The paper quotes the five-seed numbers and drops
"remarkably".

## D28. Tie-aware queue precision (found during the revision)

Finding. Contribution 1 lists tie-aware precision@k among the protocol's
guarantees, and Section IV counts queue hits "tie-aware". Node-level
precision@k was tie-aware (`_expected_positives_at_k` in `eval/metrics.py`).
Alert-level precision was not: the harness read hits in rank order, and
`build_alerts` breaks equal risk scores by community id. Isotonic calibration
maps ranges of raw scores to one value, so group scores tie often. The
five-seed actor queue exposed it: seeds 1–3 gave identical precision because
their top 130 alerts all scored 1.0.

Fix (commit 5ee1604). `alert_queue_metrics` and `illicit_coverage_at_budget`
take the expectation over a uniform random order within the tie group at each
budget, the node-level rule. Unit tests pin order-freedom and check coverage
against full enumeration when tied alerts share members. Every queue and
sensitivity config the paper cites was rerun under the fix.

Audit at the published budgets (rank order → tie-aware), any-member hit rule:

| Queue | Budget | Rank order → tie-aware |
|---|---|---|
| Financial (published) | @50 / @100 / @200 | unchanged: 0.32, 0.25, 0.135 (no ties) |
| García Italy | @10 | unchanged: 1.00 |
| Procurement (published) | @4 | 0.5000 → 0.3953 (tie group 129) |
| Procurement (published) | @18 | 0.3333 → 0.3953 (tie group 129) |
| Procurement (published) | @36 | 0.3333 → 0.3953 (tie group 129) |
| Actor seed 0 (published) | @50 | 0.0800 → 0.0846 (tie group 1780) |
| Actor seed 0 (published) | @100 | 0.0600 → 0.0538 (tie group 1780) |
| Actor seed 0 (published) | @200 | 0.0350 → 0.0384 (tie group 1780) |

Rerun values (tie-aware): procurement P@18 0.3953; under
the hit rules 0.1 and 0.25 it is 0.3876 and
0.3721. A random order of the 223 alerts gives
86/223 = 0.3857. The top 129
alerts all score 1.0 and hit at 0.3953; the other 94 hit at 0.3723. The
procurement queue therefore barely ranks its alerts, which fits the seed-0
R-GCN scoring below prevalence at the firm level.

Effect on the paper. The financial numbers, the García queue and the financial
hit-rule sentence do not change. The procurement queue sentence, its hit-rule
sentence and Appendix A change (0.33 → 0.40, with the random-order baseline
0.39). The actor seed-0 queue still prints 0.08 (0.0846). Section IV now
states that precision@k is tie-aware for nodes and for groups.
