# Demo script (M5 exit criterion, §7 step 25 — kept current through Phase 2)

The MVP exit criterion: *a stranger clones the repo, runs one documented command,
opens the dashboard, and walks from a ranked alert to its highlighted subgraph and
explanation in both domains.* Phase 2 added the About story, the actor-level queue,
the rigor artifacts, and the Investigator Copilot — this script covers the product
as shipped.

## One-command demo (Docker — full API + frontend)

```bash
uv sync
uv run poe data                    # download datasets (Kaggle key only for AMLworld)
uv run collusiongraph ingest --dataset elliptic_pp
uv run collusiongraph ingest --dataset elliptic_pp_actor   # wallet-level view (26c)
uv run collusiongraph ingest --dataset mendeley_eu
# train score runs (or reuse eval_outputs/ from a prior run on this machine), then:
uv run poe demo-artifacts          # queues + rigor map + eval_outputs/serving.json
docker compose up --build          # api (:8000, internal) + frontend (:8080)
```

Open **http://localhost:8080**. For the Copilot, put an `nvapi-…` key in the
repo-root `.env` as `NVIDIA_API_KEY=` first (see `.env.example`) — without it the
console runs fine and the dock reports "not configured" honestly.

## Non-Docker demo (Windows dev machine)

```bash
uv run poe demo                    # builds artifacts, serves the API on :8000
# in another terminal:
cd frontend && npm install && npm run dev   # Vite on :5173, proxies /api → :8000
```

Open **http://localhost:5173**.

## The demo walk (~3 minutes; the bold beats are the 90-second cut)

1. **About** (nav, right end) — the scroll-driven opener: the
   *two-ledgers-one-structure* thesis, the nine-motif table drawing itself in as
   you scroll, the pipeline, and the scope boundary. This is the narrative frame —
   start here for a first-time audience.
2. **Overview** — the command deck: multi-hue KPI band (count-up numerals; coral
   is reserved for the flagged band) and the **alert constellation** — every node
   is a real ranked alert (size = community members, color = risk band; the layout
   is schematic, the ranks are real). **Cursor spotlight** follows the pointer.
   Click any constellation node to jump straight to its subgraph.
3. **Alert Queue** — drag the **budget slider**: the "showing k of top N" readout
   updates live and the **measured P@k readout** counts to the run's published
   precision at the nearest measured budget (never interpolated). **Hover a row**:
   a temporal sparkline draws itself from the alert's real windowed-subgraph
   timestamps, and the actions slide in — *subgraph*, *dossier*, and the
   *Copilot orbital mark* (ask the Copilot about this alert). Rows carry motif
   glyph chips and red-flag badges where a bundle cites indicators.
4. Click the top alert → **Graph Explorer** — the flagged community's ego-network
   in WebGL (Sigma.js): members coral, 1-hop context dimmed, windowed server-side
   (the browser never receives the full graph). Press **▶ replay flow** — the
   temporal scrubber replays the money flow in timestamp order (drag to scrub).
5. **Evidence dossier →** — the explanation bundle as typed evidence cards: the
   detected pattern with its **motif schematic drawing itself** (DrawSVG), red-flag
   cards citing FATF/OECD indicators with per-source labels, attribution-quality
   tiles (a failed fidelity sanity check is *shown*, never hidden), the full
   payload in the technical appendix, and **Export JSON** — the one
   case-management touchpoint in scope.
6. Flip the **domain toggle** to *Procurement* — the WebGL aurora re-hues live,
   the dominant accent shifts (the inventory stays multi-hue), and the dataset
   switches to the Mendeley EU cartel anchor. Repeat beats 3–5 on a cartel community. Back in *Financial*, the
   dataset selector also offers **elliptic_pp_actor** — the wallet-level queue
   (§4.5 reports both granularities; the actor head is the precise one at tight
   budgets, its community roll-up honestly weak).
7. **Model Lab** — the figure factory: per-time-step AUC-PR bars (the Elliptic
   step-43 shift is visible, not averaged away), measured precision@k with the
   live budget marker, queue precision — every chart exports SVG/PNG. Below it,
   the **Phase-2 rigor panel**: multi-seed spread (the published seed sits inside
   its band), LOCO/LOMO transfer matrices, paired-significance rows, the
   label-noise robustness curve, and the cross-domain label-efficiency curve —
   the honest-numbers story on one screen.
8. **Copilot** (header — the orbital-spark mark with the orbiting electron) —
   open the dock and ask, e.g., *"How many alerts are in
   the mendeley queue and what is the measured precision at budget 18?"* The
   agent's tool calls stream live into the trace timeline; the answer arrives
   with confidence + grounding badges, the evidence panel (every tool call and
   result), and the **AI-generated label + screening caveat on every response**.
   Asking a guilt-presupposing question ("is X guilty?") demonstrates the guard:
   the answer opens with "This system does not determine guilt."

Every screen carries the footer: *"screening signal only — no determination of guilt."*

## Notes

- If a dataset has no explanation bundles published locally, Case Detail shows the
  designed "no bundle" state — run `collusiongraph explain -c configs/experiment/explanations_<ds>.yaml`.
- The rigor panel shows exactly the artifacts this machine has produced (multi-seed
  campaigns, matrices, curves live under `eval_outputs/` and are exists-checked at
  `poe demo-artifacts` time) — absent artifacts are omitted, never faked.
- Deep links open any view directly: `/?view=queue`, `/?view=case&alert=<alert_id>`.
- Artifacts are gitignored and regenerated per machine; only code, configs, and
  `serving.json`'s shape travel in git.
