# Frontend Overhaul — Collaborator Brief (V2)

**Status: V2 DELIVERED [laptop-C, 2026-07-18] — awaiting stakeholder review #3.**
All six §3 workstreams below shipped (multi-hue tokens with the ≥3-families-at-rest rule
verified live, visible glass over a bright 3-stop aurora, the full §3.3 hover inventory,
GSAP DrawSVG schematics + temporal scrubber + ScrollTrigger About story, the §3.5 flagship
features, dossier redesign). Constraints in §4 held: backend 237/237, frontend build +
vitest 17/17, caveat on every screen, read-only API untouched, offline fonts,
reduced-motion collapse. Detail in PROGRESS.md (Completed, 2026-07-18 V2 entry). The brief
below is kept verbatim as the record of the ask.

*(Historical status: V2 was REQUIRED after the V1 overhaul was rejected at stakeholder
re-review 2026-07-18 — V1 shipped its full scope but read as a flat single-color dark
dashboard. V1's record is in §8.)*

---

## 1. Stakeholder feedback — verbatim (2026-07-18, second rejection)

> "Still the UI is horrible, it should be something really impressive. It should be dark
> themed, I can hardly see anyother color, it a single color dominant at this stage, I am
> very disappointed with it. It should have glassmorphism effects, hover effects, amazing
> animations, use GSAP if needed, and so on, but still a massive overhaul is needed. This
> current stage is not at all presentable."

Distilled: dark theme is right; the **monochrome single-accent look is the core failure**;
glass must be *visible*; every interactive surface needs hover feedback; motion must be
*impressive* (GSAP explicitly sanctioned); the bar is "best UI", not "acceptable".

## 2. Diagnosis — WHY it reads flat (root causes in the current code)

1. **One hue family owns every screen.** `tokens.css` drives nav pills, chips, buttons,
   KPI accents, glass glows, headings, the background canvas AND the aurora washes off a
   single `--accent`/`--accent-2` pair — and the pairs are *adjacent hues* (cyan→teal,
   violet→magenta), so the "gradient" reads as one color. Risk coral/amber exist but only
   in tiny chips. Net: near-black page + one hue = the "single color dominant" complaint.
2. **The glass is imperceptible.** `--glass-fill` is 4–7% alpha over a *dark, same-hue*
   backdrop. Glassmorphism only reads when a **vibrant, multi-hue, moving backdrop** shows
   through the blur — our aurora is too dim and too monochrome for the panels to look like
   glass at all.
3. **Almost no hover language.** Rows/cards change `background` slightly; nothing lifts,
   glows, or reveals. The console feels static under the cursor.
4. **The plan's own showpiece features were deferred** — and they ARE the impressiveness.
   §5.3 already specifies: Cosmograph/Sigma mini-map hero, motif chips + red-flag counts +
   sparklines on queue rows, animated precision@k readout, GSAP temporal scrubber, DrawSVG
   motif schematics, community hulls, visx chart factory, ScrollTrigger About page. None
   are built. **V2 = build the plan's §5.3, properly.**

## 3. Design direction (researched — sources in §7)

### 3.1 Palette: from "one accent" to a functional multi-hue system
- Keep the near-black navy base (`#0A0E17` family — industry standard for data-dense dark
  UIs) and JetBrains Mono numerals (Bloomberg-terminal vocabulary: dense tables, mono
  numerics, scannable in low light).
- Rebuild tokens as a **simultaneous 5-hue functional system** (OKLCH recommended so
  lightness steps stay perceptually even across hues):
  `cyan` (financial/structure) · `violet` (procurement/models) · `magenta` (highlights,
  gradients' third stop) · `amber` (medium risk, money amounts, warnings) · `coral`
  (flagged/high-risk ONLY — keep the §5.2 exclusivity rule) · `teal/green` (benign/healthy).
  **Every screen must show ≥3 hue families at rest** (e.g. Overview: cyan KPIs, amber
  amounts, coral flagged communities, violet model chips). The domain toggle shifts which
  hue *dominates* — it must no longer recolor the entire inventory to one family.
- **Aurora backdrop, 3 stops, always multi-hue** (aurora gradients need exactly ~3 distinct
  hues — more muddies, one reads flat): cyan → violet → magenta simultaneously in BOTH
  domains, brighter than today (it must visibly feed the glass blur), with the film grain
  kept on top.
- Gradient-clipped display headings stay; give charts/chips the full hue inventory.

### 3.2 Glassmorphism that is actually visible
- Panel recipe (per current best practice): `backdrop-filter: blur(10–20px)`; fill as an
  **alpha gradient** (lighter top-left → darker bottom-right, ~`rgba(30,30,50,0.25–0.35)`
  range over the brightened aurora — up from today's 4–7%); 1px gradient border (keep the
  mask-composite technique); inner top-light; **neon edge stroke / inner glow on
  interactive glass** so elements read at night.
- Layering rule: max 1 blurred layer per stack (no nested `backdrop-filter` — perf), and
  the backdrop behind glass must be vivid enough that blur is *evident*.

### 3.3 Hover micro-interaction inventory (every interactive element gets one)
- Cards/rows: `transform: translateY(-2/-4px)` + accent glow shadow + border brighten —
  transition `transform`/`background`/`box-shadow` only (never animate `backdrop-filter`).
- Alert rows: hover reveals actions (open explorer / dossier / export) sliding in.
- Chips/motif glyphs: glow bloom + tooltip naming the motif family.
- Buttons: gradient sheen sweep on hover; pressed state compresses.
- Hero/Overview: **cursor-following radial spotlight** on the network hero (a radial
  gradient that trails the pointer — cheap, dramatic, dark-UI-native).
- KPI tiles: sparkline draws itself on hover (DrawSVG).

### 3.4 Motion: Motion (the library) for state, GSAP for the showpieces
Motion's `AnimatePresence`/`layoutId`/stagger from V1 stay. GSAP (all plugins free since
2024/2025) is now REQUIRED for what §5.2/§5.3 always specified:
- **DrawSVG motif schematics** in Case Detail — the detected motif (fan-in, cycle,
  rotation…) draws itself stroke-by-stroke in the dossier (the RQ3 money shot).
- **Temporal playback scrubber** in Graph Explorer — a GSAP timeline replays the money
  flow / award sequence over the Sigma canvas (scrub = timeline.progress()); eased
  camera moves via Sigma camera API driven by GSAP.
- **About/Methodology page (§5.3 view 6)** — ScrollTrigger scroll-driven story of the
  two-ledgers-one-structure thesis with the motif table animating in (scrub-linked
  draw-on) — this doubles as the demo-day opener the stakeholder presents.
- **Odometer/scramble numerals** for KPIs (GSAP or keep Motion CountUp, but add the
  odometer roll), charts that draw on (line draw, bars grow, heatmap cells cascade).
- Ambient: slow drifting particles/gradient shift in the hero; flagged pulses travelling
  along edges (MotionPath) — the V1 canvas already does a version of this; brighten it.
- Non-negotiables kept: `prefers-reduced-motion` collapses everything to static frames;
  animation communicates state, never idles (§5.2); stagger caps stay.

### 3.5 Build the missing §5.3 flagship features (this IS the overhaul)
1. **Overview hero:** full-ledger mini-map (Cosmograph if feasible — pre-exported
   downsampled layout JSON, offline; else a Sigma constellation) with flagged communities
   glowing coral; KPI band on glass above it.
2. **Alert Queue rows:** motif glyph chip (exists) + **red-flag count badge** + **temporal
   sparkline** per row (data available in alerts/bundles); budget slider animates the
   **precision@k readout** (the paper's central metric, made tangible).
3. **Graph Explorer:** amount-scaled edge widths where amounts exist, community hulls,
   neighbor expansion on click, the temporal scrubber (above), motif highlighting pass
   (explainer minimal subgraph at full opacity, context dimmed — partially exists).
4. **Case Detail:** animated DrawSVG motif schematic; red-flag cards restyled as evidence
   cards with per-source labels (data already rendered, presentation is JSON dumps today —
   design it: typed cards, not `<pre>` blocks).
5. **Model Lab:** visx PR curves, precision@k-vs-k with budget markers, transfer-matrix
   heatmap — **SVG/PNG export** (these double as paper figures; the `dataviz` skill and
   §5.3.5 spec them). Today it renders raw JSON — this view needs the most work.
6. **About page** (new, §5.3.6) — the ScrollTrigger story.

## 4. Hard constraints — unchanged, non-negotiable
- **Ethics caveat on every screen** (`SCREENING_CAVEAT` footer + dossier). No guilt
  language anywhere. UI copy presents calibrated scores as probabilities, never
  "percentages of certainty" (audit F30).
- **Read-only API, zero contract changes.** Frontend never writes.
- **CI green**: `npm run build` (tsc+vite) + vitest; add tests for new pure logic
  (motif→glyph maps, palette maps, scrubber timeline math).
- **Offline demo**: no network fonts/CDNs — everything self-hosted (`@fontsource` pattern).
- **Perf budget (§9.2)**: explorer interactive at ~5k nodes; one blurred layer per stack;
  animate only `transform`/`opacity`/`background`; cap canvas node counts by viewport area.
- **`prefers-reduced-motion`** honored everywhere (single static frame).

## 5. Keep-vs-build (V1's plumbing table still applies)
Everything in §8's "REUSABLE" table stays (build config, API layer, state, view logic,
Sigma integration, deploy). V1's shipped components (NetworkBackground, Glass, MotifGlyph,
CountUp, deep links incl. the 2026-07-18 cross-dataset fix) are the *starting point* —
brighten/extend, don't delete. The work is: token system rebuild (§3.1), glass upgrade
(§3.2), hover pass (§3.3), GSAP showpieces (§3.4), and the six §5.3 features (§3.5).
`gsap` and `@gsap/react` need installing; Cosmograph/visx per §3.5 (all MIT/free).

