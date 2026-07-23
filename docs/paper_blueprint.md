# CollusionGraph — Research-Paper Blueprint

> **How to use this file.** This is the writing blueprint for the paper: every section
> below lists (a) what the section must say, (b) the *measured* evidence that says it —
> with the exact artifact/table that carries the number — and (c) status. Writing the
> paper should reduce to walking this file top-to-bottom and prose-ifying each block.
> Numbers are NEVER retyped from memory: they come from `poe paper-tables`
> (`eval_outputs/paper_tables/`) and the number→config map in
> [`docs/reproducibility.md`](reproducibility.md), which carries a drift guard.
> Plan authority: implementation-plan.md §10; skeleton §10.4; venues §10.5.

---

## 0. Framing decisions (settle before writing)

| Decision | Choice | Rationale |
|---|---|---|
| **Working title** | *One Stack, Two Ledgers: Budget-Evaluated, Explainable Collusion Screening Across Illicit-Finance and Procurement Networks* | Leads with the moat (§10.1): the cross-domain merge |
| Alt titles | *CollusionGraph: Cross-Domain Screening of Collusion Structure under Honest Evaluation* · *Does Collusion Structure Transfer? A Two-Domain Study with an Imbalance-Robust, Explainable Graph Stack* | Keep the RQ4-question form if the venue rewards falsifiable titles |
| **Primary venue** | ACM ICAIF (check CFP) → KDD workshop (MLF) alternate → EPJ Data Science journal fallback | §10.5 strategy, deadline-risk-free fallback |
| **Paper type** | Full research paper w/ reproducibility appendix; 9–10 pp main + appendix | Matches ICAIF format |
| **Core claim shape** | *A single budget-evaluated stack screens both domains; transfer exists but is market-dependent and label-rich-only; honest evaluation (multi-seed, shift-aware) changes the headline story* | Every clause is measured — see §6 below |
| **Tone rule** | Screening, never accusation; negatives reported as findings | docs/ethics_and_scope.md; the caveat is part of the system |

---

## 1. Abstract (~200 words — write LAST)

