# Audit of the revision against the brief

Checked on 16 November 2026, item by item, against `paper/collusiongraph_paper.tex`
on branch `paper/journal-revision`, the change log (`paper/revision-changelog.md`) and
the run ledger (`paper/revision-results.md`). Every sub-point of Parts A–H is listed.
Status words: **Done**; **Done (source)** where the primary source overrides the
brief's wording; **Recommended** where Dr. Garg's decision was taken on a
recommendation and is flagged for his confirmation; **Open** with the reason.

## Summary

- All 13 P1 items and all five content P2 items (3, 10, 11, 12, 17) are done.
- Item 18 (Springer template and declarations) is the one item of real work left. It
  needs Springer Nature's template package, which has not been downloaded yet.
- Item 19 (earlier versions) has a recommended wording; it is Dr. Garg's call.
- Content only the authors can supply stays as marked placeholders: funding,
  competing interests, author contributions (CRediT), acknowledgements, and the
  approval of all five co-authors.

## Priority table

| # | Item | Status | Where |
|---|---|---|---|
| 1 | EU AI Act / AML argument | Done | I (para. 4), VII |
| 2 | Scope, RQ mapping, RQ3 | Done | I-A, I-B, V, VI |
| 3 | Section VII cut to Future Work | Done | Conclusion, last paragraph; Fig. 7 removed |
| 4 | Overstated claims | Done | Abstract, I-B, V-A, V-C, V-D, V-E, VI, VIII, X |
| 5 | B3 per-step curve | Done | Fig. 3, Table IV |
| 6 | XGBoost over five seeds | Done | Tables II, III, V, IX |
| 7 | B2 on local features | Done | Table II, V-A |
| 8 | Below-chance diagnoses | Done | V-A (Mendeley), V-D (probe), V-E (AMLworld) |
| 9 | Pooled lift, per-fold CIs | Done; country names cannot be done (see B5) | Table VI, Fig. 4, V-C |
| 10 | Frozen probe vs raw-feature model | Done | Table VIII, Fig. 5, V-D, abstract |
| 11 | Temporal validation; noise vs regularisers | Done | Fig. 6, Table X, V-E, Appendix C |
| 12 | Explainer metrics | Done | Table XI, VI |
| 13 | Methods details | Done except the repository URL (L3, recommended) | Appendix C |
| 14 | Internal consistency | Done except D8, D11, D12 (author decisions; recommendations below) | throughout |
| 15 | References | Done (60 references, each verified) | bibliography; `references_check.md` |
| 16 | Abstract and language | Done except the availability sentence (L3) | Abstract, I–IX |
| 17 | Figures | Done | Figs. 1–6 |
| 18 | Springer template, declarations | Open: needs the template download | — |
| 19 | Earlier versions disclosed | Recommended wording; Dr. Garg's decision | IV-E; declarations draft |

## Part A — framing and claims

**A1. AI Act argument**
- Open with the problem, not a date: Done. Section I opens with the
  false-positive load and with cartels negotiated in secret.
- 90–95% false positives: Done (source). The CEPS report the brief relies on
  says "often around 95–98%" (Lannoo and Parlour 2021, pp. 3, 31); the paper
  quotes the source.
- "Cartels found only after the fact": Done (source). The OECD 2025 Guidelines
  support "negotiated in secret and hard to detect" (pp. 7, 23) and detection
  through red flags, leniency and whistleblowers (pp. 12, 14); the paper uses that.
- AI Act requirements as a standard, not an obligation: Done (I, VII).
- Annex III 5(b) covers credit scoring only; the high-risk claim is removed: Done.
- CBUAE obligation kept and Article 149 of Federal Decree-Law No. 6 of 2025
  verified against the official text: Done (VII). It is a federal decree-law,
  not a Central Bank document; the citation says so.
- [28] cited as draft guidelines (19 May 2026, non-binding, consultation closed
  23 July 2026): Done (VII, reference `eccguidance`).
- OECD 13% of GDP and 20% price reduction, with page numbers: Done (source).
  Neither figure is in the 2025 Guidelines. The paper uses 12.7% of GDP (2023)
  from Government at a Glance 2025, p. 146. The 20% figure traces to no primary
  OECD document and is removed.

**A2. Scope and research questions**
- Two lead contributions: Done (I-B).
- LOCO and LOMO under RQ2; only the cross-domain probe under RQ4: Done (V-C, V-D).
- RQ2 matched to what was run; the "fingerprints learned from confirmed cases,
  augmented with synthetically injected patterns" phrase removed: Done.
- RQ3 reframed around fidelity and red-flag coverage and answered from them:
  Done (VI). The rater study was not run (Dr. Garg's decision; recommendation
  below).
- RQ1 answered plainly ("The answer to RQ1 is no") and the unsupervised members
  shown to lower the ensemble (+0.0295 without them, Table IX): Done (V-A).
- Section VII cut to two sentences of Future Work and Fig. 7 removed: Done.

**A3. Claims beyond the evidence**