## 6. Suggested order (each step lands green)
1. Token system rebuild (multi-hue + brighter aurora + glass recipe) — everything inherits.
2. Hover pass across existing components (cheap, huge perceived-quality delta).
3. Case Detail dossier redesign + DrawSVG schematic (highest demo value per hour).
4. Alert Queue rows (badges, sparklines, animated precision readout).
5. Model Lab visx charts + export.
6. Overview hero mini-map; Explorer scrubber + hulls.
7. About page (ScrollTrigger) — last, it's narrative not operational.
8. Re-verify: build + vitest + `docker compose up` + five-view walk in both domains on
   REAL artifacts (master and laptop-C both have them; see PROGRESS.md Next action 2 for
   the recipe). Note: in-tool browser panes freeze rAF — verify via deep links + DOM
   reads, or a real visible browser.

## 7. Research sources (2026)
- Dark data-dense console patterns (Bloomberg-terminal vocabulary, near-navy bases,
  OKLCH tokens): [Colorlib dark dashboards](https://colorlib.com/wp/dark-admin-dashboard-templates/),
  [AdminLTE dark-mode roundup](https://adminlte.io/blog/dark-dashboard-templates/),
  [Muzli dashboard examples](https://muz.li/blog/best-dashboard-design-examples-inspirations-for-2026/)
- Glassmorphism recipes (blur 10–20px, alpha-gradient fills, neon edge strokes, perf
  rules): [Inverness guide](https://invernessdesignstudio.com/glassmorphism-what-it-is-and-how-to-use-it-in-2026),
  [Dark glassmorphism](https://medium.com/@developer_89726/dark-glassmorphism-the-aesthetic-that-will-define-ui-in-2026-93aa4153088f),
  [UXPilot best practices](https://uxpilot.ai/blogs/glassmorphism-ui),
  [Developer's CSS guide](https://nineproo.com/blog/css-glassmorphism-guide)
- Aurora backdrops (3-stop rule, glass pairing, contrast rules):
  [Superdesign aurora recipe](https://superdesign.dev/styles/aurora)
- GSAP techniques (DrawSVG+ScrollTrigger scrub, MotionPath flows, chart draw-on, all
  plugins free): [GSAP DrawSVG docs](https://gsap.com/docs/v3/Plugins/DrawSVGPlugin/),
  [GSAP scroll](https://gsap.com/scroll/),
  [Codrops scroll-driven SVG maps](https://tympanus.net/codrops/2026/05/21/creating-scroll-driven-svg-map-animations-with-gsap/),
  [GSAPify examples](https://gsapify.com/gsap-animations/)

## 8. History — V1 brief (2026-07-18, delivered, then rejected at re-review)

**V1 verbatim feedback (first rejection):**
> "The UI looks completely pathetic, it is a complete piece of useless frontend, the
> frontend should be very modernised with modern tech used, this is just a thing which I
> cannot present at all, I didn't liked it all. It needs to have live animated backgrounds,
> framer, objects, impressive color scheme, make UI related to the theme and topic of the
> project as well, it needs a complete overhaul, this is completely useless."

**V1 delivered** (laptop-C, merge `8a2fee7`): animated network-canvas background, Motion
pass (view transitions, sliding pills, count-up, stagger), glass primitives + gradient
borders, aurora washes + grain, per-domain accent ramps, nine motif SVG glyphs, self-hosted
variable fonts, designed loading/error/empty states — all constraints held.

**V1 REUSABLE table (still valid):**

| Area | Files | Keep because |
|---|---|---|
| Build config | `vite.config.ts`, `tsconfig*.json`, `package.json` (+lock) | Vite 7 + React 18 + TS + Tailwind v4 wired; `motion`, `sigma`, `graphology`, TanStack Query installed |
| Design tokens | `src/styles/tokens.css`, `src/index.css` | Token system exists — §3.1 rebuilds its *palette*, not its mechanism |
| API layer | `src/api/{client,hooks,types}.ts` | Typed TanStack-Query hooks over the live read-only API; contract frozen |
| Console state | `src/state/console.ts` | Zustand domain/dataset/budget/selection/view + `data-domain` recolor + deep-link hydration |
| Views (logic) | `src/views/*/` | All five fetch real data; presentation only is rejected |
| Graph explorer | `src/views/graph-explorer/GraphExplorer.tsx` | Sigma v3 integration works; restyle + extend |
| Deploy | `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml` | Demo path verified on real artifacts |

Why V1 failed re-review: see §2 — the shipped motion/glass/palette were all keyed to a
single accent family and tuned too subtle to register; the §5.3 flagship features that
create the "impressive" reaction were deferred as optional. V2 makes them required.

---

# V3 — the "unmistakably modern" pass (2026-07-22, laptop-D)

**Review #3 verdict (stakeholder, 2026-07-22): REJECTED — "not at the level our
project is… proper hover effects, glassmorphism, not a single color dominated
schema, proper tabs, an icon/logo for the chatbot… should look like it is built
using modern frontend tech (WebGL, GSAP, Framer)."**

## Diagnosis (V2 walked live on laptop-D against a dev store)

V2 executes its brief *correctly but too quietly* — the same failure class as
V1 at a higher baseline. Measured on the live page:

1. **The depth layer is a whisper.** The backdrop is an 80-node 2D-canvas mesh
   at 0.7 opacity over CSS radial washes at 14–22% mix — behind panels it reads
   as flat black. Nothing on screen says "GPU". The glass blur has almost no
   luminance to eat, so the glassmorphism the stakeholder keeps asking for is
   physically invisible (V2's own §3.2 diagnosis, still true).
2. **The nav does not read as tabs.** text-xs buttons with a subtle accent-dim
   pill; no icons, no per-view identity, small hit areas.
3. **The Copilot has no identity.** A text glyph (◈) in the header and dock —
   the stakeholder explicitly asks for a logo.
4. **Single-color dominance persists PERCEPTUALLY.** The five-hue inventory
   exists (tokens, KPI tiles, motif chips) but the accent still owns headings,
   nav, toggle, borders, and buttons — at rest a screen is ~80% one hue.
5. **Hover language exists but is sparse** (4 hover-lift surfaces on the
   overview) and there is no cursor-reactive surface anywhere.

## V3 requirements (all shipped in this pass)

1. **WebGL aurora field** (`components/bg/AuroraGL.tsx`): a real fragment-shader
   nebula — three fbm-driven hue blobs (domain-reactive: cyan/violet/magenta ⇄
   violet/magenta/cyan), animated at ~0.03 uv/s, bright enough to feed every
   glass blur. Raw WebGL2, zero dependencies. CSS-aurora fallback when WebGL is
   unavailable; `prefers-reduced-motion` renders a single static frame; paused
   when the tab hides. The 2D mesh stays above it (opacity 0.85, 110-node cap)
   so the subject-matter ambience survives.
2. **A real tab system**: segmented glass tab bar with per-view inline-SVG
   icons and a FIXED per-view hue identity (overview cyan, queue amber, explorer
   teal, case magenta, lab violet, about slate — coral stays flagged-exclusive
   per §5.2, so no tab may take it) — the active pill, underglow,
   icon ink, and the view H1 gradient all take the view hue (kills accent
   monoculture at rest); sliding Motion pill kept; hover lifts + label always
   visible.
3. **Copilot identity**: `CopilotMark` — an orbital-spark SVG logo (magenta⇄
   violet gradient ring, spark core, breathing glow when idle, presence dot) in
   the header button AND the dock header.
4. **Cursor-reactive glass**: every `Glass` panel gets a spotlight highlight
   that tracks the pointer (CSS vars set from one mousemove handler — no
   re-render), plus a `beam` variant: an animated conic border sweep
   (@property-driven) for hero panels.
5. **Multi-hue at rest, enforced**: domain toggle pills carry their domain
   ramps (cyan→teal / violet→magenta); header underline is a slow multi-hue
   conic sweep; footer caveat keeps its shield but gains the teal benign ink.
6. **Constraints unchanged**: ethics caveat on every screen, read-only API
   untouched, one blurred layer per stack, reduced-motion collapses every
   animation, `npm run build` + vitest green, no new runtime dependencies.

Cut order under pressure: beam sweep → mesh quality bump → toggle ramps. The
aurora, tabs, Copilot mark, and spotlight are the non-negotiable core.
