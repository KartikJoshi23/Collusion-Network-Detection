# CollusionGraph — Progress Ledger

> **NUMBER RE-BASELINE (2026-07-16, PR #7).** A deep audit (30 findings) was fixed and every
> published number regenerated under the corrected protocol. Numbers quoted in the M1–M4
> entries below are SUPERSEDED by the "AUDIT FIX PASS" entry — headline changes: frozen
> train-time normalization removes an inadvertent test-time adaptation, dropping GNN test
> AUC-PR (GATv2 0.693→0.532) and widening the honest GADBench gap vs XGB (0.810); tie-aware
> metrics deflate rule/screen P@k; queue metrics shift accordingly.

## Current milestone

> ✅ **FRONTEND OVERHAUL DELIVERED [laptop-C, 2026-07-18]** per
> [`docs/frontend_overhaul.md`](docs/frontend_overhaul.md): animated network-canvas backdrop with
> coral flagged pulses, Motion throughout (view transitions, nav/domain sliding pills, KPI
> count-up, queue stagger, subdued risk pulse), glass/gradient-border panels over aurora washes +
> film grain, per-domain accent ramps (financial cyan→teal ⇄ procurement violet→magenta), motif
> SVG glyphs for all nine backend motif families, self-hosted variable fonts (Inter / JetBrains
> Mono / Space Grotesk), designed radar/error/empty states. Hard constraints held: ethics caveat
> on every screen (footer + dossier), `npm run build` + vitest green, backend 235/235 green,
> docker frontend image builds, API contract untouched (read-only, zero endpoint changes).
> **Integrated & re-verified on master 2026-07-18** (see Completed): master is demo-ready
> end-to-end on REAL artifacts (dev path :5173/:8000 AND `docker compose up` :8080), suite now
> 237/237 + frontend 8/8, and the procurement deep-link bug found during the walk is fixed.
> **⛔ RE-REVIEW VERDICT (2026-07-18, master): REJECTED AGAIN — "still horrible… single color
> dominant… massive overhaul needed". OVERHAUL V2 is now the top next action**, per the
> rewritten research-grounded brief in [`docs/frontend_overhaul.md`](docs/frontend_overhaul.md)
> (diagnosis: monochrome single-accent token usage, imperceptible glass, no hover language,
> §5.3 flagship features deferred). Phase-2 ML work stays gated behind UI acceptance (§7).
>
> ✅ **OVERHAUL V2 DELIVERED [laptop-C, 2026-07-18] — every item in the V2 brief's §3 built**
> (see Completed): simultaneous 5-hue token system (≥3 hue families at rest verified live on
> every screen), visible glass + bright 3-stop aurora, full hover language, GSAP showpieces
> (DrawSVG dossier schematics, temporal scrubber, ScrollTrigger About story), and the §5.3
> flagship features (alert constellation hero, queue badges/sparklines/measured-precision
> readout, real Model Lab charts with SVG/PNG export). Backend 237/237, frontend build +
> vitest 17/17, walked live on real artifacts in both domains. **Awaiting stakeholder review
> #3.**
>
> 🚀 **PHASE 2 OPENED [master, 2026-07-18] on the stakeholder's instruction** (Decision log:
> UI iteration deferred to the end; "remaining parts are very important"). V2 merge verified
> green on master (backend 237/237, frontend 17/17 + build). **First Phase-2 slice landed —
> §7 step 27:** PGExplainer + three-arm fidelity ablation; **verdict: PGExplainer adopted**
> for Elliptic++ bundles (PyG sanity 49/50 vs GNNExplainer 12/50, hard-fidelity necessity
> +0.034 vs ~0, 2.4× faster amortized) — regenerated bundles drop **fidelity_insane 38/50 →
> 1/50**. Suite 244/244. Next §7 items: step 26 (line-graph view, PNA/GIN+EU on AMLworld,
> actor-graph hetero), Week 11 Copilot (MC).

**M5 COMPLETE — MVP exit criterion met [master, 2026-07-18].** Clone → `poe demo` (+ `npm run dev`)
or `docker compose up` → dashboard → ranked alert → highlighted subgraph → explanation, both
domains. All five §5.3 views live and verified against the read-only API; 235 backend tests +
frontend build/test green. **Phase 1 MVP (M0–M5) done** *(the rejected UI visual design was
overhauled 2026-07-18 — see banner above)*. ⛔ Plan stop-point: MVP review with the
stakeholder before Phase-2 development (§7). Next when resumed: Phase 2 — Weeks 9–10 model depth
(line-graph/PNA/PGExplainer), Week 11 Copilot (MC). Detail of prior milestones below.

