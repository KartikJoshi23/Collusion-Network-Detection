# CollusionGraph frontend

React + TypeScript + Vite investigator console (§5). Dark-only "intelligence
console" design language; consumes the read-only artifact API (`backend/api`).

**Visual overhaul delivered (2026-07-18)** per
[`../docs/frontend_overhaul.md`](../docs/frontend_overhaul.md): animated
network-canvas backdrop with coral flagged pulses, Motion transitions
(view switches, nav/domain pills, KPI count-up, queue stagger, risk pulse),
glass/gradient-border panels over aurora washes + film grain, per-domain
accent ramps (financial cyan→teal, procurement violet→magenta), motif SVG
glyphs for all nine backend motif families, self-hosted variable fonts
(Inter, JetBrains Mono, Space Grotesk — no network font requests). All
animation collapses under `prefers-reduced-motion`; the canvas caps its node
count and pauses when the tab is hidden.

## Develop

```bash
npm install
# in another terminal: uv run collusiongraph serve   (FastAPI on :8000)
npm run dev          # Vite on :5173, proxies /api → :8000
```

Point the dev proxy elsewhere with `VITE_API_TARGET`.
Deep links: `/?view=queue|explorer|case|lab&alert=<alert_id>` opens the
console on a view / alert (used by the demo script).

## Build / test

```bash
npm run build        # tsc -b && vite build → dist/
npm run test         # vitest (unit: formatters, motif vocabulary)
```

## Layout

```
src/
  api/        types, fetch client, TanStack Query hooks
  state/      zustand console store (domain, dataset, budget, selection, deep links)
  app/        layout shell, domain toggle, dataset selector, view router
  components/ bg/ (animated network canvas) · ui/ (glass, glyphs, chips, states, count-up)
  views/      overview, alert-queue, graph-explorer, case-detail, model-lab
  lib/        formatters, motif vocabulary (mirrors backend MotifType, pinned by test)
  styles/     tokens.css (design tokens: palette, glass, radar, risk-pulse)
```

Stack: Tailwind v4 (design tokens), TanStack Query, Zustand, Sigma.js (graph),
Motion, @fontsource variable fonts. The `copilot/` dock joins in Phase 2
(§4.6, Week 11).

The ethics caveat ("screening signal only — no determination of guilt")
renders on every screen — a scope-boundary requirement (§1.5, R11), not
decoration.