| Claim | Status | Now reads |
|---|---|---|
| Calibration matters more than architecture | Done | Calibrated fusion is necessary if members are fused, but did not beat its best member (V-A, X) |
| Transfer lifts financial screening 2.31× | Done | Frozen probe 0.1502 against the target's own B2 inputs 0.2991 and B2 0.8039 (V-D, abstract) |
| Mendeley macro lift 1.17 | Done | Pooled lift 0.93 and size-weighted 0.99 lead; macro lift in a table note (Table VI) |
| Every García market beats its base rate | Done | "All four evaluated markets" / "All four García markets" (Fig. 4, V-C) |
| Assistant accuracy 0.92 | Done | Grounding 24/26, Wilson 95% CI [0.759, 0.979] (VI) |
| Bootstrap gap −0.261 beside the five-seed mean | Done | Five per-seed differences −0.264 to −0.391 and the seed-averaged −0.301 (V-A, Table III) |
| Validation-selected numbers "report luck" | Done | "Validation selection is unreliable under this shift" (V-E, X) |
| Four measurements show validation cannot see the shift | Done | Two five-seed measurements (label noise, weight decay); the normalisation fix, channel variants and crater are not counted (I-B, V-E, VIII) |

## Part B — analyses

- **B1:** per-step AUC-PR for B2 and B3 computed; B3 line in Fig. 3; Table IV
  gives steps 35–42 and 43–49 for GATv2 and B3. The trees also collapse at step
  43, and RQ1 is reframed: the whole gap lies in steps 35–42. Done.
- **B2:** XGBoost with subsample and colsample 0.8 over seeds 0–4; bootstrap per
  seed pair and on seed-averaged scores (Table III); B3 added to a calibrated
  fusion (0.7760, below B3 alone). Done.
- **B3:** B2-local and B3-local rows (Table II); the V-A paragraph rewritten.
  Done.
- **B4:** all three below-chance cases diagnosed (inverted-score AUC-PR, label
  encoding, train/test distributions); no bug in labels or scores. One config bug
  was found and fixed on the way (the AMLworld post-window fence). Done.
- **B5:** pooled lift, size-weighted lift and per-fold bootstrap 95% CIs in Table
  VI; macro lift moved to a table note. **Country names: cannot be done as
  written.** The Mendeley record names the seven countries but the data code them
  country_1 to country_7 with no key, and the per-code case counts do not match
  the publisher's per-country counts. The paper states this (V-C).
- **B6:** full-label comparison (Table VIII); the full-label point is on Fig. 5;
  the encoders' input (a shared ten-column structural template, never raw
  features) is documented (V-D, Appendix C); abstract sentence updated. Done.
- **B7:** validation split stated (temporal, steps 30–34; Appendix C); temporal
  window rerun (loss on 1–31, validation on 32–34); noise compared with label
  smoothing, weight decay, dropout and early stopping (Table X); five seeds
  throughout; Fig. 6 rebuilt; the 0.4827 vs 0.4729 difference explained (the old
  curve averaged seeds 0–2; the new clean runs are the headline runs). Done.
- **B8:** Fidelity+, Fidelity− and sparsity for PGExplainer, GNNExplainer and
  attention on the same 50 alerts (Table XI); "sane" and "implausible fidelity"
  defined (VI). Done.
- Every new run has a config in Appendix A (51 rows): Done.

## Part C — methods details (Appendix C unless noted)

| Detail | Status |
|---|---|
| Elliptic++ split and validation selection | Done |
| Mendeley and García splits, exact LOCO and LOMO folds | Done |
| Feature lists (B2 local vs aggregated; B3 graph features) | Done |
| B1 rules with thresholds | Done |
| Hyperparameters, including focal γ and α | Done (Table XIII) |
| Tuning budgets, comparable for trees and GNNs | Done (both zero, stated) |
| Unlabelled nodes in training, evaluation and queue hits | Done |
| Fusion members and calibration split | Done |
| Alert queue: Leiden resolution, size cap, Jaccard threshold, budget rationale | Done |
| Cross-domain probe: feature spaces and probe type | Done |
| Copilot: LLM name and version, temperature, prompt location, golden cases | Done |
| Compute: CPU model, memory, typical runtimes | Done |
| Code and data availability with a repository URL | Recommended (L3); see below |

## Part D — consistency (D1–D12 from the brief, D13–D28 found during the revision)

