# Datasets — acquisition status & Week-1 EDA findings

Per implementation-plan.md §4.3. Raw data lives in `data/raw/` (gitignored, re-downloadable
via `uv run poe data`); checksums + licenses in `data/manifests/` (committed). EDA notebooks
in `notebooks/` are read-only after merge.

| # | Dataset | Status | License | Manifest |
|---|---|---|---|---|
| D1 | Elliptic++ (git-disl, Google Drive) | ✅ downloaded + checksummed (9 CSVs, ~2.2 GB) | none published — research use, cite arXiv:2306.06108 | `elliptic_pp.json` |
| D1 | Elliptic base (PyG mirror) | ✅ downloaded + checksummed (3 CSVs) | none published — research use, cite Weber et al. 2019 | `elliptic.json` |
| D2 | IBM AMLworld HI-Small (Kaggle) | ⛔ **blocked — Kaggle API credentials required** (setup in README) | verify on Kaggle page at download | — |
| D3 | García Rodríguez supplement ec0010/mmc2 | ✅ downloaded + checksummed (11 files) — **fallback R2 NOT triggered** | CC BY-NC-ND 4.0 (article OA license per Crossref) | `garcia_rodriguez.json` |
| D4 | Mendeley EU cartel f3y4nrn3s6 v2 | ✅ downloaded; sha256 **matches Mendeley's official API hash** | CC BY NC 3.0 | `mendeley_eu.json` |
| D5 | OCDS bulk | Phase 2 (publisher chosen for bid-level coverage) | per publisher | — |

## Week-1 EDA verification vs. the plan's stated counts

### Elliptic / Elliptic++ (notebooks 01, 02)

Base Elliptic: **all 6 checks PASS** — 203,769 tx nodes, 234,355 directed edges,
166-dim feature vector (incl. time step), 49 time steps, 4,545 illicit (1) /
42,019 licit (2), remainder unknown. Illicit ≈ 2.2% of all transactions →
the extreme-imbalance regime the plan targets. Elliptic++ transaction-graph
verification in notebook 01 (183-feature claim checked there; label/step/edge
counts shared with base).

### Mendeley EU cartel (notebook 03)

- **73 distinct cartel cases — exactly matches the problem statement.**
- 15,616 contract rows; `is_cartel=1` on 6,548 (41.9%) — this is a **case-control
  research sample**, not a population file; population-level prevalence must come
  from the opentender base if population screening is simulated (protocol note for
  §4.5 — measured, not assumed, per §4.3 D4).
- 7 countries (anonymized `country_1..country_7`), 2004–2021; per-country rows range
  from 162 to 7,860 and per-country cartel share from 9.9% to 59.6% — LOCO folds will
  be materially heterogeneous.
- **Losing-bidder coverage: zero.** The schema has no losing-bidder identity columns
  (`bidder_id` is the awardee) — confirming the companion paper's caveat and the §4.2
  award-network-first rule. Co-bid *identity* graphs are NOT constructible from Mendeley.
- What is available everywhere: `lot_bidscount` (100% non-null in every country-year;
  multi-bid lot share ranges ~0–100% by country-year — heatmap in notebook 03) and
  `singleb_avg`, plus the paper's precomputed screens (Benford's MAD, relative value,
  consortium/subcontract flags) → these power the bid-count screen tier; the co-bid
  graph tier activates only on García Rodríguez data.

### García Rodríguez multi-country (notebook 04)

- 64,348 bid rows, 9,781 tenders, 6 market datasets (`Dataset` 0–5; market-name
  mapping in the supplement's README.txt, wired in the Week-2 adapter).
- **54,389 losing-bid rows present** (`Winner`=0) — full bid-level data incl. losing
  bidders, so co-bid graphs and bid-price screens fully apply here (unlike Mendeley).
- Collusive share per market ranges 11.3%–81.8%; bids-per-tender from 2.3 to 91.9 —
  strong cross-market heterogeneity, exactly the LOMO/LOCO transfer terrain.
- All seven screen variables (CV, SPD, DIFFP, RD, KURT, SKEW, KSTEST) 100% populated.

### IBM AMLworld HI-Small

Blocked on Kaggle credentials (this machine). After setup, `uv run poe data` downloads
`HI-Small_Trans.csv` + `HI-Small_Patterns.txt`, writes the manifest, and the license
string must be verified on the Kaggle listing. Needed from Week 3–5 (injection
calibration against the eight ground-truth patterns).
