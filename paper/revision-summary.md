# One-page change log — "One Stack, Two Ledgers" (journal revision)

Branch `paper/journal-revision`. Item-by-item detail: `paper/revision-changelog.md`;
raw results against the old claims: `paper/revision-results.md`. Every run is in;
what remains are the author decisions below.

## Headline results after the revision
- **RQ1 holds:** five-seed trees (B3 0.8123 ± 0.0012) beat GATv2 (0.4729 ± 0.0525)
  on every seed pair (paired bootstrap, every p at the 0.001 floor). **New:** the
  trees also collapse at the step-43 market closure, so the whole gap lies in steps
  35–42 (0.926 vs 0.574).
- **Transfer is weaker than claimed:** García pools to lift 1.36, but Mendeley pools
  to 0.93 (the old macro lift 1.17 came from small folds). Cross-domain, the frozen
  procurement encoder reaches 0.150 on Elliptic++, half of a probe on the target's
  own features (0.299).
- **Below-chance results explained, no bug in the labels:** Mendeley's structural
  signal reverses over time; AMLworld's one-hour training window carries almost no
  signal. **Bug fixed:** the AMLworld config never set the post-window fence.
- **Explanations:** PGExplainer passes PyG's sanity check on 49/50 alerts, but only
  25/50 under a uniform hard-mask test, and no explainer is sparse.
- **Label noise vs regularisers (B7):** on five seeds, 10% label noise lifts
  test AUC-PR from 0.4729 to 0.5646 while validation falls from 0.938 to 0.683,
  and tenfold weight decay does the same (0.5403; validation 0.8996). Both
  gains lie in steps 35–42, not across the step-43 closure, so the old
  explanation is replaced. Dropout, label smoothing and patience 5 do not repeat
  the pattern; a later validation window does not close the gap. The paper now
  counts two such measurements, not four.
- **Normalisation effect (D24):** re-normalising on the test graph lifts GATv2
  from 0.4729 ± 0.0525 to 0.6853 ± 0.0052 (every seed p ≤ 0.001), all of it in
  steps 35–42. Even adapted, GATv2 stays below the trees. The unsourced
  0.693 → 0.532 figures are gone.
- **Actor model across seeds (D25):** five seeds give 0.3400 ± 0.0632
  AUC-PR; the quoted seed 0 (0.2473) is the weakest. Precision@100 is 0.98–1.00
  on every seed. The actor queue, rebuilt per seed, reaches P@50
  0.14 ± 0.03 against 0.99 for the node ranking.
- **Queue precision is now tie-aware (D28):** the paper claimed it, but the
  alert-level code ranked ties by community id. The procurement queue's top 129
  alerts tie: P@18 is 0.40 (was 0.33), against 0.39 for a random order, so the
  procurement queue barely ranks. The financial queue does not change.

## What changed in the manuscript
- Framing (Part A): problem-first introduction; the AI Act as a design standard;
  RQs matched to the sections that answer them; Section VII cut.
- Results (Part B): Tables II–VI rebuilt from five-seed runs; new tables for steps
  35–42 vs 43–49, full-label probes, explainer metrics and regularisers; Appendix A
  rebuilt (51 rows); every printed number checked by a manifest (0 failures).
- Methods (Part C): new Appendix C with every split, feature, rule and setting.
- Consistency (Part D): 28 items found and fixed or marked, including the queues
  and explanation bundles built from the wrong models (rebuilt, counts unchanged)
  and the probe reproducibility claim (corrected).
- References (Part E): 31 → 60, each verified; one finding re-attributed.
- Language and figures (Part F): new abstract; Section I rewritten; vector
  figures at 8 pt or more, greyscale-safe.

## Recommendations applied, for Dr. Garg to confirm
- **Journal:** IJDSA (Springer), backup SNAM. The paper now comes in both
  formats: IEEE (`collusiongraph_paper.tex`) and Springer Nature `sn-jnl`
  (`collusiongraph_paper_springer.tex`, generated from it), with a flat upload
  bundle built by `scripts/paper_to_springer.py --bundle`.
- **Rater study:** not run before submission; RQ3 rests on fidelity and coverage.
- **Availability:** the public GitHub repository is cited in the abstract and
  Appendix C; a Zenodo DOI for a tagged release is recommended.
- **Earlier versions:** Section IV-E names the earlier project report and
  repository; a cover-letter paragraph is drafted in `paper/declarations_draft.md`.
- **Source disagreements with the brief:** settled on the primary sources
  (95–98%; 12.7% of GDP, the 20% figure dropped; "secret and hard to detect";
  country codes kept because the release gives no key).
- **Full audit:** `paper/brief-audit.md` checks every brief item and sub-point.

## Still needed from the authors
Funding, competing interests, author contributions (CRediT) and
acknowledgements; confirmation of the AI-use statement. All five authors
approved the revised version on 17 November 2026. Three EDA notebooks on the public main branch show raw-row
previews (5 Mendeley, 5 García, 3 AMLworld rows); they are removed on this
branch, but the repository history keeps them, and rewriting it is the
authors' call.
