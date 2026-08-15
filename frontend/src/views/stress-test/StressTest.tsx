// Stress Test view (§7 step 30, §5.3): the honest answer to "how do you
// evaluate with no answer key?" — plant fake cartels of KNOWN shapes into the
// real 163,327-firm Georgian contract network, then measure how many the
// detector claws back. Every number here is COPIED from the stored injection
// artifact (real 5-run study), never invented; the "plant & detect" motion is
// a reveal of measured results, and the exact reproduce command is shown so it
// can be re-run live. Plain language throughout (no jargon in visible strings).
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { useStressTest } from "../../api/hooks";
import { SCREENING_CAVEAT } from "../../api/types";
import { CopilotMark } from "../../components/copilot/CopilotMark";
import { CountUp } from "../../components/ui/CountUp";
import { Glass } from "../../components/ui/Glass";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { UI_HUES } from "../../lib/palette";
import { parseStress, type StressModel } from "../../lib/stressExtract";
import { useConsole } from "../../state/console";

const HUE = "#a3e635"; // the Stress Test identity hue (lime — proof/experiment)

// Friendly, jargon-free names for each planted cartel shape.
const SHAPE: Record<
  string,
  { name: string; plain: string; hint: "ring" | "star" | "split" | "rotate" | "cover" }
> = {
  coordinated_cluster: {
    name: "Bid-together ring",
    plain: "A block of firms that all pile onto the same contracts together.",
    hint: "ring",
  },
  common_control: {
    name: "Hidden common owner",
    plain: "Separate-looking firms secretly run by one owner.",
    hint: "star",
  },
  partition: {
    name: "Market carve-up",
    plain: "Firms agree to split the territory and never step on each other.",
    hint: "split",
  },
  rotation: {
    name: "Take-turns",
    plain: "Firms quietly take turns winning, one after another.",
    hint: "rotate",
  },
  cover_bid: {
    name: "Cover bidding",
    plain: "Losers file deliberately high bids to make the winner look fair.",
    hint: "cover",
  },
};

function verdict(recall: number): { label: string; hue: string } {
  if (recall >= 0.6) return { label: "CAUGHT", hue: UI_HUES.teal };
  if (recall >= 0.25) return { label: "PARTLY CAUGHT", hue: UI_HUES.amber };
  return { label: "ESCAPES", hue: "var(--text-2)" };
}

type Phase = "idle" | "planting" | "detecting" | "done";

export function StressTest() {
  const { data, isLoading, isError, error } = useStressTest();

  if (isLoading) return <Loading label="Loading the stress test…" />;
  if (isError) {
    // A 404 here is the honest thin-machine state, not a failure.
    const notHere = (error as { status?: number })?.status === 404;
    if (notHere)
      return (
        <Empty
          title="No stress test on this machine"
          hint="Run the injection study first: uv run collusiongraph train -c configs/experiment/injection_recovery_ocds_georgia_multiseed.yaml"
        />
      );
    return <ErrorState message="Could not load the stress test." />;
  }

  const study = data && Object.values(data.studies)[0];
  const model = study ? parseStress(study.payload) : null;
  if (!study || !model) return <Empty title="No stress test published" />;

  return (
    <div className="h-full min-h-0 overflow-auto p-2" style={{ ["--panel-hue" as string]: HUE }}>
      <div className="mb-4 px-2 pt-3">
        <div className="text-xs uppercase tracking-[0.2em] text-text-2">
          the honest test · no answer key
        </div>
        <h1 className="display mt-1 text-3xl font-semibold leading-tight">
          Stress <span className="text-grad">Test</span>
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-text-1">
          Our biggest network — {study.title.split("—")[0].trim()} — has{" "}
          <span style={{ color: HUE }}>no answer key at all</span>. So we hide answers we
          already know: we <b>plant fake cartels of known shapes</b> into the real network and
          measure how many come back. It's the only fair way to score a detector when reality
          gives you nothing to check against.
        </p>
      </div>

      <PlantAndDetect model={model} reproduce={study.reproduce} />

      <AmlBench />

      <div className="mt-4 flex items-center justify-center gap-2 px-4 pb-2 text-center text-xs text-text-2">
        {SCREENING_CAVEAT}
      </div>
    </div>
  );
}

