# Demo script (M5 exit criterion, §7 step 25)

The MVP exit criterion: *a stranger clones the repo, runs one documented command,
opens the dashboard, and walks from a ranked alert to its highlighted subgraph and
explanation in both domains.*

## One-command demo (Docker — full API + frontend)

```bash
uv sync
uv run poe data                    # download datasets (Kaggle key for AMLworld)
uv run collusiongraph ingest --dataset elliptic_pp
uv run collusiongraph ingest --dataset mendeley_eu
# train score runs (or copy eval_outputs/ artifacts from a prior run), then:
uv run poe demo-artifacts          # builds alert queues + eval_outputs/serving.json
docker compose up --build          # api (:8000, internal) + frontend (:8080)
```

Open **http://localhost:8080**.

## Non-Docker demo (Windows dev machine)

```bash
uv run poe demo                    # builds artifacts, serves the API on :8000
# in another terminal:
cd frontend && npm install && npm run dev   # Vite on :5173, proxies /api → :8000
```

Open **http://localhost:5173**.

## The 90-second walk

1. **Overview** — the command deck: KPI band (domain, dataset, alerts in queue) and
   the top flagged communities with calibrated risk scores. The financial anchor
   (Elliptic++) is selected by default.
2. **Alert Queue** — drag the **budget slider**; the queue re-ranks and the
   "showing k of top N" readout updates live. Each row: risk chip, motif, member
   count, time window.
3. Click the top alert → **Graph Explorer** — the flagged community's ego-network
   renders in WebGL (Sigma.js), members in coral, 1-hop context dimmed. The
   subgraph is windowed server-side (never the full graph).
4. **Explanation dossier →** — the evidence bundle: motif, evidence fields, red-flag
   cards, fidelity; **Export JSON** is the one case-management touchpoint in scope.
5. Flip the **domain toggle** to *Procurement* → the console recolors (teal → violet)
   and the dataset switches to the Mendeley EU cartel anchor. Repeat the walk on a
   cartel community.
6. **Model Lab** — the published metrics with the per-time-step breakdown (the
   Elliptic step-43 distribution shift is visible, not averaged away).

Every screen carries the footer: *"screening signal only — no determination of guilt."*

## Notes

- If a dataset has no explanation bundles published locally, Case Detail shows the
  designed "no bundle" state — run `collusiongraph explain -c configs/experiment/explanations_<ds>.yaml`.
- Artifacts are gitignored and regenerated per machine; only code, configs, and
  `serving.json`'s shape travel in git.
