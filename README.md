# CollusionGraph

**An explainable, imbalance-robust graph-learning framework for illicit-finance and bid-rigging integrity screening.**

Money laundering in a transaction ledger and bid rigging in a procurement ledger are the same
crime in two costumes: a small group of parties that should act independently instead
coordinates, and the evidence lives in the *shape of the network*, never in any single record.
CollusionGraph builds one graph-anomaly detection system that learns that shared shape, flags
suspicious subgraphs under a strict false-positive budget, explains each flag in the
investigator's own red-flag vocabulary, and studies whether a learned notion of "collusion
structure" transfers across both domains.

> **Ethics & scope statement.**
> CollusionGraph is a **risk-screening and triage instrument that ranks cases for human
> investigation — not an accusation engine. It produces no determination of guilt.**
> It processes only public and synthetic datasets; no personal or classified data is used at
> any point. Every alert carries a human-verifiable explanation and the fixed caveat
> *"screening signal only — no determination of guilt."* This constraint governs the ethics,
> the legal positioning, and the language of every output of the system, its UI, and the paper.

## Project documents

| Document | Role |
|---|---|
| [`Collusion-Network-Detection.md`](Collusion-Network-Detection.md) | Problem statement — the single source of truth for **what** |
| [`implementation-plan.md`](implementation-plan.md) | Implementation plan v3.0 — the single source of truth for **how** (architecture §3, ML stack §4, frontend §5, roadmap §7, layout §8, testing §9, risks §11) |
| [`handoff-prompt.md`](handoff-prompt.md) | Reusable session prompts (master/collaborator) for multi-machine development |
| [`PROGRESS.md`](PROGRESS.md) | Running ledger: milestone position, completed / in-flight / next actions, decision log |

## Quickstart (any machine)

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+ (frontend, from Week 8), git.

```powershell
git clone <repo-url>
cd collusiongraph
uv sync                      # creates .venv from the committed lockfile
uv run pre-commit install    # ruff + black + mypy + gitleaks on every commit
copy .env.example .env       # then fill in YOUR OWN keys (never committed)
uv run poe data              # downloads datasets, verifies checksums against data/manifests/
uv run poe test              # unit + leakage tests
```

All tasks are [poethepoet](https://poethepoet.natn.io/) tasks declared in `pyproject.toml` and
work identically in PowerShell and bash: `poe data`, `poe test`, `poe lint`, `poe ingest`,
`poe train`, `poe score`, `poe explain`, `poe eval`, `poe serve`, `poe demo-artifacts`,
`poe demo`.

## Demo (M5)

```powershell
uv run poe demo            # builds serving artifacts, serves the read-only API on :8000
# in another terminal:
cd frontend; npm install; npm run dev    # dashboard on :5173 (proxies /api → :8000)
```

Or the full container build: `docker compose up --build` → open `http://localhost:8080`.
Full walkthrough in [`docs/demo_script.md`](docs/demo_script.md).

## Running experiments

Everything is config-driven — one YAML in `configs/experiment/` = one reproducible run
(seeded; outputs land in the gitignored `eval_outputs/`):

```powershell
uv run poe ingest -- --dataset elliptic_pp             # adapter → IR store
uv run poe train  -- -c configs/experiment/gnn_elliptic_pp_gatv2_focal.yaml
uv run poe train  -- -c configs/experiment/baselines_elliptic_pp.yaml   # auto-dispatch
uv run poe score  -- -c configs/experiment/alert_queue_elliptic_pp_ensemble.yaml
uv run poe explain -- -c configs/experiment/explanations_elliptic_pp.yaml
```

Headline numbers and protocol decisions live in [`PROGRESS.md`](PROGRESS.md); reproducibility
is same-machine (XGBoost/torch thread-level determinism is not guaranteed across platforms).

### What git does NOT carry (per-machine bootstrap)

- `data/raw|interim|processed/` — datasets are re-downloaded via `poe data`; only
  checksum/license **manifests** are committed (`data/manifests/`).
- `.env` — each machine keeps its own keys, copied from `.env.example`. Never committed.
- Model checkpoints, `eval_outputs/`, `frontend/node_modules/`, the Python venv.

### Kaggle authentication (needed for IBM AMLworld)

1. Kaggle → account settings → *Create New API Token* → downloads `kaggle.json`.
2. Place it at `%USERPROFILE%\.kaggle\kaggle.json` (Windows) or `~/.kaggle/kaggle.json`
   (chmod 600 on *nix).
3. Re-run `uv run poe data`.

## Repository layout

Per `implementation-plan.md` §8 (abridged):

```
configs/            one YAML file = one reproducible experiment
data/manifests/     dataset checksums + licenses (committed; raw data never is)
backend/collusiongraph/   the Python package: schema, adapters, features, injection,
                          splits, models, training, explain, eval, artifacts, cli
backend/api/        FastAPI serving layer (precomputed artifacts; batch inference)
backend/tests/      unit / integration / leakage tests (leakage tests protect the paper)
frontend/           React + WebGL investigator console (scaffolded Week 8)
reference/          archived Gen-AI Chatbot port source (Phase-2 Investigator Copilot)
notebooks/          numbered EDA notebooks, read-only after merge
scripts/            download_data.py and other repo utilities
paper/              manuscript (Phase 2)
```

## Development workflow

- `main` is always green and demoable; feature work on `feat/<area>-<slug>` branches via PR.
- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:` + scope), small units.
- Every session starts from a prompt in `handoff-prompt.md` and ends by updating `PROGRESS.md`.
- Never commit: raw datasets, `.env`/secrets, or weakened ethics language. gitleaks runs
  in pre-commit and CI.

## License

Code is licensed under [Apache-2.0](LICENSE). Datasets are **not** redistributed in this
repository; their individual licenses are recorded in `data/manifests/` and each machine
downloads them from the canonical sources.
