# CollusionGraph — Progress Ledger

## Current milestone
M0 — Foundations (see implementation-plan.md §7 milestone table: M0–M5, MC, M6–M8).
**M0 status: COMPLETE — all 5 datasets downloaded/checksummed/licensed/EDA'd, repo pushed to GitHub. Outstanding user actions: OpenAI key rotation (R18) and flipping the GitHub repo to private.**

## Completed
<!-- - YYYY-MM-DD · item · commit ref · [machine tag: master | laptop-B | ...] -->
- 2026-07-13 · Environment verified: Python 3.11.2, uv 0.11.28 (installed this session), Node 22.21.1/npm 9.6.4, git 2.51.2 · [master]
- 2026-07-13 · Repo scaffold per §8: monorepo layout, pyproject.toml (uv-managed, PyTorch/PyG pinned **without** compiled extensions, PyGOD), poethepoet tasks, package skeleton with all §8 subpackages, unit + leakage-wiring tests (14 passing), ruff/black/mypy green · 46dc03e · [master]
- 2026-07-13 · Pre-commit (ruff, black, mypy, gitleaks — gitleaks scans **everything** incl. reference/) + GitHub Actions CI skeleton (gitleaks, lint, unit + leakage tests, conditional frontend build) · 5717b29 · [master]
- 2026-07-13 · `scripts/download_data.py`: download + sha256 + license manifests, verify mode for collaborator bootstrap; Mendeley requires stdlib urllib (its CDN 403s python-requests TLS fingerprint) · 6fcbc89 · [master]
- 2026-07-13 · Datasets acquired + manifested (4/5): Elliptic++ (9 CSVs ~2.2 GB), Elliptic base (PyG mirror), Mendeley EU cartel (sha256 matches Mendeley's official API hash), García Rodríguez supplement · 9f0d274 · [master]
- 2026-07-13 · Gen-AI Chatbot triage per §4.6: 70 files archived to `reference/genai-chatbot/` (graph/retrieval/tools/ingestion/api + all 7 frontend components + docs + goldens harness); TechNova data/results/scripts/caches/`.env` excluded; **a live-looking OpenAI key found embedded in FIX_FRONTEND.md was redacted in the archive copy** · 9ddc285 · [master]
- 2026-07-13 · Pushed to GitHub (github.com/KartikJoshi23/Collusion-Network-Detection) via git credential manager; CI run #1: lint/test/frontend green, gitleaks job failed (suspected first-push empty-`before` quirk — local full-history `gitleaks detect` is clean; watch run #2) · [master]
- 2026-07-13 · AMLworld HI-Small downloaded via new-style Kaggle token (KAGGLE_API_TOKEN env; script + .env.example updated), manifested; license **verified: CDLA-Sharing-1.0**; EDA notebook 05: 5,078,345 tx / 515,080 accounts / 5,177 laundering (1 per 980); all 8 pattern types confirmed; post-window tail measured (1,108 tx after Sep 10 are 59.1% laundering — splitter trap) · [master]
- 2026-07-13 · EDA notebooks 01–04 executed: **Elliptic++ 6/6 checks PASS** (203,769 nodes / 234,355 edges / 49 steps / 183 features / 4,545 illicit / 42,019 licit / 77.1% unknown / 2.23% prevalence); **Elliptic base 6/6 PASS**; **Mendeley: 73 cartel cases verified exactly**, prevalence measured (see Decision log), losing-bidder coverage mapped (zero identity coverage; `lot_bidscount` 100% everywhere); **García: 64,348 bids / 9,781 tenders / 6 markets, 54,389 losing bids present, screens 100%** — findings in `docs/DATASETS.md` · [master]

## In-flight
<!-- exactly what is unfinished, where, why, and which machine/branch has it -->
- Nothing mid-implementation. Remaining M0 loose ends are user actions (Next actions 1–2).

## Next actions (ordered, self-contained)
1. **[user]** Rotate/revoke the OpenAI API key exposed in `Gen-AI Chatbot/.../.env` AND embedded in the original `FIX_FRONTEND.md` (two exposures) at platform.openai.com.
2. **[user]** Make the GitHub repo private (plan requires a private repo): repo Settings → General → Danger Zone → Change visibility, or `gh repo edit KartikJoshi23/Collusion-Network-Detection --visibility private` after `gh auth login`. Also consider rotating the Kaggle token that was shared in a chat session.
3. Week 2 (§7 step 4): implement CollusionGraph IR (Parquet schemas + Pydantic models + DuckDB catalog + alert schema per §3.2/§4.2) in `backend/collusiongraph/schema/`.
4. Week 2 (§7 step 5): financial adapter Elliptic++ → IR with golden-file tests on tiny fixtures. AMLworld adapter must drop/flag the post-window tail (see Decision log).
5. Week 2 (§7 step 6): procurement adapter Mendeley → IR (award-first + cartel labels) and García Rodríguez → IR (bid-level, co-bid edges); include an award-only fixture to prove the enrichment-degradation path (§9.1).
6. Week 2 (§7 step 7): strict-inductive temporal splitter + LOCO splitter with leakage assertion tests, **replacing** `backend/tests/leakage/test_leakage_wiring.py`.

## Decision log
<!-- - YYYY-MM-DD · decision · rationale · plan section affected -->
- 2026-07-13 · Renamed `implementation-plan .md` → `implementation-plan.md` (stray space) · matches §8 · §8.
- 2026-07-13 · Repo root = existing project folder; untriaged `Gen-AI Chatbot/` original stays on disk but gitignored (contains its own `.env`); key-free port source archived under `reference/genai-chatbot/` · §4.6, §8, R18.
- 2026-07-13 · Ruff RUF001/2/3 (ambiguous unicode) disabled: typographic dashes/§ mirror the plan documents · tooling only · §4.1.
- 2026-07-13 · García Rodríguez supplement **retrieved successfully** (ars.els-cdn.com mmc2.zip, HTTP 200; CC BY-NC-ND 4.0 per Crossref) — **fallback R2 NOT triggered** · §4.3 D3, §11 R2.
- 2026-07-13 · Mendeley prevalence **measured**: 6,548 of 15,616 rows have `is_cartel=1` (41.9%) — the file is a case-control research sample, not a population file; the statement's "15,000+ contracts awarded to cartel members" reads as the file's total row count. Protocol consequence: population-style Precision@top-% screening on Mendeley must be framed within-sample, or use the opentender population base in Phase 2 · §4.3 D4, §4.5.
- 2026-07-13 · Mendeley countries are **anonymized** (`country_1..country_7`) — LOCO folds fine, but country-name-keyed analyses are impossible without the companion paper's mapping · §4.3 D4.
- 2026-07-13 · `facts*.yaml` (218 KB TechNova domain content) NOT archived (Replace-list); `schema.yaml` + `goldens.json` archived as **structural templates** for the Week-11 rebuild · §4.6.
- 2026-07-13 · AMLworld post-window artifact **measured** (not "all laundering" as the Kaggle discussion suggests: 59.1% of the 1,108 post-Sep-10 tx) — Week-2 temporal splitter must drop or explicitly fence the post-window tail; `HI-Small_accounts.csv` (not in the plan's file list) also acquired for the adapter · §4.3 D2, §9.1.

## Known issues
<!-- - description · discovered when · severity -->
- **Live OpenAI key exposed in TWO places** in the original chatbot folder (`.env` and `FIX_FRONTEND.md` line ~124). Redacted in the archived copy; originals untouched (user's data). **Rotate now** · 2026-07-13 · high until rotated.
- **GitHub repo is PUBLIC** (plan §7 requires private) — flip visibility; see Next action 2 · 2026-07-13 · medium.
- `gh` CLI token still invalid (pushes work via git credential manager; `gh`-dependent commands don't) — `gh auth login` when convenient · 2026-07-13 · low.
- CI gitleaks job failed on run #1 despite a clean local full-history scan — suspected gitleaks-action empty-`before` quirk on the first push to an empty repo; if run #2 also fails, replace the action with a direct `gitleaks detect` CLI step · 2026-07-13 · low-medium.
- pre-commit's gitleaks hook builds via Go on first run (pre-commit bootstraps its own Go toolchain); first-commit hook setup took ~2 min on this machine — expected, one-time per machine · 2026-07-13 · low.
