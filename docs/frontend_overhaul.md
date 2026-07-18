# Frontend Overhaul — Collaborator Brief

**Status: DELIVERED [laptop-C, 2026-07-18] — awaiting stakeholder re-review.**
Everything in §3 ("to BUILD") shipped; the hard constraints in §4 were held (caveat on
every screen, build/CI green, API untouched, docker image builds). See PROGRESS.md
(Completed 2026-07-18 + Decision log) for what was built and how it was verified, and
`frontend/README.md` for the resulting layout. The §5.3-optional flourishes (GSAP
scrubber, Cosmograph hero, visx charts) were deliberately deferred — queued in
PROGRESS.md "In-flight" if the stakeholder wants more. The brief below is kept verbatim
as the record of the ask.

---

## 1. Stakeholder feedback — verbatim (2026-07-18)

> "The UI looks completely pathetic, it is a complete piece of useless frontend, the
> frontend should be very modernised with modern tech used, this is just a thing which I
> cannot present at all, I didn't liked it all. It needs to have live animated backgrounds,
> framer, objects, impressive color scheme, make UI related to the theme and topic of the
> project as well, it needs a complete overhaul, this is completely useless."

Distilled requirements:

1. **Live animated background(s)** — motion in the backdrop, not a static flat color.
2. **Framer Motion** — the `motion` package (motion.dev, formerly Framer Motion) is
   **already a dependency** (`frontend/package.json`) but is currently used **nowhere**.
   Use it for enter/exit transitions, layout animations, stagger, hover/tap, count-up.
3. **Objects / depth** — glassmorphism, layered panels, glow, 3D/parallax touches.
4. **Impressive color scheme** — richer than the current flat graphite; gradients + neon
   accents are expected. Keep it dark (investigator console, §5.2 of implementation-plan).
5. **Themed to the project** — this is a *collusion-network / graph-intelligence* tool for
   *illicit-finance and bid-rigging* screening. The visuals should evoke that: network
   graphs, nodes/edges, money-flow, radar/scan, motif shapes. Not a generic dashboard.

## 2. What EXISTS today and is REUSABLE (do not rebuild these)

The plumbing is done and correct — keep it and restyle on top of it:

| Area | Files | Keep because |
|---|---|---|
| Build config | `vite.config.ts`, `tsconfig*.json`, `package.json` (+lock) | Vite 7 + React 18 + TS + Tailwind v4 (`@tailwindcss/vite`) all wired; `motion`, `sigma`, `graphology`, TanStack Query all installed |
| Design tokens | `src/styles/tokens.css`, `src/index.css` | CSS-variable token system + Tailwind `@theme` mapping already exists — **extend the palette here**, don't start over |
| API layer | `src/api/{client,hooks,types}.ts` | Typed, TanStack-Query hooks over the **live read-only API** (`backend/api/app.py`). Do not change the contract |
| Console state | `src/state/console.ts` | Zustand store: domain / dataset / budget / selection / view. `data-domain` is mirrored to `<html>` so tokens recolor per domain already |
| Views (logic) | `src/views/*/` (overview, alert-queue, graph-explorer, case-detail, model-lab) | All five fetch real data and render it. The **data wiring is correct**; only the presentation is rejected |
| Graph explorer | `src/views/graph-explorer/GraphExplorer.tsx` | Sigma.js v3 ego-network over `/subgraph/{id}` — keep the Sigma integration, restyle node/edge/glow |
| Deploy | `frontend/Dockerfile`, `frontend/nginx.conf`, root `docker-compose.yml` | nginx serves the build and proxies `/api`; the demo path works |

## 3. What is MISSING / to BUILD (the overhaul itself)

None of the below exists yet — this is net-new work:

- **Animated network background component** (e.g. `src/components/bg/NetworkBackground.tsx`):
  a full-viewport `<canvas>` of drifting nodes + edges with occasional coral "flagged"
  pulses travelling along edges. Low opacity behind content; **must** honor
  `prefers-reduced-motion` (render one static frame) and cap node count for perf.
- **Framer Motion throughout**: wrap view switches in `AnimatePresence` (see `ViewRouter.tsx`),
  stagger the alert-queue rows, `layoutId` sliding indicator on the nav (`App.tsx`), count-up
  the KPI numerals (Overview), subtle risk-pulse on high-risk chips (`components/ui/Chips.tsx`).
- **Glass + glow panel primitive** (e.g. `src/components/ui/Glass.tsx`): `backdrop-blur`,
  translucent fill, 1px gradient border, inner glow — replace the flat `bg-bg-1` panels.
- **Palette upgrade** in `tokens.css`: gradient accent ramps (financial cyan→teal,
  procurement violet→magenta), gradient-clipped display headings, richer risk colors, grain.
- **Motif glyphs** (e.g. `src/components/ui/MotifGlyph.tsx`): small SVG icons per motif
  (cycle, fan-in, fan-out, rotation, cover-bid, …) used on alert rows and the case dossier.
- **Fonts**: `tokens.css` references Inter + JetBrains Mono but they are **never loaded**
  (currently falling back to system fonts). Add them — **prefer self-hosted/`@fontsource`
  over a Google Fonts `<link>`** so the offline Docker demo doesn't depend on the network.
  A display face (e.g. Space Grotesk) for headings would help the "modern" ask.

## 4. Hard constraints — DO NOT break these during the overhaul

- **Ethics caveat stays on every screen.** The footer in `App.tsx` renders
  `SCREENING_CAVEAT` ("screening signal only — no determination of guilt"). It is a
  scope-boundary requirement (implementation-plan §1.5, §5.2, R11), not decoration. No
  guilt/accusation language may be introduced anywhere in copy.
- **Keep it building and CI-green.** CI runs `npm ci && npm run build` (see
  `.github/workflows/ci.yml`); `npm run build` must stay clean (tsc + vite). Keep the one
  vitest (`src/lib/format.test.ts`) passing and add tests for new pure logic.
- **Keep the API read-only and unchanged.** The frontend consumes REST only, never writes
  (§3.2). Don't add client-side data mutation.
- **Keep the demo path working** (`docker compose up` / `poe demo`).
- **Performance budget (§9.2):** graph explorer interactive at ~5k nodes; the animated
  background must not tank it — throttle/cap and respect reduced-motion.

## 5. Suggested order of work

1. Palette + fonts + a `Glass` primitive in `tokens.css` / `components/ui/` — the visual
   language first (everything else inherits it).
2. `NetworkBackground` canvas mounted once in `App.tsx` behind `<main>`.
3. Motion pass: `ViewRouter` transitions → nav indicator → Overview count-up → queue stagger.
4. Per-view polish: Overview command deck (hero + KPIs), Alert Queue (motif glyphs +
   animated budget→precision readout), Graph Explorer (node glow, temporal scrubber),
   Case Detail (animated motif schematic), Model Lab (charts — see the `dataviz` skill).
5. Re-verify: `npm run build`, `docker compose up`, walk the demo path in both domains.

## 6. Pointers

- Visual design language spec: `implementation-plan.md` §5.2 ("intelligence console") and
  §5.3 (the seven views) — already written, follow it.
- The current (rejected) look is the baseline in git at commit `a7ed4db`; diff against it
  as you go so nothing wired gets lost.
- No half-written overhaul code was left in the tree — you are starting from a clean,
  green, functionally-complete baseline. Build the visual layer on top.