| Brief row | Status |
|---|---|
| Table V vs Appendix A: 0.92 ± 0.17 vs 0.923 ± 0.162 | Done: one source, one rounding |
| Fold prevalence 0.29–0.89 vs 0.25–0.89 | Done: 0.29–0.89 (Mendeley) and 0.25–0.55 (García) |
| USA vs America | Done: USA throughout |
| "Every García market" | Done |
| Procurement queue at P@4 vs P@18 | Done: P@18 throughout, justified (top 5% of 363 firms). The value is now 0.40, tie-aware (item D28) |
| Clean 0.4827 vs headline 0.4729 | Done (B7) |
| Table VII: removing the unsupervised members gives the headline | Done: GATv2 is stated as the only supervised member |
| "Our own previously published" 0.5492 | Recommended wording (D8; Dr. Garg's decision, item 19) |
| V-A "tree baseline is not winning as…" | Done: rewritten after B3 |
| Fig. 2 vs III-C: 2% vs 0.065 | Done: each figure and table names its denominator (III-C, Table I) |
| Abstract promises code with no link | Recommended (L3) |
| Acknowledgements placeholder | Open: authors to supply |

Found during the revision and fixed: D13–D28, listed in the change log. The
latest, D28, made queue precision tie-aware as Contribution 1 claims.

## Part E — references

- [3] Motie and Raahemi: volume and article number added. Done.
- [8] Elliptic++: the KDD 2023 paper is cited. Done.
- [11] and [14]: authors, volume, article number and DOI added. Done.
- [12] and [13]: rechecked; both are still arXiv preprints with no published
  version (Imhof et al. 2025; Gomes et al. 2024). **Note for IJDSA:** its
  guidelines ask that the reference list hold only published or accepted works.
  Keeping them as arXiv preprints is common practice, but the authors may move
  them to the text if the editor insists.
- [22]: replaced by the CEPS report it pointed to. Done.
- [28]: titled as draft guidelines dated 19 May 2026. Done.
- [4]: removed (a weak venue); Weber et al. make the same point. Done.
- Section II paragraphs without citations: each now has two to four. Done.
- Suggested additions: Wachs et al. 2021 (IJDSA), Huber and Imhof 2019, Agarwal
  et al. 2023, and Weber et al. for random forest beating GCN. All cited. Done.
- 45–60 complete references: 60. Springer numbered style: in the Springer move
  (BibTeX in `paper/references.bib`).

## Part F — language, abstract, figures

- Abstract 200–250 words in the brief's order (problem; what was built; three
  findings with numbers; what is released); copilot dropped: Done (239 words).
  IJDSA allows 150–250 and forbids undefined abbreviations: "AUC-PR" is defined
  in the abstract in this pass.
- Every sentence in the brief's "Sentences to fix" table: Done (none of the old
  phrases remains; "therules" was a PDF-extraction artefact).
- No contractions; no asides: Done (checked by search).
- Sentences under about 25 words: four sentences of 30–31 words were split in
  this pass; the rest are 27 words or fewer.
- Fig. 6: "(%)" fixed and annotation moved off the curve: Done.
- Fig. 7: removed: Done.
- Fig. 3: B3 line: Done.
- Fig. 4: the base-rate label sits in the legend, not behind the bars: Done.
- All figures vector, fonts of at least 8 pt, greyscale-safe: Done.

## Part G — Springer format and declarations

| Point | Status |
|---|---|
| Target IJDSA, backup SNAM | Recommended (Dr. Garg to confirm) |
| sn-jnl template with numbered references | Open: needs the template download |
| Abstract within the journal limit | Done (IJDSA: 150–250 words) |
| 4–6 keywords | Done in this pass (six keywords) |
| Declarations: funding, competing interests | Placeholders (authors to supply) |
| Data availability: five datasets with links and licences | Drafted (`declarations_draft.md`); goes into the template |
| Code availability: repository URL | Recommended (L3) |
| Author contributions (CRediT) | Placeholder (authors to supply) |
| Ethics approval: not applicable | Drafted |
| AI-use disclosure | Drafted and flagged for confirmation |
| Acknowledgements | Placeholder (authors to supply) |
| Earlier versions disclosed (0.5492) | Recommended wording (item 19) |
| García licence: released artifacts do not redistribute modified data | Done for the repository: `eval_outputs/` is never committed; three notebook previews of raw rows removed on this branch. No public deployment is recorded. Any public console must leave out the García queue and bundles |

## Part H — report back

- Revised PDF, LaTeX source and one-page change log: delivered.
- Every changed number from a config in Appendix A: Done (`verify_numbers.py
  --strict`: 0 failures, 0 unlisted).
- Items that cannot be done are marked open with the reason: Done (country
  names; the template download; author-supplied content).
- Headlines rewritten where reruns changed them (B1, D24, D25, D28, B7): Done.
- No claims beyond the results: checked in this audit.

Final check before sending:

| Check | Status |
|---|---|
| All 13 P1 items done | Yes, with D8, D11, D12 on recommendations or placeholders |
| Numbers agree across abstract, text, tables and Appendix A | Yes (manifest check) |
| References complete and in Springer style | Complete; Springer style comes with the template |
| Figures readable in print and greyscale | Yes |
| Declarations complete | No: author-supplied content and the template |
| All five co-authors approved | No: only the authors can do this |

## IJDSA requirements, read from the journal's own page

Source: https://link.springer.com/journal/41060/submission-guidelines (read 16
November 2026).

- Springer's LaTeX package in a two-column format.
- No subfolders in the LaTeX upload: figures and the bibliography sit beside the
  .tex file.
- Abstract of 150 to 250 words, with no undefined abbreviations or unspecified
  references.
- Four to six keywords.
- A "Statements and Declarations" section; author contributions and competing
  interests are also entered in the submission system.
- Numbered citations in square brackets; full DOI links in the reference list.
- The reference list holds only published or accepted works.
- Use of a large language model must be declared, except AI-assisted copy editing.
