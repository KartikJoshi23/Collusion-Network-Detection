# CollusionGraph — Progress Ledger

## Current milestone
M0 — Foundations (see implementation-plan.md §7 milestone table: M0–M5, MC, M6–M8).
**M0 status: complete on this machine except (a) GitHub push — `gh` token invalid, commands below; (b) AMLworld HI-Small — blocked on Kaggle credentials; (c) OpenAI key rotation — user action.**

## Completed
<!-- - YYYY-MM-DD · item · commit ref · [machine tag: master | laptop-B | ...] -->
- 2026-07-13 · Environment verified: Python 3.11.2, uv 0.11.28 (installed this session), Node 22.21.1/npm 9.6.4, git 2.51.2 · [master]
- 2026-07-13 · Repo scaffold per §8: monorepo layout, pyproject.toml (uv-managed, PyTorch/PyG pinned **without** compiled extensions, PyGOD), poethepoet tasks, package skeleton with all §8 subpackages, unit + leakage-wiring tests (14 passing), ruff/black/mypy green · 46dc03e · [master]
- 2026-07-13 · Pre-commit (ruff, black, mypy, gitleaks — gitleaks scans **everything** incl. reference/) + GitHub Actions CI skeleton (gitleaks, lint, unit + leakage tests, conditional frontend build) · 5717b29 · [master]
- 2026-07-13 · `scripts/download_data.py`: download + sha256 + license manifests, verify mode for collaborator bootstrap; Mendeley requires stdlib urllib (its CDN 403s python-requests TLS fingerprint) · 6fcbc89 · [master]
- 2026-07-13 · Datasets acquired + manifested (4/5): Elliptic++ (9 CSVs ~2.2 GB), Elliptic base (PyG mirror), Mendeley EU cartel (sha256 matches Mendeley's official API hash), García Rodríguez supplement · 9f0d274 · [master]
- 2026-07-13 · Gen-AI Chatbot triage per §4.6: 70 files archived to `reference/genai-chatbot/` (graph/retrieval/tools/ingestion/api + all 7 frontend components + docs + goldens harness); TechNova data/results/scripts/caches/`.env` excluded; **a live-looking OpenAI key found embedded in FIX_FRONTEND.md was redacted in the archive copy** · 9ddc285 · [master]
- 2026-07-13 · EDA notebooks 01–04 executed: **Elliptic++ 6/6 checks PASS** (203,769 nodes / 234,355 edges / 49 steps / 183 features / 4,545 illicit / 42,019 licit / 77.1% unknown / 2.23% prevalence); **Elliptic base 6/6 PASS**; **Mendeley: 73 cartel cases verified exactly**, prevalence measured (see Decision log), losing-bidder coverage mapped (zero identity coverage; `lot_bidscount` 100% everywhere); **García: 64,348 bids / 9,781 tenders / 6 markets, 54,389 losing bids present, screens 100%** — findings in `docs/DATASETS.md` · [master]

## In-flight
<!-- exactly what is unfinished, where, why, and which machine/branch has it -->
- Nothing mid-implementation. Remaining M0 items are user actions (see Next actions 1–3).

## Next actions (ordered, self-contained)
1. **[user]** Rotate/revoke the OpenAI API key exposed in `Gen-AI Chatbot/.../.env` AND embedded in the original `FIX_FRONTEND.md` (two exposures) at platform.openai.com.
2. **[user]** Re-authenticate GitHub and push: `gh auth login -h github.com`, then from the repo root:
   `gh repo create collusiongraph --private --source . --remote origin --push`
   (or create the private repo in the web UI and `git remote add origin <url> && git push -u origin main`). Verify CI goes green on GitHub Actions.
3. **[user]** Kaggle auth (kaggle.com → account → Create New API Token → save to `%USERPROFILE%\.kaggle\kaggle.json`), then `uv run poe data` to fetch AMLworld HI-Small; verify the license string on the Kaggle listing and update `data/manifests/amlworld_hi_small.json` notes.
4. Week 2 (§7 step 4): implement CollusionGraph IR (Parquet schemas + Pydantic models + DuckDB catalog + alert schema per §3.2/§4.2) in `backend/collusiongraph/schema/`.
5. Week 2 (§7 step 5): financial adapter Elliptic++ → IR with golden-file tests on tiny fixtures.
6. Week 2 (§7 step 6): procurement adapter Mendeley → IR (award-first + cartel labels) and García Rodríguez → IR (bid-level, co-bid edges); include an award-only fixture to prove the enrichment-degradation path (§9.1).
7. Week 2 (§7 step 7): strict-inductive temporal splitter + LOCO splitter with leakage assertion tests, **replacing** `backend/tests/leakage/test_leakage_wiring.py`.

## Decision log
<!-- - YYYY-MM-DD · decision · rationale · plan section affected -->
- 2026-07-13 · Renamed `implementation-plan .md` → `implementation-plan.md` (stray space) · matches §8 · §8.
- 2026-07-13 · Repo root = existing project folder; untriaged `Gen-AI Chatbot/` original stays on disk but gitignored (contains its own `.env`); key-free port source archived under `reference/genai-chatbot/` · §4.6, §8, R18.
- 2026-07-13 · Ruff RUF001/2/3 (ambiguous unicode) disabled: typographic dashes/§ mirror the plan documents · tooling only · §4.1.
- 2026-07-13 · García Rodríguez supplement **retrieved successfully** (ars.els-cdn.com mmc2.zip, HTTP 200; CC BY-NC-ND 4.0 per Crossref) — **fallback R2 NOT triggered** · §4.3 D3, §11 R2.
- 2026-07-13 · Mendeley prevalence **measured**: 6,548 of 15,616 rows have `is_cartel=1` (41.9%) — the file is a case-control research sample, not a population file; the statement's "15,000+ contracts awarded to cartel members" reads as the file's total row count. Protocol consequence: population-style Precision@top-% screening on Mendeley must be framed within-sample, or use the opentender population base in Phase 2 · §4.3 D4, §4.5.
- 2026-07-13 · Mendeley countries are **anonymized** (`country_1..country_7`) — LOCO folds fine, but country-name-keyed analyses are impossible without the companion paper's mapping · §4.3 D4.
- 2026-07-13 · `facts*.yaml` (218 KB TechNova domain content) NOT archived (Replace-list); `schema.yaml` + `goldens.json` archived as **structural templates** for the Week-11 rebuild · §4.6.

## Known issues
<!-- - description · discovered when · severity -->
- **Live OpenAI key exposed in TWO places** in the original chatbot folder (`.env` and `FIX_FRONTEND.md` line ~124). Redacted in the archived copy; originals untouched (user's data). **Rotate now** · 2026-07-13 · high until rotated.
- `gh` token invalid (account KartikJoshi23) — push blocked; see Next action 2 · 2026-07-13 · medium.
- Kaggle credentials absent — AMLworld HI-Small blocked; see Next action 3; needed by Week 3–5 (injection calibration) · 2026-07-13 · medium.
- pre-commit's gitleaks hook builds via Go on first run (pre-commit bootstraps its own Go toolchain); first-commit hook setup took ~2 min on this machine — expected, one-time per machine · 2026-07-13 · low.