**M4 COMPLETE** (§7 definition: "Every top-k alert on both domains carries a validated explanation
bundle" — Elliptic++ 50/50 bundles with GNNExplainer minimal subgraphs + fidelity, 24 with matched
motifs + FATF flags; Mendeley 20/20 bundles with matcher + OECD evidence, learned attribution
deferred per the R12 finding below). The §9.1 flagship test passes: the motif matcher recovers
ALL TEN injected motif families with 100% recall on fixtures — matcher and injector are
independent implementations cross-validating each other. First procurement alert queue shipped:
Mendeley P@4 0.75 / P@18 0.56 vs 0.358 prevalence (within-sample) — the community roll-up
substantially rescues the weak R-GCN node scores. Week-6 stack merged to main via PR #6 on the
user's standing merge instruction.
**WEEK 7 COMPLETE (§7 steps 20–22) [master, 2026-07-17]:** transfer runners + real runs (LOCO
country_5 AUC-PR 0.80 vs 0.67 prevalence; cross-domain probes: fin→proc negative, proc→fin
weakly positive — see Completed), FastAPI artifact serving + torch-free docker image verified
live on Docker Desktop. Also this session: user-directed decisions (context-fusion B-CF verdict:
NOT adopted — negative result; AWS deployment plan in docs/deployment.md; NVIDIA NIM adopted
for the Week-11 Copilot LLM). Next: Week 8 (§7 steps 23–25, dashboard → M5).
**M3 COMPLETE** (§7 definition: "Ensemble + injection-recovery report" — both delivered on
Elliptic++; headline: calibrated fusion preserves the strong member with weak co-members —
AUC-PR 0.674 / P@100 1.00 vs the measured rank-fusion failure 0.056 — and the injection-recovery
report establishes the RQ2 baseline: small realistic motifs evade structure-only arms at budget,
only `common_control` is caught (floor, recall 1.0)). Week-5 stack (steps 14–16) built on
laptop-B, merged to main via PR #5 on the user's standing merge instruction. AMLworld-pattern
injector calibration deferred (needs Kaggle credentials on the running machine).
Next: Week 6 (§7 steps 17–19, explanations → M4).
**M2 COMPLETE** (documented-gap path: GNN P@100 0.99 vs XGB 1.00, AUC-PR 0.69 vs 0.81, causes in
the Decision log; GADBench's central finding replicated). Week-4 stack merged via PR #4.
**M0 COMPLETE**; **Week 2 (§7 steps 4–7) COMPLETE and pushed** (the previous "not yet pushed"
note was stale — origin/main carries b93717c…1713806, verified by anonymous clone 2026-07-15).
**Week 3 step 8 (§7) COMPLETE** on laptop-B: shared structural feature template + financial +
screens packs, all with as-of discipline (§9.1b), verified on real Elliptic++/Mendeley/García —
pushed as `feat/features-structural`, **PR #1 open and CI-green** (all four jobs; the lint failure
was an environment bug, fixed by pinning Python 3.11 — see Decision log), awaiting master-laptop
review + merge. (The earlier 403 push blocker resolved the right way: KartikJoshi23's pending
collaborator invitation to gagu00000 was accepted via `gh api` — write access confirmed 2026-07-15.)
**Week 3 step 9 (§7) COMPLETE** on laptop-B: evaluation harness (alert unit + hit rule + NMS dedup,
Precision@k / AUC-PR / FPR-Recall@budget, config-driven runs, `collusiongraph eval` CLI) — pushed as
`feat/eval-harness` (**stacked on PR #1**), PR #2 open, **CI green on all four jobs**.
**Week 3 step 10 (§7) COMPLETE → M1** on laptop-B: baselines B1–B3 on Elliptic++ and B1–B4 on
Mendeley firms, config-driven, leakage-safe — pushed as `feat/baselines-m1` (**stacked on PR #2**),
PR #3 open. Headline numbers in the Completed entry below.
Outstanding user actions: OpenAI key rotation (R18); flip the GitHub repo to private (re-verified
still public 2026-07-15 — anonymous clone succeeded).

## Completed
<!-- - YYYY-MM-DD · item · commit ref · [machine tag: master | laptop-B | ...] -->
- 2026-07-18 · **§7 STEP 27 → PGExplainer ADOPTED for Elliptic++ bundles (first Phase-2 slice).**
  *Built:* `explain/pgexplainer_runner.py` (amortized PGExplainer, same ego windows / top-k
  thresholding / `NodeExplanation` output as the GNNExplainer runner — drop-in; targets are the
  model's OWN hard predictions, so phenomenon-mode fidelity coincides with model-mode, no labels
  touched; GATv2-only R12 guard; seeded) + `explain/explainer_ablation.py` (three arms on the
  SAME top-50 queue members, scored with a UNIFORM hard-mask fidelity — probability deltas under
  hard edge removal/keep — plus PyG binary fidelity for the mask arms; config-driven, CLI `arms:`
  shape) + `supervised_model.explainer` switch in the bundle writer (loading refactored into
  shared `load_supervised_for_explaining`/`top_members_of`). 7 new tests (invariants,
  determinism, R12 rejections, hard-fidelity boundary identities, attention self-loop exclusion,
  end-to-end integration); **suite 244/244**, ruff/mypy/black green. *Measured (seed 0, real
  artifacts):* GNNExplainer 122.9s, hard-fid+ −0.0004, PyG-sane 12/50; **PGExplainer 51.3s,
  hard-fid+ +0.0335, hard-fid− −0.0232 (necessary AND more-than-sufficient), PyG-sane 49/50**;
  attention-only 2.9s, ~0 both ways. *Adopted:* `explanations_elliptic_pp.yaml` flipped to
  `explainer: pgexplainer`; regenerated 50/50 bundles — **fidelity_insane 38/50 → 1/50**, motif
  and red-flag counts unchanged (matcher independent); serving.json refreshed. Report at
  `eval_outputs/elliptic_pp/explainer_ablation/explainer_ablation.json` · [master]
- 2026-07-18 · **OVERHAUL V2 INTEGRATION VERIFIED ON MASTER**: pulled 9f8f794..c9cbce8
  fast-forward (three laptop-C commits — tokens, flagship views, ledger); npm install (gsap +
  @gsap/react, 0 vulns); backend 237/237, frontend vitest 17/17 + tsc + build green on this
  machine; `serving.json` regenerated for the queue-metrics ride-along (the measured-precision
  readout's data path) — both queues byte-identical (254/223). Only frontend + demo-artifacts
  script changed: API contract untouched, caveat everywhere, no secrets · [master]
- 2026-07-18 · **FRONTEND OVERHAUL V2 (second-rejection response — docs/frontend_overhaul.md V2 §3, all six workstreams).** *(1) Multi-hue token system:* five simultaneous hue families (cyan/violet/magenta/amber + reserved coral, teal benign) with the domain toggle shifting DOMINANCE only; chart tier validated with the dataviz six-checks against #0a0e17 (`lib/palette.ts`, pinned by `palette.test.ts` incl. the coral-exclusivity rule); **≥3 hue families at rest verified live** (Overview KPI band renders 4 distinct families). *(2) Visible glass:* 3-stop multi-hue aurora in BOTH domains bright enough to feed the blur, 22–38% alpha-gradient fills + `saturate(1.5)`, neon-edge interactive glass (`glass-neon`, per-panel `--panel-hue`), multi-hue drifting canvas. *(3) Hover language:* lift+glow cards, row accent-edge sweep, chip bloom + tooltips, button sheen sweep, cursor-following spotlight on the hero — transform/opacity/background only. *(4) GSAP showpieces (gsap + @gsap/react installed — all plugins free):* DrawSVG motif schematics drawing themselves in the dossier (9 scenes), temporal playback scrubber replaying REAL edge timestamps over Sigma (play/pause + scrub, amount-scaled widths where amounts exist per D1), ScrollTrigger About/Methodology story (§5.3 view 6 — NEW view, lazy-loaded 20 kB chunk) with the motif table draw-on. *(5) Flagship features:* alert-constellation hero (real ranked alerts, size=members, color=risk band, golden-angle layout labeled schematic), queue rows with red-flag badges (lazy bundle lookups, 404-tolerant), hover-drawn temporal sparklines from real windowed-subgraph timestamps (`lib/sparkline.ts`, tested — never synthesized), hover-revealed actions, measured-precision readout (nearest PUBLISHED budget, never interpolated; queue metrics now ride serving.json via `build_demo_artifacts.py`); Model Lab rebuilt: per-time-step AUC-PR bars (the step-43 crater figure) + precision@k lines with live budget marker + queue precision, hand-rolled SVG per the dataviz mark specs (visx deferred — plan §5.1 allows D3-direct/hand-rolled), SVG/PNG export on every chart (paper figures). *(6) Dossier redesign:* typed evidence cards with per-source labels, indicator-cited red-flag cards, fidelity tiles with the failed-sanity warning surfaced, technical appendix keeps the full payload inspectable. Reduced-motion collapses everything (Motion config + CSS + GSAP guards). **Verified:** backend 237/237, frontend build green (main 183 kB gzip + 20 kB About chunk) + vitest 17/17 (5 new pure-logic tests), live walk of all six views on REAL artifacts in both domains (constellation/charts/schematic/scrubber/badges/readout all confirmed rendering real data) · [laptop-C]
- 2026-07-18 · **INTEGRATION + MASTER DEMO-READY (Next action 2 executed on the master machine).**
  *Integration:* pulled 56ea4fc..f31a200 fast-forward; `feat/frontend-overhaul` confirmed fully
  contained in main (0 ahead) — verdict MERGE (already effected by laptop-C's 8a2fee7), remote
  branch deleted; contract spot-checks passed (caveat in the app-shell footer on every screen,
  zero API-contract changes in the merged diff, no secrets, MotifGlyph↔MotifType pinned by test);
  main verified green here: backend 236/236 → **237/237** with the new test, frontend build +
  vitest, ruff/mypy/black. *Master serving artifacts (full recipe from committed configs):*
  gatv2_focal test AUC-PR **0.5492 / P@100 0.96 — byte-identical to laptop-C** (laptop-B's
  published 0.5318 is the divergent machine; see Decision log), ensemble_calibrated **0.5246**
  (laptop-C 0.5242), elliptic explanations **50/50 (15 motif+FATF, fidelity_insane 38/50 —
  exactly laptop-C's numbers)**, mendeley **20/20 (0 motifs in top-20, as published)**, queues
  byte-reproduce (254 / 223), `serving.json` wired with `explanations` for BOTH datasets.
  *Verified live on master:* five views walked on the real API in both domains (dossier shows a
  real fan-in bundle with FATF-STRUCT-01 + attention + honest fidelity_sane=false; explorer
  101-node windowed subgraph; accent recolor #22d3ee→#a78bfa) AND the compose path (`docker
  compose up`: nginx :8080 → containerized api, artifact mounts live, images api 815 MB /
  frontend 75 MB) · [master]
- 2026-07-18 · **fix(frontend): cross-dataset deep links** — `/?view=case&alert=<mendeley…>`
  404'd the bundle: the initial dataset auto-select ran under the default `financial` domain, so
  a procurement alert was fetched under `elliptic_pp`. New `lib/deeplink.ts` resolves the
  alert-id's dataset prefix against `/datasets` and a `hydrateFromAlert` store action adopts its
  dataset+domain without clearing the selection; vitest 8/8 (deep-link table pinned). Found by
  walking the real demo path on master — the demo script's procurement deep links now work.
  Docker frontend image rebuilt with the fix · [master]
- 2026-07-18 · **fix(cli): `collusiongraph` console script + legacy-console help** — the CLI the
  docs/ledger reference as `uv run collusiongraph …` was never installed as an entry point
  (`[project.scripts]` added; `poe` tasks unchanged), and `--help` crashed with
  UnicodeEncodeError on cp1252 Windows consoles (the §/→ typography): stdout/stderr now degrade
  via `reconfigure(errors="replace")`; regression test runs `--help` under forced cp1252 —
  suite 237/237 · [master]
- 2026-07-18 · docs: collaborator handoff workflow (PROMPT A step 4.3) reconciled to the
  standing direct-merge policy — the user's uncommitted edit on master carried contradictory
  fragments of the old PR-only flow; wording made coherent (merge to `main` yourself; branch
  naming + description requirements kept) · [master]
- 2026-07-18 · **REAL SERVING ARTIFACTS ON LAPTOP-C (Next action 2 executed) + demo verified on real data.** Full pipeline from the committed configs: ingest (elliptic_pp 203,769/234,355; mendeley_eu 14,555/24,251 — ledger counts matched exactly) → GATv2 raw + multi + calibrated ensemble → cross-domain probe (source run = the mendeley demo scorer) + LOCO transfer → `poe demo-artifacts` (elliptic 254 alerts / mendeley 223 — identical to published) → 50/50 elliptic GNNExplainer bundles + 20/20 mendeley matcher bundles → `serving.json` complete with `explanations` wired for BOTH datasets. **Overhauled UI walked live against the real API**: Overview KPI deck, 101-node windowed subgraph in the Explorer, real bundle in Case Detail (fidelity + attention + evidence + caveat), both queues at budget 50, LOCO metrics in Model Lab. **Reproducibility record (seed 0, cross-machine):** LOCO 0.8025 / probe 0.1501 / GATv2-multi 0.3781 / queue P@50 0.32 / mendeley P@4 0.50 all **byte-reproduce** laptop-B's published numbers; raw GATv2 diverges (test AUC-PR **0.5492 vs 0.5318**, P@100 0.96 vs 0.95 — torch CPU scatter reductions are not bitwise deterministic across machines, early-stop trajectory shifts) and the calibrated ensemble follows its supervised member (**0.5242 vs 0.5103**); bundles: 15 motif+FATF (vs 16), fidelity_insane 38/50 (vs 41/50) — same R12 conclusion. Artifacts are per-machine and gitignored; only this record travels · [laptop-C]
- 2026-07-18 · **CLI transfer dispatch wired** — `collusiongraph train -c` now routes LOCO-transfer (`test_group`) and cross-domain-probe (`source`+`target`) configs to the Week-7 runners (they were library-API-only; the CLI silently mis-dispatched them to the GNN trainer). 2 new F22 dispatch tests; suite 236/236 · 0393600 · [laptop-C]
- 2026-07-18 · **FRONTEND VISUAL OVERHAUL (stakeholder-directed, docs/frontend_overhaul.md).** Everything in the brief's "to BUILD" list shipped: `components/bg/NetworkBackground.tsx` (full-viewport canvas — drifting nodes, proximity edges, coral flagged pulses travelling along edges; node count area-capped ≤80, pauses on hidden tab, static single frame under `prefers-reduced-motion`, recolors live on domain flip via MutationObserver on `data-domain`); Motion pass (`AnimatePresence` view transitions in ViewRouter, `layoutId` sliding pills on nav + domain toggle, KPI `CountUp` via imperative `animate()`, alert-queue row stagger delay-capped at 15 rows, dossier card stagger, `MotionConfig reducedMotion="user"`); `components/ui/Glass.tsx` + tokens.css glass system (translucent fill, backdrop-blur 14px, 1px gradient border via mask-composite, inner top-light); palette upgrade (aurora radial washes + SVG-turbulence film grain on `body::before/::after`, per-domain accent ramps cyan→teal / violet→magenta, gradient-clipped display headings); `components/ui/MotifGlyph.tsx` — nine schematic SVG glyphs mirroring backend `MotifType` exactly, **pinned by `lib/motifs.test.ts`**; self-hosted `@fontsource-variable` Inter + JetBrains Mono + Space Grotesk (imported in main.tsx — zero network font requests, offline-demo safe); designed states (radar-sweep loading, warning-glyph error, dashed-network empty); all five views restyled on the untouched API/state wiring; deep-link initial state `/?view=…&alert=…` for the demo script. **Verified live [laptop-C]:** `npm run build` (tsc+vite) green, vitest 6/6, backend 235/235, `docker compose build frontend` OK, and a full browser walk of all five views in BOTH domains against `collusiongraph serve` (fonts confirmed loaded, glass/backdrop confirmed computed, Sigma subgraph rendered, accent recolor confirmed #22d3ee→#a78bfa, caveat present on every screen) — served from a **synthetic schema-conformant store** (see Decision log). Bundle 144 kB gzip JS (was 100; Motion added) + ~29 kB CSS + fonts as separate woff2 · merge 8a2fee7 (6b38e6f/a0d8a7c/43b459a/dbd7ce4; direct merge under the standing merge instruction — gh CLI absent on laptop-C, no PR record) · [laptop-C]
- 2026-07-18 · laptop-C environment bootstrapped from a bare folder: init+fetch+checkout of origin/main (56ea4fc), uv sync (Py 3.11), npm install (192 pkgs, 0 vulns), `.env` from example (keys blank — none needed), datasets 4/5 downloaded+verified via `poe data` (amlworld `blocked` as designed — no Kaggle token on this machine); cold-clone baseline verified green BEFORE changes: backend 235/235, frontend build+test green · [laptop-C]
- 2026-07-18 · **WEEK 8 (§7 steps 23–25) → MILESTONE M5 (MVP exit criterion).** React+TS+Vite console (`frontend/`): Tailwind v4 design tokens (§5.2 dark "intelligence console", per-domain teal/violet recolor), TanStack Query + Zustand, all **five views** — Overview command deck, Alert Queue (budget slider), Graph Explorer (Sigma.js WebGL ego-network, members in coral, server-windowed subgraph), Case Detail dossier (JSON export), Model Lab (metrics + per-step step-43 breakdown) — plus domain toggle, dataset selector, designed loading/error/empty states, ethics footer on every screen. **Verified live end-to-end** (API + Vite): drove Overview → click alert → Graph Explorer (101-node windowed subgraph) → Model Lab, both domains, **zero console errors**. Demo path: `poe demo` (build artifacts + serve API) + `npm run dev`, or `docker compose up` (api + nginx frontend); `scripts/build_demo_artifacts.py` regenerates the two queues + `serving.json`; `docs/demo_script.md` is the 90-second walk. CI builds+tests the frontend. Slices A/B/C pushed · [master]
- 2026-07-17 · **§7 steps 20–21 RUNS → WEEK 7 COMPLETE.** *LOCO transfer (Mendeley, test=country_5, val=country_7, R-GCN on per-country z-scored structural channel):* test AUC-PR **0.8025 vs 0.667 prevalence**, P@10 0.90 / P@25 0.80 / R@50 0.825 (60 confirmed test firms — small pool, noted). *Cross-domain probes (frozen SAGE structural encoder → logistic probe):* **fin→proc NEGATIVE** — AUC-PR 0.284 < 0.358 prevalence; probe scores collapse to a near-single tie block (flat tie-aware P@k = 1/36), consistent with the weak structural-only source (elliptic source val 0.304). **proc→fin weakly POSITIVE** — AUC-PR 0.1502 vs 0.065 prevalence (~2.3×), P@200 0.41; far below within-domain models (GATv2 0.53 / XGB 0.81). RQ4 headline so far: transfer is asymmetric and source-strength-dependent — honest partial/negative result per §4.4; multi-seed + fine-tuning curves are the Phase-2 follow-up · runs under `eval_outputs/{mendeley_eu/transfer_loco_country_5, cross_domain/*}` · [master]
- 2026-07-17 · **§7 step 22 — FastAPI artifact serving + containers**: `backend/api/` (serving index, 7 read-only endpoints, server-side ego-window subgraphs that never ship `raw_features`, caveat on every response — 9 tests incl. the torch-free-import pin), `collusiongraph serve` CLI, `docker/Dockerfile.api` + root `docker-compose.yml` + `.dockerignore`; verified live in a container against real mounted artifacts · 870049e · [master]
- 2026-07-17 · **§7 steps 20–21 — transfer runners**: `training/transfer_run.py` — LOCO transfer (group-respecting early stopping on a held-out TRAIN country; test country scored on its own isolated subgraph; per-country z-scored structural channel) + cross-domain frozen probe (GraphSAGE encoder on source structural channel → frozen `embed()` → logistic probe on target train period → target test period; target-only normalization) — 4 tests; real runs recorded separately · 02eb9be · [master]
- 2026-07-17 · **Context-fusion (A13) implemented**: `ContextFusionEncoder` (per-family encoders + learned sigmoid gates) + `FusedModel` wrapper preserving GATv2 attention, multi-family `features: [raw, structural]` support with span tracking in the trainer, B-CF ablation configs, 10 tests. Verdict in the Decision log (NOT adopted — negative result recorded) · 0c7ca6c · [master]
- 2026-07-16 · **AUDIT FIX PASS — 30 findings fixed, every number regenerated (SUPERSEDES the numbers in the M1–M4 entries below).** Fix details in the Decision log; 34 new/updated regression tests (212 total). **Re-baselined results.** *Elliptic++ node-level (test 35–49, prevalence 0.065; frozen train normalization, tie-aware metrics):* B1 rules (5 rules — the dead burstiness rule removed) AUC-PR 0.0576 / P@100 0.00; B2 XGB 0.8076 / P@100 1.00 and B3 0.8104 / P@100 1.00 (unchanged — trees were never affected by F2–F4); GATv2-focal val 0.9508 → test 0.5318 / P@100 0.95; SAGE-focal 0.4743 / 0.85; SAGE-wce 0.3882 / 0.47 (focal's margin widens under the honest protocol); DOMINANT 0.041 / GAE 0.039 / floor 0.055; **ensemble_calibrated 0.5103 / P@100 0.93** vs ensemble_rank 0.0535 (robustness story unchanged). The GNN drop vs the M2 numbers is the F3 fix removing inadvertent test-time re-normalization — the old scoring pass was absorbing part of Elliptic's covariate shift; an EXPLICIT test-time-adaptation ablation is a legitimate Phase-2 arm, an accidental one is not a baseline. *Mendeley (as-of train labels; tie-aware):* **zero train-label flips at train_end=2013** — the F1 hole was real in protocol but did not contaminate this split's published numbers (measured); B1 0.3426 / P@18 0.47 (tie-corrected from 0.56), B2 0.3925 / 0.22, B3 0.3775 / 0.56, B4 0.3811 / 0.78, R-GCN val 0.9430 → test 0.2731. *Queues (artifact-capped, recalibrated):* Elliptic ensemble queue 254 alerts (64 mega-communities excluded at the artifact), alert-level P@50 0.32; Mendeley 223 alerts, P@4 0.50. *Explanations:* Elliptic 50/50 bundles — all with fidelity AND attention summaries; 16 with motif+FATF flags; **fidelity_sane=false on 41/50** (GNNExplainer explanation quality is poor on this model — previously invisible, now measured; PGExplainer/tuning is the Phase-2 answer). Mendeley 20/20 valid bundles, 0 motifs in the recalibrated top-20 (tiny 2-node communities lead; first motif match at rank 54 — matcher verified healthy). *Injection recovery (calibrated ensemble arm):* unchanged — floor catches common_control 1.0, everything else evades; the ensemble arm now honestly uses the primary fusion. · (PR #7) · [laptop-B]
- 2026-07-16 · **§7 steps 17–19 → MILESTONE M4** — explanation layer: `explain/motif_matcher.py` (pattern-level rules: directed cycles, fan stars, retention/hold pass-through chains, linked_to cliques, rotation, cover bids, market partition, coordinated co-bid clusters — **recovers all ten injected families with 100% recall, with negative controls on innocuous graphs**), `explain/redflags/` (curated FATF + OECD indicator tables; every matcher motif maps to ≥1 indicator, pinned by test), `explain/explainer_runner.py` (GNNExplainer on k-hop ego subgraphs with topk thresholding + fidelity±; **R12 de-risk finding: mask-based explanation aligns only with full-edge-set convs — GATv2 works, sliced-edge SAGE and per-relation RGCNConv are rejected with TypeError; R-GCN explanations need HeteroExplanation over true HeteroData (follow-up)**), `explain/bundles.py` (§4.4 pydantic bundle: locked caveat, resolvable red flags, evidence-source labels, D1 evidence adaptation — amount fields only where amounts exist; config-driven batch writer). Alert-queue upgrade: `precalibrated` scores path (ensemble queue). 23 new tests. **Runs: Elliptic++ ensemble-scored queue (P@50 0.38, parity with the SAGE queue) + 50/50 validated bundles (all with fidelity, 24 with motif+FATF flags); Mendeley first procurement queue (228 alerts from 1,283 test-window communities — only communities containing scored firms rank; P@4 0.75 / P@18 0.56 / P@36 0.47 vs prevalence 0.358, within-sample) + 20/20 validated bundles (5 with motif+OECD flags; fidelity absent by design per R12).** · (PR #6) · [laptop-B]
- 2026-07-16 · **§7 steps 14–16 → MILESTONE M3** — unsupervised arm + ensemble + injector: `models/unsupervised.py` (native DOMINANT-style and GAE-style GCN autoencoders — PyGOD is unusable here, see Decision log — plus the transparent structural floor), `models/ensemble.py` (**calibrated fusion** — members isotonic-calibrated on the validation pool, fused as weighted mean of calibrated probabilities — and rank fusion kept as the scale-free ablation), `injection/` (all five motif-table rows × both domains with geometry pinned by tests: cycle/fan_in/fan_out/common_control/pass_through and rotation/cover_bid/partition/common_control/coordinated_cluster; injector with ground-truth records, bridge-edge camouflage, background-untouched guarantee; `recovery_at_budget`), `training/ensemble_run.py` (config-driven `run_ensemble` + `run_injection_recovery`). 32 new tests (planted-anomaly detection, fusion invariants incl. noise-cannot-outvote-calibrated-strong, generator geometry, injector determinism/conformance). **Results — Elliptic++ test window: members DOMINANT 0.041 / GAE 0.039 / floor 0.055 (all ≤ prevalence 0.065 — illicit tx are not attribute outliers; the honest B5 answer) vs supervised GATv2 0.693; ensemble_calibrated 0.674 / P@100 1.00; ensemble_rank 0.056 / P@100 0.11 — the §4.4 calibrate-before-fusing requirement, measured. Injection recovery (25 instances / 160 members in 67,664 nodes, budgets 200/500/1000): floor catches common_control at recall 1.0 (linked_to clique lights clustering+triangles+k-core at once); cycle/fan_in/fan_out/pass_through at realistic sizes evade every arm at budget — the RQ2 baseline the Week-6 motif matcher and AMLworld calibration exist to beat.** · (PR #5) · [laptop-B]
- 2026-07-16 · **§7 steps 11–13 → MILESTONE M2** — supervised GNN core + first alert queue: `models/gnn.py` (direction-aware GraphSAGE with per-direction SAGE aggregations; GATv2 with the direction flag as edge feature and last-layer attention captured for Week-6; R-GCN over forward/reverse relations per IR edge type), `training/losses.py` (focal vs class-weighted CE — the RQ1 ablation pair), `training/graph_build.py` (IR→PyG: doubled edges + direction flags + relation ids; y∈{1,0,−1}, unknowns carry structure never gradient), `training/trainer.py` (config-driven: strict-inductive train graph ≤train_end, loss pool ≤loss_end, TEMPORAL val tail, early stop on val AUC-PR, per-graph z-scored inputs, scores → harness), `models/rollup.py` (Leiden on weighted undirected projection, singletons dropped; isotonic calibration on the val pool; §4.4 max+top-p-mean community scores), `artifacts/alert_store.py` (schema-conformant ranked alerts with the immutable caveat), `training/alert_queue.py` (test-window queue: calibrate → Leiden → roll-up → alerts → §4.5 harness). 23 new tests (§9.1 model sanity: overfit-single-batch, seed determinism, shapes, calibration monotonicity; end-to-end integration; training provably blind to test-period edges). **Results — Elliptic++ (test 35–49, prevalence 0.065): GATv2-focal test AUC-PR 0.693 / P@50 1.00 / P@100 0.99 / P@200 0.99 (val 0.951); SAGE-focal 0.652 / P@100 0.99; SAGE-weighted-CE 0.645 / P@100 0.90 — focal wins both arms. vs B2/B3 XGB (0.808/0.810, P@100 1.00): trees still lead — the GADBench prediction, causes in Decision log. Mendeley R-GCN: val 0.942 but test 0.285 < prevalence 0.358 — honest negative, era shift + weak award-tier signal (all M1 baselines also hover at prevalence). First end-to-end alert queue (SAGE-focal, test window, 67,504 nodes / 77,512 edges — matches the step-7 splitter count exactly): 318 Leiden communities → 254 alerts after the size cap (64 mega-communities excluded), alert-level P@50 0.40, illicit coverage@50 9.4%.** · (PR #4) · [laptop-B]
- 2026-07-15 · **§7 step 10 → MILESTONE M1** — baselines: `models/baselines.py` (B1 rules engine with train-only percentile thresholds; B2/B3 XGBoost with `scale_pos_weight`, NaN-native; GADBench-style `neighbor_mean_features` via scipy sparse matmul, NaN for isolated/unknown; B4 direction-adjusted screen z-composite) + `training/baseline_run.py` (one YAML = one sweep: strict split → as-of features → scores → harness → `scoreboard.json`) + committed experiment configs. `run_eval` now skips (never fakes) alert-level metrics when no alert queue exists yet. 20 new tests incl. as-of leakage negative controls for neighbor aggregation and rule thresholds. **Scoreboard (test-period, confirmed nodes only): Elliptic++ (train 1–34/test 35–49, 16,670 confirmed test nodes, 1,083 illicit): B1 rules AUC-PR 0.056 (below the 0.065 prevalence baseline; P@100=0 — the rules-FP-overload critique, measured), B2 XGB 0.808 / P@100 1.00, B3 XGB-Graph 0.810 / P@100 1.00 (B3≈B2 expected: Elliptic raw features already embed one-hop aggregates). Mendeley firms (within-sample, train ≤2013/test ≥2014, 363 test firms, 35.8% prevalence; budgets 4/18/36 = top 1/5/10%): B1 0.343, B2 0.393, B3 0.377, B4 screens 0.381 with P@18 0.78 — everything near prevalence: award-tier-only signals are weak firm discriminators; the GNN + co-bid/LOCO settings own that headroom.** · (PR #3) · [laptop-B]
- 2026-07-15 · **§7 step 9** — evaluation harness in `eval/`: `alert_unit.py` (greedy NMS dedup, Jaccard **strictly >** 0.5 suppresses, suppressed alerts carry their suppressor's `overlap_group`; n_members ≤ 100 size cap; ≥1-confirmed-member hit rule with `min_fraction` param ready for the Phase-2 ≥10%/≥25% sensitivity); `metrics.py` (node-level P@k / Recall@k / FPR@k / AUC-PR-with-prevalence-baseline validated against hand-computed values AND sklearn; alert-level queue metrics with honest `k_effective` truncation + illicit-coverage@budget); `report.py` (one YAML → `metrics.json`, optional W&B offline); first real CLI subcommand `collusiongraph eval -c <yaml>`; canonical §4.5 fragments in `configs/eval/`. 17 new tests incl. the §9.1 60%-overlap NMS fixture. Real-scale smoke: naive degree scorer on Elliptic++ 46,564 confirmed nodes in 0.03s — AUC-PR 0.084 vs prevalence 0.098 (degree alone is anti-informative; the baselines will contextualize) · (PR #2) · [laptop-B]
- 2026-07-15 · **§7 step 8** — feature layer: `features/structural.py` (§4.2 rule-2 template: multi-edge in/out degrees, triangle + mutual-dyad motif participation, clustering, k-core, Goh–Barabási burstiness, community-relative stats defaulting to weak components until Leiden, `zscore_per_graph`), `features/financial.py` (retention ratio, velocity, holding time via per-node asof-join, round-amount share, directional burstiness, sinusoidal time encodings), `features/screens.py` (award tier: within-market share, buyer/supplier HHI, normalized winner-rotation entropy; bid tier: CV/spread/DIFFP/RD/kurtosis/skew with quorum-nulls; co-bid stats) — every function takes `as_of` (§9.1b); 8-test as-of leakage suite with negative controls; `GraphStore.write_features` artifact path (+ DuckDB views). Real-data verified: Elliptic++ 203,769 nodes structural in 1.9s, as-of@34 = 136,265 visible nodes and equals the truncated graph exactly; Mendeley bid tier degrades to empty, 710 buyers with rotation entropy; García screens on 9,781 tenders, co-bid on exactly the 4 identified markets · a77e8d7 + 1855dc8 · [laptop-B]
- 2026-07-15 · **Bootstrap fix** — `download_data.py` now downloads when a manifest exists but the raw dir is absent (collaborator machines could previously never bootstrap: verify-only reported mismatch), then checksum-verifies against the committed manifest; 5 unit tests; proven live on this machine (4/5 datasets downloaded and `verified`; amlworld correctly `blocked` pending this machine's Kaggle token) · c5d5063 · [laptop-B]
- 2026-07-15 · laptop-B environment bootstrapped from a bare clone: uv 0.11.3 → Python 3.11.15, 188 packages, cold-clone suite 54/54 green before any changes · [laptop-B]
- 2026-07-14 · **§7 step 4** — CollusionGraph IR: pyarrow schemas + Pydantic rows for nodes/edges/labels/communities/alerts (§4.2, §3.2 verbatim), `GraphStore` (validated parquet write/read + zero-server DuckDB views + meta.json), `conform()` schema gate, alert-caveat lock (weakened ethics string is unconstructable) · b93717c · [master]
- 2026-07-14 · **§7 step 5** — financial adapters: Elliptic++ tx-graph (183 raw features, verified 203,769/234,355 on real data in 8.5s) and AMLworld account-graph (515,088 accounts / 5,078,345 pays edges with amounts; edge ground truth in raw_attrs; post-window fence value in meta) + golden-file fixture tests · 20e5a1c · [master]
- 2026-07-14 · **§7 step 6** — procurement adapters: Mendeley award-first (14,555 nodes / 24,251 edges, 7 countries; null-buyer rows → no buys_from edge) and García per-market (77,007 nodes / 111,046 edges; firm identities on 4/6 markets — Japan/Italy/Brazil/America carry `Competitors`, Swiss markets don't) + degradation-path fixtures (§9.1) · adc34a1 · [master]
- 2026-07-14 · **§7 step 7** — strict-inductive temporal splitter (train-induced subgraph only at train time; optional fence; unplaceable-time nodes excluded) + LOCO splitter (entity-disjoint, cross-group edges never bridge folds) + leakage checks that run at split construction AND in CI; 12-test leakage suite with negative controls replaces the wiring placeholder. Verified on real data: Elliptic++ 1–34/35–49 split withholds 77,512 test-period edges; AMLworld fence drops exactly the 1,108 poisoned tail edges; Mendeley yields 7 disjoint LOCO folds · 63d6e67 · [master]
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
- ~~Frontend overhaul V1 rejected → V2 required~~ **V2 DELIVERED [laptop-C] and verified on
  master (2026-07-18, see Completed); awaiting stakeholder review #3.** Nothing half-written.
  Per the stakeholder's 2026-07-18 instruction (Decision log), further UI iteration is
  deferred to the end — Phase-2 development proceeds now.
- **Phase 2 in progress [master]:** step 27 (PGExplainer) DONE; step 26 arms not started —
  see Next action 3 for the machine-matched menu (line-graph aux view is the CPU-feasible
  default; PNA/GIN+EU parity wants GPU + `NeighborLoader`; actor-graph data already on disk).
- ~~The overhaul was verified against a synthetic serving store on laptop-C~~ **Resolved
  2026-07-18 [master]:** the overhauled UI is verified against REAL artifacts on BOTH laptop-C
  and master; master walked all five views live in both domains and verified the compose path.
  Either machine can host the stakeholder demo as-is.
- Nothing else mid-implementation. Weeks 3–6 stacks + the audit fix pass are merged to main; feature branches deleted.
- Post-audit follow-ups queued in Next actions: explicit test-time-adaptation ablation (the F3 finding), PGExplainer for the 41/50 fidelity-insane explanations, HeteroExplanation (R12), AMLworld activation.
- Stratified (minority-enriched) neighbor sampling and `NeighborLoader` minibatching are deferred to the AMLworld run (full-batch is faster at Elliptic++ scale on CPU); the imbalance ablation shipped is focal-vs-weighted-CE.
- Procurement top-% budgets were resolved manually for Mendeley (4/18/36 = top 1/5/10% of the 363-firm test queue, in the experiment config); automatic percent→k resolution inside `run_eval` remains a nice-to-have.
- `eval_outputs/` is regenerable and gitignored: scoreboard numbers live in this ledger and PR #3's description; rerun `run_baselines('configs/experiment/baselines_<anchor>.yaml')` to reproduce (seeded, deterministic).
- AMLworld raw data is absent on laptop-B (Kaggle credentials are per-machine; script reports `blocked` as designed). Financial pack is untested at AMLworld scale (5M edges) — see Next action 5.

## Next actions (ordered, self-contained)
1. ~~FRONTEND OVERHAUL V2~~ **DONE on laptop-C (2026-07-18, see Completed)** — all six V2
   workstreams shipped and verified live on real artifacts in both domains; constraints held
   (caveat everywhere, read-only API, build+vitest+backend green, offline fonts,
   reduced-motion, one blurred layer per stack).
2. **[user/stakeholder] REVIEW #3 — the V2 UI** — `poe demo` + `npm run dev` (or
   `docker compose up` → :8080), walk all SIX views (About is new — the demo-day opener) in
   both domains; hover the queue rows (sparklines + actions), drag the budget slider
   (measured-precision readout), play the explorer's temporal scrubber, export a Model Lab
   chart. *(Phase-2 work no longer waits on this — stakeholder decision 2026-07-18, Decision
   log; further UI iteration is deferred to the end.)*
3. **Phase 2, next slice — §7 step 26 (pick by machine):** (a) **line-graph auxiliary view**
   (LineMVGNN-style edge→node duality; §4.4 table): CPU-feasible on Elliptic++ — build the
   line-graph transform in `training/graph_build.py` style, an aux-encoder whose embeddings
   concatenate into the main model, ablation config B-LG, §9.1 tests (transform correctness on
   toy graphs, leakage: transform runs per split graph), run vs the published GATv2 — either
   result is reportable; (b) **PNA + GIN+EU reference configs on AMLworld HI-Small** (Multi-GNN
   parity check): needs GPU (Colab/Kaggle) or a very patient CPU — master has the AMLworld raw
   data + IR store; wire `NeighborLoader` minibatching first (In-flight note); (c) **Elliptic++
   actor-graph heterogeneous experiment** (the 9-CSV actor tables are already downloaded).
   Start with (a) if on CPU. PGExplainer (step 27) is DONE — see Completed.
4. **Week 11 — Copilot (MC)** after (or in parallel with) step 26: port per §7 27a–c; user
   action first: create the NVIDIA NIM key at build.nvidia.com → `.env` `NVIDIA_API_KEY`
   (2026-07-17 decision).
5. ~~Produce REAL serving artifacts~~ **DONE on laptop-C AND master (2026-07-18, see
   Completed)** — both machines are demo-ready end-to-end. For any OTHER machine the recipe
   is unchanged: `poe data` → `collusiongraph ingest` (both datasets) → `train` the four configs
   (gatv2_focal, gatv2_focal_multi, ensemble, cross_domain_probe_proc2fin +
   transfer_loco_mendeley) → `poe demo-artifacts` → `explain` both datasets →
   `poe demo-artifacts` again (second pass wires `explanations/` into serving.json). The bare
   `uv run collusiongraph …` spelling now works on a fresh `uv sync` (console script added
   2026-07-18).
6. **[user]** Rotate/revoke the OpenAI API key exposed in `Gen-AI Chatbot/.../.env` AND embedded in the original `FIX_FRONTEND.md` (two exposures) at platform.openai.com.
7. **[user]** Make the GitHub repo private (plan requires a private repo): repo Settings → General → Danger Zone → Change visibility, or `gh repo edit KartikJoshi23/Collusion-Network-Detection --visibility private` after `gh auth login`. Also consider rotating the Kaggle token that was shared in a chat session.
8. Deferred small items: HeteroExplanation for R-GCN (R12 finding — mask-based explainer is GATv2-only); AMLworld injection-recovery calibration + feature packs + baselines + `NeighborLoader` training on a machine with Kaggle credentials; wire the datasets' **precomputed screens** through as B4 inputs (Mendeley `lot_bidscount`/`relative_value`, García screen columns in `raw_attrs`); automatic percent→k budget resolution in `run_eval`; Mendeley R-GCN follow-up (firm+tender joint supervision, García co-bid enrichment) before concluding graph signal is absent; degree-preserving null-model z-scores for the structural floor (Phase 2).

## Decision log
<!-- - YYYY-MM-DD · decision · rationale · plan section affected -->
- 2026-07-18 · **[master, stakeholder-directed] PHASE 2 UN-GATED before UI acceptance.** The
  stakeholder instructed: proceed with the remaining development from where the collaborator
  stopped — "UI can be modified or enhanced at the end as well, as remaining parts are very
  important." This supersedes the §7 ⛔ stop-point's strict reading: Phase-2 ML/product work
  proceeds now; the V2 UI awaits review #3 in parallel and further UI iteration is deferred to
  the end. Recorded because it re-orders the §7 gate, not because anyone disputed it · §7.
- 2026-07-18 · **[master] §7 STEP 27 ABLATION VERDICT: PGExplainer adopted for Elliptic++
  bundles; GNNExplainer demoted to alternative.** Grounds (seed 0, top-50 queue members, uniform
  hard-mask fidelity + PyG binary fidelity): PGExplainer's top-20 edges are the only arm whose
  removal measurably breaks the prediction (hard-fid+ +0.0335 vs ≈0 for GNNExplainer and
  attention-only) and whose subgraph alone reproduces it (hard-fid− −0.0232); PyG sanity 49/50
  vs 12/50; 2.4× faster and amortized (train once, explain any alert in one forward — the
  queue-scale property §7 step 27 wanted). Honest caveats: absolute probability deltas are small
  (the model is saturated-confident on these egos), and the amortized MLP is trained on the
  explained instances' own ego windows with the model's OWN predictions as targets (no labels,
  no leakage; standard PGExplainer deployment). GNNExplainer's collapse mirrors the audit-era
  finding (38/50 insane) — now measured against alternatives instead of tolerated. Config flip +
  regenerated bundles in Completed · §4.4, §7 step 27, R12 lineage.
  directed.** Verbatim: *"Still the UI is horrible, it should be something really impressive.
  It should be dark themed, I can hardly see anyother color, it a single color dominant at this
  stage, I am very disappointed with it. It should have glassmorphism effects, hover effects,
  amazing animations, use GSAP if needed, and so on, but still a massive overhaul is needed.
  This current stage is not at all presentable."* Root causes diagnosed in code (not re-argued):
  the whole console keys off ONE `--accent` pair of adjacent hues, glass fills are 4–7% alpha
  over a same-hue dim backdrop (imperceptible), hover states barely exist, and the §5.3
  flagship features (Cosmograph hero, queue sparklines/red-flag badges, GSAP scrubber, DrawSVG
  schematics, visx Model Lab, About page) were deferred as "optional" — they are the
  impressiveness and are now REQUIRED. `docs/frontend_overhaul.md` rewritten as the V2 brief
  (research-grounded: multi-hue OKLCH system, visible-glass recipe, hover inventory, GSAP
  showpieces; sources cited in the brief §7). Also directed this session: an honest
  remaining-work audit — Phase-1/M0–M5 ML scope is ON plan (§7 Weeks 1–8 all delivered +
  verified); remaining roadmap is Phase 2 Weeks 9–17 (MC, M6, M7, M8: model depth,
  Copilot, transfer science/multi-seed rigor, practitioner study + ablations, paper); the
  only off-plan consumption is UI rework, now on its third pass — while the frontend is
  actually BELOW the plan's own §5.3 spec, which V2 closes · §5.2/§5.3, §7, R11.: master's
  seed-0 runs are **byte-identical to laptop-C's** on every number including the
  nondeterministic-path ones (raw GATv2 0.5492 / P@100 0.96; bundles 15 motif+FATF,
  fidelity_insane 38/50) while laptop-B remains the divergent machine (0.5318; 16; 41/50) —
  ensemble differs only in the 4th decimal (0.5246 vs laptop-C 0.5242). So torch-CPU scatter
  nondeterminism is not unique per machine: two of three machines agree exactly; the ±0.02
  variance claim stands but is driven by hardware/thread topology classes, not per-run noise.
  Multi-seed protocol (R5) still subsumes this for publication · §4.5, §9.3, R5.
- 2026-07-18 · **[laptop-C] Cross-machine reproducibility measured, worth citing in the paper's
  reproducibility note**: with identical seeds/configs/lock, every deterministic-path number
  (LOCO, frozen probe, GATv2-multi, isotonic+Leiden queues) byte-reproduces across machines, but
  raw-GATv2 training does NOT (0.5492 laptop-C vs 0.5318 laptop-B) — torch CPU scatter reductions
  are order-nondeterministic across hardware, shifting the early-stop trajectory. Published
  single-seed GNN numbers therefore carry machine variance of roughly ±0.02 AUC-PR on Elliptic++;
  the Phase-2 multi-seed protocol (already planned for R5) should report mean±std and subsumes
  this. The demo/serving path is unaffected (it ships whatever run the machine produced, and the
  queue layer reproduced exactly) · §4.5, §9.3, R5.
- 2026-07-18 · **[laptop-C] Overhaul verification used a SYNTHETIC serving store** (scratchpad-only
  script fabricating two schema-conformant datasets `synthetic_financial`/`synthetic_procurement`
  via the real `GraphStore`/`Alert`/`conform` classes — 40 alerts each, all nine motifs, bundles,
  metrics — served by the real `collusiongraph serve`): laptop-C has no trained score runs and the
  frontend task needed a live API today, not a multi-hour pipeline. Every number in those
  screenshots is fake by construction and labeled `synthetic_`; **no synthetic artifact is in
  git**, and the real-artifact demo remains gated on Next action 2 · §9.2.
- 2026-07-18 · **[laptop-C] Deep-link initial state added to the console store** (`/?view=…&alert=…`,
  validated against the ViewId union; the initial dataset auto-select no longer clears a
  deep-linked alert selection — switching datasets still does): needed so the demo script can open
  a view directly, and used by this session's live verification. Also: `@fontsource-variable`
  packages over a Google-Fonts link (offline demo, per the brief); `.claude/launch.json` committed
  (dev-preview config; `settings.local.json` stays ignored) · §5.4, §5.1.
- 2026-07-18 · **[laptop-C] Motion policy**: `MotionConfig reducedMotion="user"` app-wide + CSS
  `@media (prefers-reduced-motion: reduce)` kills the canvas loop (single static frame), risk
  pulse, and radar sweep — §5.2's "animation communicates state, never decorates idly" enforced at
  both layers. Stagger delays are index-capped so long queues don't serialize their entrance.
  Known verification caveat: the in-tool browser pane runs tabs hidden (rAF frozen), so view
  transitions were verified via deep links + Motion's `skipAnimations` test hook rather than
  animated end-to-end; on a visible tab this is ordinary Motion behavior · §5.2, §9.2.
- 2026-07-18 · **[master → collaborator handoff] FRONTEND OVERHAUL directed by stakeholder.** Verbatim
  feedback: *"The UI looks completely pathetic, it is a complete piece of useless frontend, the
  frontend should be very modernised with modern tech used, this is just a thing which I cannot
  present at all, I didn't liked it all. It needs to have live animated backgrounds, framer,
  objects, impressive color scheme, make UI related to the theme and topic of the project as well,
  it needs a complete overhaul, this is completely useless."* Action: the functionally-complete but
  visually-rejected frontend (Weeks 8A–8C, `b4abe37`/`7a54f28`/`a7ed4db`) is handed to the
  collaborator for a full visual redesign per `docs/frontend_overhaul.md` (required tech: animated
  network-graph background, Framer Motion, glassmorphism, themed neon palette). Constraints held:
  ethics caveat on every screen, CI/build green, read-only API contract, working demo. A partial
  `index.html` overhaul fragment started on master was **reverted** to keep the handoff baseline
  clean — no half-code in the tree · §5.2/§5.3, R11.
- 2026-07-17 · **[master] AUDIT of this session's own commits (0c7ca6c..7cebc6b), 3 fixes.** (1) **Security — path traversal in `/explanations/{alert_id}`**: an unvalidated alert_id mapped to a filename; a backslash-encoded id (`..%5Csecret`) escaped the bundles dir and leaked an arbitrary JSON file on Windows (proven, then fixed). Fix: charset allowlist + resolved-path containment, regression test with 4 payloads. (2) **Robustness — cross-domain probe** silently loaded non-SAGE / fusion-encoder source weights into a plain `GraphSAGE` via leftover kwargs; now raises if the source encoder isn't GraphSAGE and strips fusion kwargs. (3) **Deployment doc** corrected to t3.micro per stakeholder guidance (was t4g.small), with the 1 GB-RAM/swap caveat. Context-fusion column-order (span-slice vs z-scored frame) audited and confirmed correct · security, §4.4, docs/deployment.md.
- 2026-07-17 · **[master] B-CF ABLATION VERDICT: gated context-fusion NOT adopted as default.** Seed-0, identical protocol on Elliptic++ (train≤34/test≥35): raw-only GATv2 (published) val 0.9508 / test AUC-PR 0.5318 / P@100 0.95; concat raw+structural val 0.9206 / test 0.3781 / P@100 0.80; **gated val 0.9483 / test 0.3242 / P@100 0.21**. The pre-registered "beats concat on val" rule technically fired — and is hereby recorded as a FLAWED selector: gated's val gain is validation overfitting (higher val, materially worse test under the t43 shift, R5). Two findings worth reporting: (a) adding the structural family to GATv2 input *hurts* test generalization on Elliptic++ regardless of fusion (shift-sensitive channel); (b) model selection on val AUC-PR is unreliable under temporal shift — multi-seed + shift-aware selection belongs in Phase 2. Default stays `fusion: concat`, published config stays raw-only; the encoder remains in-tree as ablation arm B-CF (negative result, honest per §4.4) · §4.4, A13, R5.
- 2026-07-17 · **[master] Docker verified on Docker Desktop**: `docker/Dockerfile.api` builds at **815 MB** (torch-free, pinned by `test_serving_never_imports_torch`; vs ~3.5 GB with torch), container serves `/api/v1/domains` + `/datasets` from read-only artifact mounts with the caveat attached; smoke container removed after test. Compose blueprint at repo root (frontend joins Week 8, copilot Week 11) · docs/deployment.md, A14.
- 2026-07-17 · **[master] INTEGRATION: collaborator Weeks 3–6 (M1–M4) + audit pass verified on the master machine** — pulled 1713806..132661f fast-forward, `uv sync` (no dep changes), full `poe check` green: **212/212 tests pass** locally; ledger claims spot-checked against the merged tree. Verdict: MERGE-state confirmed, `main` demoable · §7 workflow.
- 2026-07-17 · **[user-directed] Context-Fusion: ADOPTED, scoped** as a gated context-fusion input encoder for the §4.4 GNN family (per-family encoders over raw/structural/screen features + learned sigmoid gates; config `fusion: gated|concat`), shipped only if it beats concat on val AUC-PR — either result reported as ablation arm B-CF. Motivation: post-audit GNN gap (Elliptic++ GATv2 0.532 vs XGB 0.810 AUC-PR) is an input-representation weakness; 2025 context-aware GAD literature (context encoding + adaptive aggregation, AAAI-25 CGNN; multi-level fusion) targets exactly this. NOT adopted: multimodal/sensor-style fusion (no such modalities here — would be forceful) · §4.4, Appendix A13.
- 2026-07-17 · **[user-directed] Deployment & scalability plan written** (`docs/deployment.md`): 3-container decomposition (frontend / api / copilot) with the batch-ML-never-serves rule; AWS free-tier mapping under the 2025-revamped tier ($100+$100 credits, 6-month free plan, always-free CloudFront/Lambda): Track A demo = S3+CloudFront + one small EC2 on credits (≈$0 out of pocket), Track B scale = Lambda-container → ECS Fargate; cost table included. **Docker: adopted** — Dockerfiles + compose land WITH the API (§7 step 22), giving dev/prod parity; nothing containerized before the API exists · Appendix A14, §3.2.
- 2026-07-17 · **[user-directed] NVIDIA Developer Program: USEFUL, adopted for the Copilot LLM (Week 11)** — build.nvidia.com `nvapi-…` keys carry free inference credits (1,000→5,000, 40 RPM) on an OpenAI-compatible endpoint (`integrate.api.nvidia.com/v1`), so the ported chatbot's OpenAI client needs only base_url+key; retires R16's cost leg. NOT needed for GNN training (local/Colab GPUs suffice) or RAG embeddings (local sentence-transformers already planned). **User action when Week 11 starts: create the key at build.nvidia.com and put it in `.env` as `NVIDIA_API_KEY`** · §4.6, R16.
- 2026-07-13 · Renamed `implementation-plan .md` → `implementation-plan.md` (stray space) · matches §8 · §8.
- 2026-07-13 · Repo root = existing project folder; untriaged `Gen-AI Chatbot/` original stays on disk but gitignored (contains its own `.env`); key-free port source archived under `reference/genai-chatbot/` · §4.6, §8, R18.
- 2026-07-13 · Ruff RUF001/2/3 (ambiguous unicode) disabled: typographic dashes/§ mirror the plan documents · tooling only · §4.1.
- 2026-07-13 · García Rodríguez supplement **retrieved successfully** (ars.els-cdn.com mmc2.zip, HTTP 200; CC BY-NC-ND 4.0 per Crossref) — **fallback R2 NOT triggered** · §4.3 D3, §11 R2.
- 2026-07-13 · Mendeley prevalence **measured**: 6,548 of 15,616 rows have `is_cartel=1` (41.9%) — the file is a case-control research sample, not a population file; the statement's "15,000+ contracts awarded to cartel members" reads as the file's total row count. Protocol consequence: population-style Precision@top-% screening on Mendeley must be framed within-sample, or use the opentender population base in Phase 2 · §4.3 D4, §4.5.
- 2026-07-13 · Mendeley countries are **anonymized** (`country_1..country_7`) — LOCO folds fine, but country-name-keyed analyses are impossible without the companion paper's mapping · §4.3 D4.
- 2026-07-13 · `facts*.yaml` (218 KB TechNova domain content) NOT archived (Replace-list); `schema.yaml` + `goldens.json` archived as **structural templates** for the Week-11 rebuild · §4.6.
- 2026-07-13 · AMLworld post-window artifact **measured** (not "all laundering" as the Kaggle discussion suggests: 59.1% of the 1,108 post-Sep-10 tx) — Week-2 temporal splitter must drop or explicitly fence the post-window tail; `HI-Small_accounts.csv` (not in the plan's file list) also acquired for the adapter · §4.3 D2, §9.1.
- 2026-07-14 · **García "co-bid graphs apply fully" corrected**: the combined `All` file has NO bidder identities; per-market files carry `Competitors` (company ID) in Japan/Italy/Brazil/America only — the two Swiss markets are bid-price-without-identity. Adapter ingests per-market files; co-bid/awarded tier on 4/6 markets; earlier DATASETS.md phrasing overstated coverage · §4.3 D3, §4.2 rule 1.
- 2026-07-14 · IR conventions fixed at implementation: int64 dataset-specific time unit recorded in meta (`elliptic_time_step` / `epoch_minutes` / `year`); raw dataset features in `nodes.raw_features` (list<f32>); domain specifics in JSON `raw_attrs` (AMLworld edge-level ground truth rides there); the §4.2 structural template will live in a separate features artifact, never in nodes · §4.2.
- 2026-07-14 · Mendeley labels attach to **firms and tenders** (max of `is_cartel` over their awards, source `mendeley_is_cartel`); García labels attach to **bids** everywhere and **firms** where identified; rows with null `buyer_id` (~19.5%) yield no buyer node/edge · §4.3 D3/D4.
- 2026-07-14 · Splitter policy: nodes with null time are excluded from both sides of temporal splits (counted as `n_unplaced_nodes`); temporal gaps (embargo) supported via `test_start`; AMLworld fencing is the splitter's job (`fence_after=meta.primary_window_end`), adapters stay faithful to the raw data · §4.3, §9.1.
- 2026-07-15 · **Feature as-of policy**: under `as_of=T`, undated edges are EXCLUDED (they cannot be proven past — stricter than the splitter, which can afford undated train edges because it also gates on endpoint membership); `as_of=None` means "no temporal restriction" and is reserved for entity-disjoint LOCO/LOMO evaluation (the regime where undated data like García Italy stays usable). Leakage tests assert as-of ≡ truncated-graph equality plus negative controls · §9.1b.
- 2026-07-15 · Amount-derived financial features are **null (unknown), never 0.0 or NaN**, on amount-less datasets (Elliptic++): polars sums all-null columns to 0, which would have silently produced 0/0=NaN retention and poisoned per-graph z-scoring — guarded with quorum `when()` clauses; same quorum-null rule for bid screens below 2/3/4 bids · §4.3 D1, §4.4.
- 2026-07-15 · Community-relative structural stats default to **weakly connected components** until Leiden lands (§7 step 13); `structural_features` accepts an IR `communities` frame to swap them in without API change · §4.2 rule 2.
- 2026-07-15 · Feature packs are **variable-width artifacts** (`features_<pack>.parquet` + optional `features_<pack>.meta.json` recording `as_of`), written via `GraphStore.write_features` (only `node_id` is required), exposed as DuckDB views alongside IR tables; never merged into `nodes.parquet` (per the 2026-07-14 IR decision) · §3.2, §4.2.
- 2026-07-15 · Bid screens take **winner = lowest bid** (first-price sealed-bid convention of the García markets); winner-rotation entropy is Shannon entropy of a buyer's winner shares normalized to [0,1], null for single-winner buyers (rotation undefined, not zero) · §4.4.
- 2026-07-15 · `download_data.py` bootstrap semantics: manifest present + raw dir absent → fetch then verify against committed checksums; manifest present + raw dir present but mismatched → report mismatch, never silently re-fetch (corruption needs a human) · §7 handoff workflow.
- 2026-07-15 · **Python pinned to 3.11 via `.python-version`**: uv.lock forks numpy at the 3.12 boundary (2.4.6 below, 2.5.1 above); CI's setup-uv floated to Python 3.12 → numpy 2.5.1, whose PEP 695 `type`-statement stubs crash mypy (target 3.11). Surfaced by PR #1's `import igraph` (first checked import transitively reaching numpy stubs). Pinning the interpreter makes dev and CI resolve the same lock branch · §4.1 environment reproducibility.
- 2026-07-15 · **Alert-level FPR is reported as `false_alert_rate` (1 − precision@k)**: alert-level true negatives are ill-defined (there is no enumerable universe of non-alerts), so the §4.5 "FPR@budget" cell is served by node-level FPR@k (FP / all confirmed negatives) plus the alert-level false-alert rate — both in `metrics.json` · §4.5.
- 2026-07-15 · Harness conventions fixed: NMS suppresses on Jaccard **strictly greater** than the threshold; budgets larger than the queue truncate honestly (`k_effective` reported, never padded); the fractional hit rule's denominator is **confirmed members only** (unknowns are neither hits nor misses, §4.3 D1); AUC-PR always ships with its prevalence baseline · §4.5, §9.1.
- 2026-07-15 · Baseline feature-group boundary: **B2 "tabular" = per-node attributes only** (raw dataset features + financial pack on financial; award-tier screens on procurement); **B3 adds the graph channel** (structural template + GADBench neighborhood means — neighbor base: raw features on financial, structural on procurement). Train-side inputs (rule thresholds, matrices, neighbor means) computed as-of `train_end`; test rows featurized on the full inference graph (§4.3 D1 inference regime) · §4.5 B2/B3.
- 2026-07-15 · **Mendeley M1 baselines are firm-level and within-sample** (case-control file, 41.9% overall / 35.8% test prevalence — per the 2026-07-13 prevalence decision): tender-queue budgets resolved manually to k=4/18/36 (top 1/5/10% of the 363-firm test queue). Population-style claims wait for opentender/LOCO settings · §4.3 D4, §4.5.
- 2026-07-15 · `run_eval` skips alert-level metrics when no alert queue exists (M1 baselines are node-score-only; alerts arrive with the §7 step-13 roll-up) — skipped, never faked · §4.5.
- 2026-07-15 · Empty-graph dtype guard: frames built from possibly-empty node lists pin `node_id` to Utf8 (an empty as-of graph must not degrade schemas downstream) — found by the step-10 single-class split test · §9.1.
- 2026-07-16 · **GNN inputs are z-scored per graph** (train-graph stats for training, inference-graph stats for scoring): Elliptic's raw feature columns span wildly different scales — unstandardized they stalled optimization (SAGE val AUC-PR 0.258, best epoch 4); standardized, the same config reaches 0.947. Trees are scale-invariant, so B2/B3 were unaffected · §4.4, §9.1 model sanity.
- 2026-07-16 · **Temporal validation, never random** (§4.5 protocol): loss pool = confirmed nodes ≤ `loss_end` (Elliptic 29 / Mendeley 2010), validation = the confirmed tail of the train period (30–34 / 2011–2013), early stopping on val AUC-PR. Both pools must contain both classes or the trainer refuses to run · §9.1.
- 2026-07-16 · **M2 verdict documented**: XGB (B2/B3) still leads the GNNs on Elliptic++ (AUC-PR 0.81 vs 0.69; P@100 1.00 vs 0.99) — GADBench's central finding replicated. Understood causes: (a) Elliptic's 183 raw features already embed one-hop aggregates, handing trees the graph signal for free; (b) the step-43 dark-market shift punishes learned representations harder (val 0.95 → test 0.65–0.69 across all GNN arms while trees hold 0.81); (c) focal beats weighted-CE on both val and test in the head-to-head. The ensemble (Week 5) and injection (RQ2) are where the graph stack earns its keep · §4.5 M2, §10.2.
- 2026-07-16 · **Alert-queue framing**: the operational queue covers the TEST window only — Leiden runs on the test-period subgraph, calibration is fit on the validation pool, and the harness receives labels restricted to the test window so coverage denominators match the queue's scope. Leiden singletons are dropped (a 1-node community is a node ranking in disguise). Alert-level precision is depressed by the 77% unknown-label rate: unconfirmed alerts count as non-hits (never as hits) per §4.3 D1 — unconfirmed ≠ false, stated wherever these numbers appear · §4.5, §7 step 13.
- 2026-07-16 · **DEEP AUDIT (30 findings) → fix pass, all numbers regenerated.** The high-severity findings and their fixes: **(F1)** Mendeley firm labels rolled up the firm's ENTIRE history — future cartel awards leaked into train-period targets; fixed with `train_label_policy: mendeley_as_of` (labels derived from award-level ground truth at train_end via `mendeley_firm_labels_as_of`; test evaluation keeps stored full-knowledge labels; the same rollup caveat applies to AMLworld when it lands). **(F2)** the trainer saved validation scores from the INFERENCE graph (test-period adjacency touched downstream calibration); now saved from the train-graph forward that drives early stopping. **(F3)** per-graph z-scoring created train/serve normalization skew; the trainer now FITS stats on the train graph and freezes them (`feature_stats.json` beside the checkpoint; every downstream scorer/explainer loads them). `zscore_per_graph` remains the §4.2 rule-2 transfer-channel transform. **(F4)** P@k was order-arbitrary for tie-heavy scorers (B1's P@100=0 was partly a tie artifact); all @k metrics are now the EXPECTED value under uniform random tie-breaking (order-free, pinned by permutation test). **(F5)** the injection-recovery ensemble arm used the known-collapsed rank fusion; now calibrated fusion (primary mode). · audit report in PR #7.
- 2026-07-16 · Audit fixes, mechanical batch: fence keeps null-time nodes and counts them as unplaced, not fenced (F6, matching `restrict_as_of`); unsupervised projection edge type is config-explicit and an empty projection errors instead of silently autoencoding attributes (F7); pass-through matching is EDGE-level so embedded/bridged chains match — the old in-degree-0 head rule went blind on any chain attached to background traffic (F8); `simple_cycles` capped (`max_cycles`) and red flags deduped to one citation per indicator with instance counts (F9); trainer rejects `epochs/patience < 1` (F10); the §4.5 size cap is enforced AT THE ARTIFACT — mega-communities never enter `alerts.parquet` — with NMS as defense in depth, and score ties rank deterministically by community_id (F11, F29); node-level budgets truncate honestly with `k_effective` instead of silently dropping (F12); fidelity+≥fidelity− recorded per bundle as `fidelity_sane` — flagged, never blocking (F13); store artifact names sanitized against path/SQL-hostile strings (F14); GATv2 attention summaries now populate `attention_summary` (F15); per-time-step Elliptic metrics in the harness (F16, §4.3 D1); W&B path unit-tested with an offline default (F21); CLI `ingest/train/score/explain` wired with shape-dispatch and README made truthful incl. a same-machine reproducibility note (F22, F27); `docs/red_flag_mappings.md` written with the YAMLs as source of truth (F23); matcher thresholds config-exposed (F24); bridge edges respect node-type semantics (F26); remaining `explode` defaults pinned (F28).
- 2026-07-16 · **Audit fallout worth knowing:** the B1 `burstiness` rule on Elliptic was silently dead from day one — Elliptic edges connect transactions within a single time step, so inter-event gaps are all zero and burstiness is undefined for EVERY node (the old 0/0=NaN threshold never triggered; the null fix made `RulesEngine.fit` fail loudly). The rule is removed from the config (B1 now has 5 rules); temporal-gap features are structurally uninformative on Elliptic's tx graph and this is now stated rather than hidden · §4.4.
- 2026-07-16 · Audit items deliberately NOT fixed here (scope, not defects): AMLworld runs incl. injector pattern calibration (F17, blocked on Kaggle credentials); García downstream + LOMO (F18, §7 step 20); precomputed-screens passthrough (F19, with B4 follow-up); HeteroExplanation for R-GCN (F20/R12); null-model floor (Phase 2); NMS/mask-loop O(n²) scale work (F25, AMLworld-time); calibrated queue scores are low in absolute terms — UI copy must present them as calibrated probabilities, not percentages of certainty (F30) · ledger Next actions.
- 2026-07-16 · **R12 de-risk outcome (mask-based explainability)**: PyG's set-masks explanation hooks require every conv layer to consume the SAME edge set the explainer masks — GATv2 qualifies; direction-sliced GraphSAGE and per-relation RGCNConv do not (mask-size mismatch, verified). The explainer is GATv2-only, enforced with TypeError; R-GCN explanations need `HeteroExplanation` over true `HeteroData` models — a scoped follow-up, not attempted this week. Procurement bundles meanwhile carry matcher + screen evidence, labeled per §4.4 scope honesty · §7 step 17, §11 R12.
- 2026-07-16 · Bundle policy: not every ranked community contains a nameable motif (Elliptic 24/50, Mendeley 5/20 carried motif+flags) — a bundle without a motif match is still valid and shipped, leading with the evidence it has (learned subgraph/fidelity where available, structural/temporal always); `motif: null` is honest, never fabricated · §4.4, §9.1 explanation invariants.
- 2026-07-16 · Red-flag tables are paraphrased condensations of FATF indicator lists and the OECD bid-rigging checklist (curated, not verbatim); every matcher motif type must map to ≥1 indicator per domain — pinned by a vocabulary-completeness test · §4.4.
- 2026-07-16 · **PyGOD replaced by native detector implementations**: PyGOD 1.1's `fit` unconditionally routes through `NeighborLoader`, which requires the pyg-lib/torch-sparse compiled extensions §4.1 deliberately excludes on Windows — it cannot run in this environment. `models/unsupervised.py` implements DOMINANT-style (attr + inner-product structure reconstruction) and GAE-style (attr reconstruction) detectors natively on PyG, pinned by planted-anomaly tests; PyGOD stays an optional backend for machines with the extensions · §4.1, §4.4.
- 2026-07-16 · **Calibrated fusion is the primary §4.4 fusion**; equal-weight rank fusion is the measured failure mode (Elliptic++: three ≤-prevalence members outvote GATv2, 0.693 → 0.056) and is kept as an ablation. Isotonic calibration on the validation pool flattens near-random members to ~prevalence so they stop outvoting strong members (ensemble_calibrated 0.674 / P@100 1.00). Unsupervised members obtain validation scores by refitting on the train-window graph — never test · §4.4, §7 step 15.
- 2026-07-16 · **Structural floor simplification**: mean of positive per-graph z-scores over the structural template, instead of the planned degree-preserving null-model motif z-scores (Phase-2 upgrade). Transparent and cheap; it is the only arm that caught an injected motif family (common_control, recall 1.0) · §4.4.
- 2026-07-16 · **Injection-recovery baseline recorded honestly**: at realistic motif sizes (fan-in of 8 sub-threshold sources, 5-cycles, 5-hop pass-throughs) no arm recovers injected members at budgets ≤1000 on the 67.7k-node test window except the floor on common_control — small motifs hide in graph-scale statistics. This motivates the Week-6 motif matcher (pattern-level, not statistics-level) and the AMLworld pattern calibration (deferred: Kaggle credentials) · §4.4 item 4, §10.2 RQ2.
- 2026-07-16 · Injection generators consolidated into two domain modules (`generators/financial.py`, `generators/procurement.py`) instead of §8's ten per-motif files — same public registry, less file sprawl · §8.
- 2026-07-16 · **Week-3 stack merged to main from laptop-B on explicit user instruction** — a recorded deviation from the "master laptop integrates" rule (§7 collaboration workflow). CI was green on every PR head before merging; 126/126 tests re-verified on merged main. Bookkeeping note: PR #2 (`feat/eval-harness`) ended **closed-unmerged** — deleting PR #1's branch outside the PR flow closed it and GitHub cannot reopen a PR whose base ref is gone; its commits (d2ad3c3, beec8dc) reached main via PR #3, which was retargeted to main and merged. Merge refs: PR #1 380465c, PR #3 030b2fa · §7.

## Known issues
<!-- - description · discovered when · severity -->
- **Live OpenAI key exposed in TWO places** in the original chatbot folder (`.env` and `FIX_FRONTEND.md` line ~124). Redacted in the archived copy; originals untouched (user's data). **Rotate now** · 2026-07-13 · high until rotated.
- **GitHub repo is PUBLIC** (plan §7 requires private) — flip visibility; see Next action 2; re-verified still public 2026-07-15 (anonymous clone succeeded on laptop-B) · 2026-07-13 · medium.
- `gh` CLI token invalid on the master machine (pushes work via git credential manager; `gh`-dependent commands don't) — `gh auth login` when convenient. laptop-B status noted in the PR handoff. **laptop-C: gh not installed at all** — the 2026-07-18 overhaul landed as a direct no-ff merge (full PR-style description in the merge commit 8a2fee7); install+auth gh there if PR records are wanted from that machine · 2026-07-13 · low.
- CI gitleaks job failed on run #1 despite a clean local full-history scan — suspected gitleaks-action empty-`before` quirk on the first push to an empty repo; ledger header says run #2 was green; the `feat/features-structural` push will produce another data point · 2026-07-13 · low-medium.
- pre-commit's gitleaks hook builds via Go on first run (pre-commit bootstraps its own Go toolchain); first-commit hook setup took ~2 min on the master machine — expected, one-time per machine · 2026-07-13 · low.
- `collusiongraph` CLI: `eval` is implemented (step 9); the rest remain roadmap stubs (incl. `ingest`, whose adapters exist as library functions — wire with step 10's config-driven baseline runs) · 2026-07-15 · low.