One sentence each, in order:
1. Problem: collusion (laundering rings, bid-rigging cartels) is a *structural* crime; two literatures study it separately.
2. Contribution: one IR + one stack, six datasets, two domains, budget-first evaluation.
3. RQ1 result: trees still beat GNNs on Elliptic++ under honest protocol (GATv2 0.4729 ± 0.0525 vs XGB-Graph 0.8104; paired Δ −0.261, p ≈ 0.001) — the GADBench finding replicated *and sharpened by multi-seed*.
4. RQ2 result: injection recovery at scale + queue granularity findings (actor head seed-stable P@100 ≥ 0.98).
5. RQ4 result: LOCO/LOMO transfer is real but **market-dependent** (García uniformly positive, macro lift 1.57; Mendeley's largest market fails, 0.90); cross-domain transfer is label-rich-only in one direction, never in the other.
6. RQ3 + product: PGExplainer + motif→FATF/OECD bundles, practitioner-study instrument, guarded LLM copilot (24/24 goldens, zero guilt-language releases).
7. Honesty hook: label-noise curve — corrupting 20% of train labels *raises* test AUC-PR (0.48 → 0.60) while validation collapses: temporal-shift val-overfitting made explicit.
8. Release: code, configs, seeds, model card, five datasheets, reproducibility map.

---

## 2. Introduction (~1 page)

- Hook: EU AI Act high-risk obligations enforceable **2 Aug 2026** (fraud/AML explicitly in scope) — explainable, auditable, human-in-the-loop screening is now a legal property, not a nicety (§10.6.1).
- The two-ledgers-one-structure argument: fan-in/fan-out/cycles/pass-through ↔ rotation/cover-bids/market-partition — same abstraction, two enforcement worlds.
- The four RQs, verbatim from implementation-plan §2 (RQ1 budgets, RQ2 transfer/injection, RQ3 explanations, RQ4 cross-domain).
- Contribution list (5 bullets): unified IR + adapters (6 datasets); budget-first leakage-safe protocol w/ multi-seed + significance discipline; transfer matrices both granularities + both directions; explanation bundles with practitioner instrument + guarded copilot; honest-negative catalog (val-blindness ×4 measurements).
- Forward pointer to the honesty theme: "the paper's evaluation protocol is itself a contribution" (arXiv:2604.19514 / 2604.23494 critiques are *implemented*, not just cited).

## 3. Related work (~0.75 page — six threads, one paragraph each)

Thread → key cites (full list in §10.4 of the plan):
1. Graph anomaly detection & benchmarks — Ma et al. 2023; **GADBench** (XGB-Graph discipline).
2. AML GNNs — Motie & Raahemi 2024; LineMVGNN; Lawal et al.; Multi-GNN/AMLworld line (arXiv:2412.00241 — we replicate their bidirectional-edge evidence in-house: −0.19 AUC-PR without reverse edges).
3. Evaluation-protocol critiques — arXiv:2604.19514, 2604.23494 (queue granularity: our tx-vs-actor disagreement measures it).
4. Cartel detection: screens tradition (García Rodríguez, IJIO 2025) + cartel GNNs (Imhof; Gomes et al. — our LOMO numbers are the comparison point).
5. Transfer/GFM framing — arXiv:2505.15116, 2503.09363 (RQ4 as a falsifiable GFM case study).
6. LLM-augmented explanation — arXiv:2506.14933, 2507.14785 (copilot: participation without dependence).

## 4. Data & unified representation (~0.75 page)

- Table **T-DATA**: six datasets × (domain, nodes/edges, labels, license, role) — source: [`docs/DATASETS.md`](DATASETS.md) + five datasheets in [`docs/datasheets/`](datasheets/).
- The IR contract (§4.2): typed nodes/edges/labels/history packs; what adapters must NOT do (no cleaning heroics; degradation paths explicit — García identities on 4/6 markets, Mendeley case-control caveat, AMLworld post-window fence).
- As-of label policies (F1 fix): `mendeley_as_of`, `history_as_of` — one paragraph, it is a leakage contribution.

## 5. Method (~1.25 pages)

- Detection arms: baselines B1–B4, GNNs (SAGE/GATv2/R-GCN, direction-aware, focal), unsupervised (DOMINANT/GAE/floor), isotonic-calibrated fusion; Leiden roll-up → alert unit (NMS, size caps, hit rules).
- Imbalance handling (RQ1 constraint): focal vs wCE; injection with known ground truth.
- Explanation layer: PGExplainer (adopted over GNNExplainer — sanity 49/50 vs 12/50, the ablation is Appendix material), motif matcher (9 families, 100% recall on injected fixtures), FATF/OECD citations.
- Copilot (½ column): bounded SQL-agent, deterministic guards, goldens gate — cite gate numbers (24/24, grounded 1.0, zero released guilt-language).
- **Evaluation protocol subsection (the differentiator):** budget-first tie-aware P@k; AUC-PR with prevalence baselines; strict-inductive splits + CI leakage tests; frozen train-time normalization; multi-seed ≥5 with paired stratified bootstrap; per-time-step reporting.

## 6. Results (~2.5 pages) — every table pre-generated

Run `uv run poe paper-tables` → `eval_outputs/paper_tables/`. Status key: ✅ artifact exists on ≥1 machine · 🔶 regenerate (per-machine artifact) · ⛔ needs a run.

| Table | Content | Source artifact | Status |
|---|---|---|---|
| **T1 RQ1-fin** | Elliptic++ scoreboard: B1–B3, SAGE/GATv2 (focal + wCE multi-seed), unsup, ensembles — mean ± std + seed-0 | `elliptic_headline` table (needs `gnn_gatv2_wce_multiseed` — on laptop-D) | 🔶 |
| **T2 RQ1-proc** | Mendeley scoreboard: B1–B4 + R-GCN multi-seed (0.2808 ± 0.0087 vs prev 0.358 — the honest negative) | `mendeley_headline` (needs baselines rerun on this machine) | 🔶 |
| **T3 significance** | GATv2 vs XGB Δ −0.261 [−0.285, −0.235]; calibrated vs rank Δ +0.471 [0.440, 0.499]; both p ≈ 0.001 (seed-0 deltas labeled beside multi-seed means — RT-1) | `significance` | ✅ |
| **T4 LOCO/LOMO** | Mendeley 7×5 matrix (macro lift 1.17, country_2 fails 0.90) + García 4×5 (uniform, macro 1.57) | `loco_mendeley`, `lomo_garcia` | ✅ |
| **T5 cross-domain** | Probes both directions + label-efficiency curves (proc→fin pays only k ≥ ~1000; fin→proc never) | `label_efficiency_*` | ✅ (fin2proc) / 🔶 (proc2fin, laptop-C) |
| **T6 injection (RQ2)** | At-scale OCDS injection recovery, 5-seed verdict | `injection_ocds` (laptop-D artifact) | 🔶 |
| **T7 ablations** | −bidir (−0.19), −focal (second-order per wce campaign), −unsup (−0.03), −screens, line-graph, context-fusion — one honest-ablation table | assemble from run.json entries listed in reproducibility.md | ⛔ assemble |
| **T8 robustness** | Label-noise curve (0.48→0.60 while val 0.94→0.57) + sensitivity sweeps (NMS-invariant; hit-rule-robust) | `label_noise` + sensitivity.json | ✅ |

Figures (export from the Model Lab — every chart has SVG/PNG export):
- **F1** per-time-step AUC-PR (the step-43 crater) · **F2** precision@k with budget marker ·
  **F3** LOCO/LOMO lift chart · **F4** label-noise curve · **F5** label-efficiency curves ·
  **F6** an example evidence bundle (dossier screenshot) · **F7** system architecture
  (adapt from [`docs/architecture.html`](architecture.html)).

Results narrative order: RQ1 (trees win, sharpened) → queue granularity (tx vs actor) →
RQ2 (injection + at-scale) → RQ4 (matrices → cross-domain → label efficiency) → robustness
(noise, sensitivity, significance) → RQ3 handoff to §7.

## 7. Explanation study (RQ3, ~0.75 page)

- Fidelity: PGExplainer hard-fidelity numbers + the 38/50→1/50 sanity repair (ablation in Appendix).
- Practitioner study: instrument + packets are BUILT ([`docs/practitioner_study.md`](practitioner_study.md), `collusiongraph eval` study configs); report means, Krippendorff's α, themes. **⛔ human phase pending — recruitment fallback (R14): rubric-trained graduate raters + ≥1 domain expert, reported as a limitation.**
- Copilot arm (bundle vs bundle+copilot) if the study runs both.

## 8. Regulatory alignment & ethics (~0.5 page — the freshness hook)

EU AI Act Art. 6 / Annex III obligations mapped to shipped properties (explanation bundles,
fixed-budget human triage, audit export, caveat immutability); CBUAE Art. 149; TRL 3–4
honesty; source: [`docs/ethics_and_scope.md`](ethics_and_scope.md) + model card §ethics.
No prior AML/cartel-GNN paper offers this subsection (§10.6.1).

## 9. Limitations (write from §10.2 item 8 — all already measured/known)

Elliptic t43 shift (and that val selection is blind to it — cite our four measurements);
anonymized features limit narratives; AMLworld synthetic; Mendeley case-control prevalence
(lift, not raw AUC-PR, is the comparator); García identity coverage 4/6; label noise;
transfer magnitudes as measured; practitioner-study substitution if fallback used;
single-GPU compute envelope.

## 10. Reproducibility statement (~0.25 page)

Point at: [`docs/reproducibility.md`](reproducibility.md) (number→config map + drift
guard), model card, datasheets, seeds/configs/lock committed, `poe paper-tables`,
red-team review ([`docs/red_team_review.md`](red_team_review.md)) incl. clean-clone
reproduction, Zenodo DOI on acceptance (⛔ mint at submission).

---

## 11. Writing order (fastest honest path)

1. §6 Results — tables exist; prose-ify T1–T8 (regenerate 🔶 artifacts first: wce/proc2fin/injection tables from their home machines, or rerun locally).
2. §5 Method + §4 Data (mostly transcription from the plan + DATASETS.md).
3. §7 RQ3 (run or fallback the human phase — the ONLY external dependency).
4. §3 Related work → §2 Introduction → §9–10 → §1 Abstract last.
5. Red-team pass against the evaluation-protocol checklist (already once-run; repeat on the draft).

## 12. Submission checklist

- [ ] All 🔶 tables regenerated and drift-guard green (`poe paper-tables` exits 0, no skips)
- [ ] Practitioner phase done or fallback executed + limitation worded
- [ ] Figures exported at print DPI from the Model Lab
- [ ] Every number in prose traced to a table (no retyped numbers)
- [ ] Ethics/caveat wording intact in examples and screenshots
- [ ] Repo tagged, Zenodo DOI minted, anonymization per venue policy
- [ ] Venue CFP dates confirmed (ICAIF primary; KDD-MLF alternate; EPJ DS fallback)