function PlantAndDetect({ model, reproduce }: { model: StressModel; reproduce: string }) {
  const budgets = model.budgets;
  const [budget, setBudget] = useState(budgets[budgets.length - 1]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [copied, setCopied] = useState(false);
  const askCopilot = useConsole((s) => s.askCopilot);

  // Drive the idle → planting → detecting → done reveal.
  useEffect(() => {
    if (phase === "planting") {
      const t = setTimeout(() => setPhase("detecting"), 1000);
      return () => clearTimeout(t);
    }
    if (phase === "detecting") {
      const t = setTimeout(() => setPhase("done"), 1300);
      return () => clearTimeout(t);
    }
  }, [phase]);

  const pct = (r: number) => Math.round(r * 100);
  const scanning = phase === "planting" || phase === "detecting";

  return (
    <Glass beam neon hue={HUE} className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-hairline/60 px-4 py-3">
        <div>
          <div className="text-sm font-medium">The playground</div>
          <div className="mono text-[11px] text-text-2">
            <CountUp value={model.population} /> firms ·{" "}
            {model.nInstances ?? "—"} fake cartels planted · {model.nMembers ?? "—"} firms ·{" "}
            {model.nSeeds > 1 ? `${model.nSeeds} runs` : "1 run"}
          </div>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1">
            <span className="mr-1 text-[11px] text-text-2">review budget</span>
            {budgets.map((b) => {
              const on = b === budget;
              return (
                <button
                  key={b}
                  onClick={() => setBudget(b)}
                  className="rounded-md px-2 py-1 text-[11px] transition-colors"
                  style={{
                    color: on ? "#0a0e17" : "var(--text-1)",
                    background: on ? HUE : "var(--glass-fill-lo)",
                    boxShadow: on ? "none" : "inset 0 0 0 1px var(--hairline)",
                  }}
                  title={`review the top ${b.toLocaleString()} firms (${(
                    (b / model.population) *
                    100
                  ).toFixed(1)}% of the network)`}
                >
                  top {b.toLocaleString()}
                </button>
              );
            })}
          </div>
          <button
            onClick={() => setPhase(phase === "idle" || phase === "done" ? "planting" : phase)}
            disabled={scanning}
            className="btn-sheen rounded-lg px-3.5 py-1.5 text-[13px] font-semibold"
            style={{ color: "#0a0e17", background: HUE, opacity: scanning ? 0.6 : 1 }}
          >
            {phase === "idle"
              ? "▶ Plant & Detect"
              : phase === "planting"
                ? "Planting…"
                : phase === "detecting"
                  ? `Scanning ${model.population.toLocaleString()} firms…`
                  : "↻ Run again"}
          </button>
        </div>
      </div>

      {/* scanning sweep */}
      <div className="relative">
        <AnimatePresence>
          {scanning && (
            <motion.div
              initial={{ x: "-30%", opacity: 0 }}
              animate={{ x: "130%", opacity: 0.8 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.1, ease: "linear", repeat: Infinity }}
              className="pointer-events-none absolute inset-y-0 left-0 z-10 w-1/4"
              style={{
                background: `linear-gradient(90deg, transparent, color-mix(in srgb, ${HUE} 22%, transparent), transparent)`,
              }}
              aria-hidden
            />
          )}
        </AnimatePresence>

        <div className="grid gap-px bg-hairline/40 sm:grid-cols-2 xl:grid-cols-3">
          {model.shapes.map((shape, i) => {
            const meta = SHAPE[shape.motif] ?? {
              name: shape.motif,
              plain: "",
              hint: "ring" as const,
            };
            const rec = shape.byBudget[budget];
            const recall = rec?.recall ?? 0;
            const v = verdict(recall);
            const revealed = phase === "done";
            return (
              <div key={shape.motif} className="bg-bg-1/40 p-3.5">
                <div className="flex items-center gap-2.5">
                  <ShapeHint kind={meta.hint} planted={phase !== "idle"} />
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium">{meta.name}</div>
                    <div className="mono text-[10px] text-text-2">
                      {shape.nMembers} firms planted
                    </div>
                  </div>
                  <AnimatePresence>
                    {revealed && (
                      <motion.span
                        initial={{ scale: 0.6, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 0.15 + i * 0.08, type: "spring", stiffness: 500 }}
                        className="mono ml-auto rounded px-1.5 py-0.5 text-[10px] font-semibold"
                        style={{
                          color: v.hue,
                          background: `color-mix(in srgb, ${v.hue} 14%, transparent)`,
                        }}
                      >
                        {v.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </div>

                <p className="mt-2 text-[11px] leading-snug text-text-1">{meta.plain}</p>

                {/* recovery bar */}
                <div className="mt-2.5">
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="text-[10px] text-text-2">recovered</span>
                    <span className="mono text-[11px]" style={{ color: revealed ? v.hue : "var(--text-2)" }}>
                      {revealed ? `${pct(recall)}%` : "—"}
                      {revealed && rec?.std ? (
                        <span className="text-text-2"> ± {pct(rec.std)}</span>
                      ) : null}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-bg-3">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: v.hue }}
                      initial={{ width: 0 }}
                      animate={{ width: revealed ? `${pct(recall)}%` : 0 }}
                      transition={{ delay: revealed ? 0.15 + i * 0.08 : 0, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* honest takeaway + reproduce */}
      <div className="border-t border-hairline/60 p-4">
        <div
          className="rounded-lg p-3 text-[12px] leading-relaxed text-text-1"
          style={{ background: `color-mix(in srgb, ${HUE} 7%, transparent)` }}
        >
          <b style={{ color: HUE }}>What this proves.</b> Reviewing barely 1% of the network, the
          detector reliably catches cartels whose firms <b>physically bid together</b> — and is
          honestly blind to cartels that merely <b>take turns</b> and never appear side by side.
          Knowing exactly which it will and won't catch is far more useful than one average
          score. This is the case with no answer key, so the tree model and every method that
          needs answers cannot even take part — only the learn-what's-normal models can.
        </div>

        <div className="mt-2.5 flex items-center gap-2">
          <button
            onClick={() =>
              askCopilot(
                "In the stress test, which planted cartel shapes does the detector catch and which escape, and roughly what fraction of the bid-together ring do we recover?",
              )
            }
            className="btn-sheen inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-medium"
            style={{
              color: UI_HUES.magenta,
              background: `color-mix(in srgb, ${UI_HUES.magenta} 12%, transparent)`,
              boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${UI_HUES.magenta} 30%, transparent)`,
            }}
          >
            <CopilotMark size={14} /> Ask the Copilot about the stress test
          </button>
          <span className="text-[10px] text-text-2">
            it reads these same numbers and answers, grounded, in the dock
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-text-2">Not a canned result — run it live:</span>
          <code className="mono flex-1 truncate rounded bg-bg-0/60 px-2 py-1.5 text-[11px] text-text-1">
            {reproduce}
          </code>
          <button
            onClick={() => {
              void navigator.clipboard?.writeText(reproduce);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
            className="btn-sheen rounded px-2 py-1 text-[11px]"
            style={{ boxShadow: "inset 0 0 0 1px var(--hairline)" }}
          >
            {copied ? "copied ✓" : "copy"}
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-text-2">
          The exact command plants fresh random cartels into the real network and reproduces
          these numbers in a few minutes — nothing here is hard-coded.
        </p>
      </div>
    </Glass>
  );
}

// A tiny shape hint per cartel type — dots that "plant in" when armed.
function ShapeHint({
  kind,
  planted,
}: {
  kind: "ring" | "star" | "split" | "rotate" | "cover";
  planted: boolean;
}) {
  const dots: [number, number][] =
    kind === "ring"
      ? [
          [10, 8],
          [22, 8],
          [26, 18],
          [16, 24],
          [6, 18],
        ]
      : kind === "star"
        ? [
            [16, 16],
            [16, 5],
            [27, 16],
            [16, 27],
            [5, 16],
          ]
        : kind === "split"
          ? [
              [8, 9],
              [8, 22],
              [24, 9],
              [24, 22],
            ]
          : kind === "rotate"
            ? [
                [16, 6],
                [26, 16],
                [16, 26],
                [6, 16],
              ]
            : [
                [16, 7],
                [9, 24],
                [16, 24],
                [23, 24],
              ];
  const edges: [number, number][] =
    kind === "star"
      ? [
          [0, 1],
          [0, 2],
          [0, 3],
          [0, 4],
        ]
      : kind === "ring" || kind === "rotate"
        ? dots.map((_, i) => [i, (i + 1) % dots.length] as [number, number])
        : kind === "cover"
          ? [
              [0, 1],
              [0, 2],
              [0, 3],
            ]
          : [];
  return (
    <svg viewBox="0 0 32 32" width="34" height="34" className="shrink-0" aria-hidden>
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={dots[a][0]}
          y1={dots[a][1]}
          x2={dots[b][0]}
          y2={dots[b][1]}
          stroke={HUE}
          strokeWidth="1"
          opacity={planted ? 0.5 : 0.15}
          style={{ transition: "opacity 0.5s ease" }}
        />
      ))}
      {dots.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r="2.4"
          fill={HUE}
          opacity={planted ? 0.95 : 0.25}
          style={{ transition: `opacity 0.4s ease ${i * 0.06}s` }}
        />
      ))}
    </svg>
  );
}

// The known-answer bench — reframes why AMLworld is kept even though its
// per-account score is poor. Static facts (measured, from the datasheet).
function AmlBench() {
  const AML = UI_HUES.cyan;
  return (
    <Glass hue={AML} className="mt-4 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-hairline/60 px-4 py-3">
        <div className="text-sm font-medium">The known-answer bench — AMLworld</div>
        <span className="mono ml-auto text-[11px] text-text-2">not shown on the queue — on purpose</span>
      </div>
      <div className="grid gap-4 p-4 md:grid-cols-[1.3fr_1fr]">
        <div className="text-[12px] leading-relaxed text-text-1">
          <p>
            The stress test above only works if the planting method itself is sound. AMLworld is
            where we prove that: it's made-up bank payments where{" "}
            <b style={{ color: AML }}>every answer is known perfectly</b> — so we can check the
            whole machine against the truth before trusting it on data that has no truth.
          </p>
          <p className="mt-2">
            <b>So why not put it on the dashboard?</b> Honestly — because our per-account model
            scores <b>below blind guessing</b> on it, and showing that queue would mislead. Its
            job was never to top a leaderboard. Its job is to be the reference standard: the
            known answers, all eight real laundering shapes to copy, and real money amounts (our
            other money dataset is anonymised and has none). Reporting its weak score openly is a
            credibility feature, not a gap.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            ["515,088", "accounts"],
            ["5,078,345", "payments, real amounts"],
            ["6,357", "known criminal — perfect key"],
            ["8", "real laundering shapes"],
          ].map(([n, label]) => (
            <div key={label} className="glass rounded-lg p-2.5" style={{ ["--panel-hue" as string]: AML }}>
              <div className="mono text-lg" style={{ color: AML }}>
                {n}
              </div>
              <div className="text-[10px] leading-tight text-text-2">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </Glass>
  );
}
