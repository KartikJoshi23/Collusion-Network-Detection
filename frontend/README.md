# CollusionGraph frontend

React + TypeScript + Vite investigator console (§5). Dark-only "intelligence
console" design language; consumes the read-only artifact API (`backend/api`).

## Develop

```bash
npm install
# in another terminal: uv run collusiongraph serve   (FastAPI on :8000)
npm run dev          # Vite on :5173, proxies /api → :8000
```

Point the dev proxy elsewhere with `VITE_API_TARGET`.

## Build / test

```bash
npm run build        # tsc -b && vite build → dist/
npm run test         # vitest (unit: formatters, state)
```

## Layout

```
src/
  api/        types, fetch client, TanStack Query hooks
  state/      zustand console store (domain, dataset, budget, selection)
  app/        layout shell, domain toggle, dataset selector, view router
  components/ ui/ (states, chips) — design system
  views/      overview, alert-queue, graph-explorer, case-detail, model-lab (Week 8B)
  lib/        formatters
  styles/     tokens.css (design tokens)
```

Stack: Tailwind v4 (design tokens), TanStack Query, Zustand, Sigma.js (graph),
Motion. The `copilot/` dock joins in Phase 2 (§4.6, Week 11).
