# One-page change log — "One Stack, Two Ledgers" (journal revision)

Branch `paper/journal-revision`. Item-by-item detail: `paper/revision-changelog.md`;
raw results against the old claims: `paper/revision-results.md`. **Draft: B7, D24
and D25 are still running; their lines are marked.**

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
- **Label noise vs regularisers (B7):** [PENDING]
- **Normalisation effect (D24):** [PENDING; seed 0 reproduces 0.692 vs 0.549]
- **Actor model across seeds (D25):** [PENDING]

## What changed in the manuscript
- Framing (Part A): problem-first introduction; the AI Act as a design standard;
  RQs matched to the sections that answer them; Section VII cut.
- Results (Part B): Tables II–VI rebuilt from five-seed runs; new tables for steps
  35–42 vs 43–49, full-label probes and explainer metrics; Appendix A rebuilt (42
  rows); every printed number checked by a manifest (0 failures).
- Methods (Part C): new Appendix C with every split, feature, rule and setting.
- Consistency (Part D): 27 items found and fixed or marked, including the queues
  and explanation bundles built from the wrong models (rebuilt, counts unchanged)
  and the probe reproducibility claim (corrected).
- References (Part E): 31 → 60, each verified; one finding re-attributed.
- Language and figures (Part F): new abstract; Section I rewritten; vector
  figures at 8 pt or more, greyscale-safe.

## Decisions needed from the authors
Target journal (then Part G, the Springer move); rater study; repository URL and
availability wording; disclosure of earlier versions (and the "previously
published" sentence); confirmation of the AI-use statement in
`paper/declarations_draft.md`; funding, competing interests, contributions,
acknowledgements; co-author approval; the four source disagreements with the
brief (95–98% vs 90–95%; the OECD 13%/20% figures; "after the fact"; country names).
