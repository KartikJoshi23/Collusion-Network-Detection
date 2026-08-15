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
  api/        types, fetch client, TanStack Query hooks, copilot SSE client
              (the archive's CRLF-fixed parser, pure + tested)
  state/      zustand console store (domain, dataset, budget, selection,
              deep links, copilot open/seed)
  app/        layout shell, domain toggle, dataset selector, view router
  components/ bg/ (animated network canvas) · ui/ (glass, glyphs, schematics,
              chips, states, count-up) · charts/ (SVG figure factory + export)
              · copilot/ (the §5.3 view-7 dock: bubbles, live trace, badges,
              evidence, AI label + caveat)
  views/      overview (constellation hero), alert-queue, graph-explorer
              (temporal scrubber), case-detail (dossier), model-lab, about
              (ScrollTrigger story)
  lib/        formatters, motif vocabulary + palette (pinned by tests),
              sparkline + metrics extractors (pure, tested)
  styles/     tokens.css (V2 multi-hue system, glass, hover language)
```

Stack: Tailwind v4 (design tokens), TanStack Query, Zustand, Sigma.js (graph),
Motion, GSAP (DrawSVG/ScrollTrigger), @fontsource variable fonts.

The ethics caveat ("screening signal only — no determination of guilt")
renders on every screen — a scope-boundary requirement (§1.5, R11), not
decoration.
