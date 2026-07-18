// About / Methodology (§5.3 view 6) — the scroll-driven demo-day opener:
// the two-ledgers-one-structure thesis, the motif table drawing itself in
// (GSAP ScrollTrigger + DrawSVG, scrubbed to scroll), the pipeline, and the
// scope boundary. Static content under prefers-reduced-motion.
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef } from "react";
import { SCREENING_CAVEAT } from "../../api/types";
import { Glass } from "../../components/ui/Glass";
import { MotifGlyph } from "../../components/ui/MotifGlyph";
import { MOTIF_LABEL, MOTIF_TYPES } from "../../lib/motifs";
import { MOTIF_HUE, UI_HUES } from "../../lib/palette";

gsap.registerPlugin(ScrollTrigger, DrawSVGPlugin, useGSAP);

const FINANCIAL = ["cycle", "fan_in", "fan_out", "pass_through"] as const;
const PROCUREMENT = ["rotation", "cover_bid", "partition", "clique"] as const;

const PIPELINE = [
  ["Ingest", "public ledgers → one graph IR", UI_HUES.cyan],
  ["Learn", "GNNs + calibrated ensemble score entities", UI_HUES.violet],
  ["Rank", "community roll-up → budgeted alert queue", UI_HUES.amber],
  ["Explain", "motif match + red-flag citations per alert", UI_HUES.magenta],
] as const;

export function About() {
  const scrollRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const scroller = scrollRef.current;
      if (!scroller || matchMedia("(prefers-reduced-motion: reduce)").matches)
        return;

      gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((el) => {
        gsap.from(el, {
          opacity: 0,
          y: 36,
          duration: 0.7,
          ease: "power2.out",
          scrollTrigger: { scroller, trigger: el, start: "top 88%" },
        });
      });

      // motif glyphs draw themselves as the table scrolls in (scrubbed)
      gsap.utils.toArray<HTMLElement>("[data-motif-card]").forEach((card, i) => {
        const paths = card.querySelectorAll("path");
        if (paths.length)
          gsap.from(paths, {
            drawSVG: "0%",
            ease: "none",
            scrollTrigger: {
              scroller,
              trigger: card,
              start: "top 92%",
              end: "top 55%",
              scrub: true,
            },
            stagger: 0.08,
            delay: i * 0.01,
          });
      });
    },
    { scope: scrollRef },
  );

  return (
    <div ref={scrollRef} className="h-full min-h-0 overflow-auto">
      {/* hero */}
      <section className="mx-auto max-w-3xl px-6 pb-10 pt-16 text-center">
        <div className="text-xs uppercase tracking-[0.25em] text-text-2">
          methodology
        </div>
        <h1 className="display mt-3 text-4xl font-semibold leading-tight sm:text-5xl">
          Two ledgers.
          <br />
          One <span className="text-grad">structure</span>.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-text-1">
          Money laundering rings and bid-rigging cartels live in different
          worlds — transaction ledgers and procurement records — but they leave
          the <em>same kind</em> of fingerprint: coordination has geometry.
          CollusionGraph screens both domains with one graph-learning stack.
        </p>
      </section>

      {/* motif table */}
      <section className="mx-auto max-w-4xl px-6 py-8">
        <h2 data-reveal className="display mb-1 text-xl font-semibold">
          The motif table
        </h2>
        <p data-reveal className="mb-5 max-w-2xl text-xs text-text-1">
          Nine coordination patterns, curated from FATF money-laundering
          indicators and the OECD bid-rigging checklist. The matcher recovers
          all nine injected families at 100% recall on fixtures — and every
          match cites its indicator source in the dossier.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...FINANCIAL, "common_control", ...PROCUREMENT].map((m) => (
            <div key={m} data-motif-card>
              <Glass
                lift
                neon
                hue={MOTIF_HUE[m]}
                className="flex flex-col items-center gap-2 p-4"
              >
                <span style={{ color: MOTIF_HUE[m] }}>
                  <MotifGlyph motif={m} size={44} />
                </span>
                <span
                  className="text-xs font-medium"
                  style={{ color: MOTIF_HUE[m] }}
                >
                  {MOTIF_LABEL[m as (typeof MOTIF_TYPES)[number]]}
                </span>
                <span className="text-center text-[10px] leading-snug text-text-2">
                  {FINANCIAL.includes(m as never)
                    ? "financial flow pattern"
                    : PROCUREMENT.includes(m as never)
                      ? "procurement pattern"
                      : "shared ownership pattern"}
                </span>
              </Glass>
            </div>
          ))}
        </div>
      </section>

      {/* pipeline */}
      <section className="mx-auto max-w-3xl px-6 py-8">
        <h2 data-reveal className="display mb-5 text-xl font-semibold">
          From raw ledger to explained alert
        </h2>
        <div className="grid gap-3">
          {PIPELINE.map(([title, text, hue], i) => (
            <div key={title} data-reveal>
              <Glass lift hue={hue} className="flex items-center gap-4 p-4">
                <span
                  className="mono grid h-9 w-9 shrink-0 place-items-center rounded-lg text-sm font-semibold"
                  style={{
                    color: hue,
                    background: `color-mix(in srgb, ${hue} 14%, transparent)`,
                    boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${hue} 32%, transparent)`,
                  }}
                >
                  {i + 1}
                </span>
                <div>
                  <div className="text-sm font-medium" style={{ color: hue }}>
                    {title}
                  </div>
                  <div className="text-xs text-text-1">{text}</div>
                </div>
              </Glass>
            </div>
          ))}
        </div>
        <p data-reveal className="mt-4 text-xs leading-relaxed text-text-2">
          Every number the console shows is leakage-safe by construction:
          strict-inductive temporal splits, as-of features, group-isolated
          folds — and every headline reads against its prevalence baseline.
        </p>
      </section>

      {/* scope boundary */}
      <section className="mx-auto max-w-3xl px-6 pb-16 pt-6">
        <div data-reveal>
          <Glass strong neon hue={UI_HUES.coral} className="p-6 text-center">
            <div
              className="text-xs font-medium uppercase tracking-[0.2em]"
              style={{ color: "var(--risk-high)" }}
            >
              scope boundary
            </div>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-text-0">
              CollusionGraph produces {SCREENING_CAVEAT}. Alerts are calibrated
              screening probabilities for human investigators — inputs to due
              process, never substitutes for it.
            </p>
          </Glass>
        </div>
      </section>
    </div>
  );
}
