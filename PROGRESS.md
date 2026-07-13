# CollusionGraph — Progress Ledger

## Current milestone
M0 — Foundations (see implementation-plan.md §7 milestone table: M0–M5, MC, M6–M8)

## Completed
<!-- - YYYY-MM-DD · item · commit ref · [machine tag: master | laptop-B | ...] -->
- 2026-07-13 · Environment verified: Python 3.11.2, uv 0.11.28 (installed this session), Node 22.21.1/npm 9.6.4, git 2.51.2; `gh` 2.87.0 present but token invalid; Kaggle credentials absent · [master]
- 2026-07-13 · Repo scaffold per §8: monorepo layout, pyproject.toml (uv-managed, PyTorch/PyG pinned **without** compiled extensions, PyGOD), poethepoet tasks, package skeleton with all §8 subpackages, unit + leakage-wiring tests (14 passing), ruff/black/mypy green · [master]
- 2026-07-13 · Pre-commit config (ruff, black, mypy, gitleaks) + GitHub Actions CI skeleton (gitleaks, lint, unit + leakage tests, conditional frontend build) · [master]
- 2026-07-13 · `scripts/download_data.py`: download + sha256 checksum + license-recording manifests, manifest-verify mode for collaborator bootstrap, Kaggle auth documented, blockers reported without stalling · [master]

## In-flight
<!-- exactly what is unfinished, where, why, and which machine/branch has it -->
- Dataset acquisition sprint running (this session): Elliptic (PyG mirror), Mendeley EU cartel, García Rodríguez supplement, Elliptic++ (Google Drive via gdown), AMLworld HI-Small (blocked — see Known issues).
- Gen-AI Chatbot triage (this session): archive port source to `reference/genai-chatbot/`.
- EDA notebooks (this session).

## Next actions (ordered, self-contained)
1. Week 2 (§7 steps 4–7): implement CollusionGraph IR (Parquet schemas + Pydantic models + DuckDB catalog + alert schema) in `backend/collusiongraph/schema/`.
2. Week 2: financial adapter Elliptic++ → IR with golden-file tests on tiny fixtures (`backend/collusiongraph/adapters/financial.py`).
3. Week 2: procurement adapter Mendeley → IR (award-first graph + cartel labels) (`backend/collusiongraph/adapters/procurement.py`).
4. Week 2: strict-inductive temporal splitter + LOCO splitter with leakage assertion tests in CI, **replacing** `backend/tests/leakage/test_leakage_wiring.py`.

## Decision log
<!-- - YYYY-MM-DD · decision · rationale · plan section affected -->
- 2026-07-13 · Renamed `implementation-plan .md` → `implementation-plan.md` (stray space in filename) · matches §8 layout · §8.
- 2026-07-13 · Repo root = the existing project folder (`Collusion-Network-Detection/`); the untriaged `Gen-AI Chatbot/` original stays on disk but is gitignored (it contains its own `.env`); the key-free port source is archived under `reference/genai-chatbot/` · §4.6, §8, R18.
- 2026-07-13 · Ruff rules RUF001/2/3 (ambiguous unicode) disabled: typographic dashes/§-references mirror the plan documents and are project style · tooling only, no protocol impact · §4.1.
- 2026-07-13 · García Rodríguez supplement **is retrievable** (ars.els-cdn.com mmc2.zip, ~1.5 MB, HTTP 200; article OA under CC BY-NC-ND 4.0 per Crossref) — fallback R2 **not** triggered · §4.3 D3, §11 R2.

## Known issues
<!-- - description · discovered when · severity -->
- `gh` CLI token invalid on this machine (account KartikJoshi23) — repo cannot be created/pushed from this session; exact commands for the user recorded in the session report · 2026-07-13 · medium (blocks push only).
- Kaggle credentials absent (`%USERPROFILE%\.kaggle\kaggle.json`) — AMLworld HI-Small download blocked; setup steps documented in README.md and `scripts/download_data.py`; its exact license string must be verified on the Kaggle page at download time · 2026-07-13 · medium (D2 needed from Week 3–5 for injection calibration).
- The live OpenAI API key in the original chatbot `.env` must be **rotated/revoked by the user** (R18); the file never enters the repo (gitignored + never copied) · 2026-07-13 · high until rotated.
