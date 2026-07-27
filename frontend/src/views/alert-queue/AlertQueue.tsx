import { useState } from "react";
import { motion } from "motion/react";
import { useAlerts, useExplanation, useMetrics, useSubgraph } from "../../api/hooks";
import type { AlertRow } from "../../api/types";
import { BudgetSlider } from "../../components/ui/BudgetSlider";
import { CountUp } from "../../components/ui/CountUp";
import { CopilotMark } from "../../components/copilot/CopilotMark";
import { FlagBadge, MotifChip, RiskChip } from "../../components/ui/Chips";
import { Glass } from "../../components/ui/Glass";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { describeTimeWindow, fmtTimeWindow, shortId } from "../../lib/format";
import { parseQueue } from "../../lib/metricsExtract";
import { UI_HUES } from "../../lib/palette";
import { bucketTimestamps, sparklinePoints } from "../../lib/sparkline";
import { useConsole } from "../../state/console";

// The core operational surface (§5.3 view 2). V2: rows carry motif chips,
// red-flag badges (from the alert's bundle when one exists), a temporal
// sparkline drawn from the REAL windowed-subgraph timestamps (fetched lazily
// on first hover — never synthesized), and hover-revealed actions; the
// header shows the run's MEASURED precision at the nearest published budget.
const BADGE_ROWS = 20; // bundle lookups only for the queue's head

/** Risk bands. "Low" is the answer to the question every evaluator asks —
 *  "show me one it did NOT flag" — which the queue could not do before, because
 *  it only ever rendered the top-k. Low-risk groups were always in the data
 *  (148 of Elliptic's 254 alerts score below 0.2); nothing surfaced them. */
const BANDS = [
  { id: "all", label: "All", test: () => true },
  { id: "high", label: "High risk", test: (s: number) => s >= 0.6 },
  { id: "medium", label: "Medium", test: (s: number) => s >= 0.2 && s < 0.6 },
  { id: "low", label: "Low / normal", test: (s: number) => s < 0.2 },
] as const;
type BandId = (typeof BANDS)[number]["id"];

export function AlertQueue() {
  const dataset = useConsole((s) => s.dataset);
  const budget = useConsole((s) => s.budget);
  const selected = useConsole((s) => s.selectedAlertId);
  const [band, setBand] = useState<BandId>("all");
  // Always fetch the whole queue (500 is the API's hard maximum) so the band
  // counts are true totals rather than "whatever fell inside the budget", and
  // switching bands needs no refetch. The BUDGET still governs what "All"
  // shows and what the precision readout reports — that number must match the
  // published protocol.
  const { data, isLoading, isError, error } = useAlerts(dataset, 500);
  const all = data?.alerts ?? [];
  const bandTest = BANDS.find((b) => b.id === band)!.test;
  const visible =
    band === "all" ? all.slice(0, budget) : all.filter((a) => bandTest(a.risk_score));
  // Counts on the buttons: on some datasets a band is genuinely EMPTY (every
  // Mendeley group scores high, because its case-control sample is ~42% cartel
  // by construction). Showing the count up front beats clicking into a blank
  // table and wondering whether the filter is broken.
  const bandCounts = Object.fromEntries(
    BANDS.map((b) => [
      b.id,
      b.id === "all" ? all.length : all.filter((a) => b.test(a.risk_score)).length,
    ]),
  ) as Record<BandId, number>;

  return (
    <Glass className="flex h-full flex-col overflow-hidden">
      <div className="flex flex-wrap items-center gap-4 border-b border-hairline/60 px-4 py-2.5">
        <h2 className="display text-sm font-semibold">Alert Queue</h2>
        <BudgetSlider />
        <PrecisionReadout dataset={dataset} budget={budget} />
        <div className="flex items-center gap-1">
          {BANDS.map((b) => (
            <button
              key={b.id}
              onClick={() => setBand(b.id)}
              className="chip-bloom rounded-md px-2 py-0.5 text-[11px] transition-colors"
              title={
                b.id === "low"
                  ? "groups the model scored as ordinary — the contrast case"
                  : undefined
              }
              disabled={bandCounts[b.id] === 0}
              style={{
                color: band === b.id ? "var(--text-0)" : "var(--text-2)",
                background:
                  band === b.id
                    ? "color-mix(in srgb, var(--accent) 18%, transparent)"
                    : "transparent",
                boxShadow:
                  band === b.id
                    ? "inset 0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent)"
                    : "inset 0 0 0 1px var(--hairline)",
              }}
            >
              {b.label}
              <span className="mono ml-1 opacity-60">{bandCounts[b.id]}</span>
            </button>
          ))}
        </div>
        {data && (
          <span className="mono ml-auto text-xs text-text-2">
            showing <span className="text-accent">{visible.length}</span>
            {band === "all"
              ? ` at budget ${budget} · ${all.length} in queue`
              : ` ${band}-risk of ${all.length} in queue`}
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {!dataset ? (
          <Empty title="No dataset selected" />
        ) : isLoading ? (
          <Loading label="Loading alert queue…" />
        ) : isError ? (
          <ErrorState
            message="No alert queue published for this dataset"
            detail={(error as Error)?.message}
          />
        ) : !data || visible.length === 0 ? (
          <Empty
            title={band === "all" ? "Queue is empty" : `No ${band}-risk groups in this queue`}
            hint={
              band === "all"
                ? "Run `collusiongraph score` for this dataset and point serving.json at the output."
                : "Every group this dataset produced sits in a different risk band — try All."
            }
          />
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead
              className="sticky top-0 z-10 text-left text-xs text-text-2"
              style={{
                background: "color-mix(in srgb, var(--bg-1) 90%, var(--accent))",
              }}
            >
              <tr className="border-b border-hairline">
                <th className="px-4 py-2 font-medium">#</th>
                <th
                  className="px-4 py-2 font-medium"
                  title="How strongly this group stands out, on a scale of 0 to 1. A reason to look, never proof."
                >
                  Risk
                </th>
                <th
                  className="px-4 py-2 font-medium"
                  title="Which of the nine known cheating shapes this group matches. We only put a name here when we can prove it, so 'none named' is common and honest."
                >
                  Pattern
                </th>
                <th
                  className="px-4 py-2 font-medium"
                  title="How many official warning signs (FATF for money, OECD for contracts) this group matched."
                >
                  Flags
                </th>
                <th className="px-4 py-2 font-medium" title="How many accounts or companies are in this group.">
                  Members
                </th>
                <th
                  className="px-4 py-2 font-medium"
                  title="A tiny chart of activity over time. Flat means it all happened in one window; a varied line means it was spread out."
                >
                  Activity
                </th>
                <th
                  className="px-4 py-2 font-medium"
                  title="When it happened. Some sources record calendar years; the Bitcoin data records numbered steps in order instead of dates, shown as 'step 35'."
                >
                  When
                </th>
                <th className="px-4 py-2 font-medium">Alert ID</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((a, i) => (
                <Row
                  key={a.alert_id}
                  alert={a}
                  index={i}
                  dataset={dataset}
                  active={a.alert_id === selected}
                  withBadge={i < BADGE_ROWS}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Glass>
  );
}

function Row({
  alert: a,
  index,
  dataset,
  active,
  withBadge,
}: {
  alert: AlertRow;
  index: number;
  dataset: string;
  active: boolean;
  withBadge: boolean;
}) {
  const selectAlert = useConsole((s) => s.selectAlert);
  const setView = useConsole((s) => s.setView);
  const askCopilotAbout = useConsole((s) => s.askCopilotAbout);

  // lazy, cached; 404 (no bundle for this alert) is a normal outcome
  const bundle = useExplanation(dataset, a.alert_id, withBadge);
  const flags = Array.isArray(bundle.data?.bundle?.red_flags)
    ? (bundle.data.bundle.red_flags as unknown[]).length
    : 0;

  const open = (view: "explorer" | "case") => {
    selectAlert(a.alert_id);
    setView(view);
  };

  return (
    <motion.tr
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 14) * 0.022, duration: 0.25 }}
      onClick={() => open("explorer")}
      className="hover-row group cursor-pointer border-b border-hairline/40"
      style={
        active
          ? {
              background: "var(--accent-dim)",
              boxShadow: "inset 2px 0 0 var(--accent)",
            }
          : undefined
      }
    >
      <td className="mono px-4 py-1.5 text-text-2">{a.rank}</td>
      <td className="px-4 py-1.5">
        <RiskChip score={a.risk_score} />
      </td>
      <td className="px-4 py-1.5">
        <MotifChip motif={a.motif_type} explained={a.explained !== false} />
      </td>
      <td className="px-4 py-1.5">
        <FlagBadge count={flags} />
      </td>
      <td className="mono px-4 py-1.5 text-text-1">{a.n_members}</td>
      <td className="px-2 py-1.5">
        <ActivitySparkline dataset={dataset} alertId={a.alert_id} />
      </td>
      <td
        className="mono px-4 py-1.5 text-text-1"
        title={describeTimeWindow(a.time_window_start, a.time_window_end)}
      >
        {fmtTimeWindow(a.time_window_start, a.time_window_end)}
      </td>
      <td className="mono relative px-4 py-1.5 text-text-2">
        <span className="transition-opacity group-hover:opacity-0">
          {shortId(a.alert_id, 22)}
        </span>
        {/* hover-revealed actions (V2 §3.3) */}
        <span className="absolute inset-y-0 right-2 flex translate-x-2 items-center gap-1.5 opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100">
          <button
            onClick={(e) => {
              e.stopPropagation();
              open("explorer");
            }}
            className="btn-sheen rounded px-2 py-0.5 text-xs"
            style={{ color: "var(--accent)", background: "var(--accent-dim)" }}
          >
            subgraph
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              open("case");
            }}
            className="btn-sheen rounded px-2 py-0.5 text-xs"
            style={{
              color: UI_HUES.amber,
              background: "color-mix(in srgb, var(--hue-amber) 14%, transparent)",
            }}
          >
            dossier
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              selectAlert(a.alert_id);
              askCopilotAbout(a.alert_id);
            }}
            title="ask the Copilot about this alert"
            className="btn-sheen rounded px-2 py-0.5 text-xs"
            style={{
              color: UI_HUES.magenta,
              background: "color-mix(in srgb, var(--hue-magenta) 14%, transparent)",
            }}
          >
            <CopilotMark size={13} />
          </button>
        </span>
      </td>
    </motion.tr>
  );
}

// Draws the alert's REAL edge-timestamp histogram as a self-drawing polyline.
// Loads eagerly (cached + deduped by TanStack Query) so the Activity column is
// populated for every row — not blank until hovered. A single-time-window
// subgraph (e.g. Elliptic tx-graphs all in one step) draws a flat baseline
// rather than a gap, so the column reads consistently.
function ActivitySparkline({
  dataset,
  alertId,
}: {
  dataset: string;
  alertId: string;
}) {
  const { data, isLoading } = useSubgraph(dataset, alertId, 1, true);

  if (isLoading || !data)
    return (
      <span
        className="block h-4 w-16 animate-pulse rounded bg-bg-2/60"
        aria-hidden
      />
    );
  const counts = bucketTimestamps(data.edges.map((e) => e.timestamp), 14);
  // no timestamps at all → a flat baseline (still a consistent mark)
  const flat = counts.every((c) => c === 0);
  const points = flat
    ? "0,15 64,15"
    : sparklinePoints(counts, 64, 16);
  return (
    <svg
      viewBox="0 0 64 16"
      width="64"
      height="16"
      aria-label="temporal activity sparkline (windowed subgraph)"
    >
      <polyline
        points={points}
        fill="none"
        stroke={flat ? "var(--text-2)" : "var(--accent)"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={100}
        style={{
          strokeDasharray: 100,
          strokeDashoffset: 0,
          animation: "spark-draw 0.5s ease-out",
        }}
      />
      <style>{`@keyframes spark-draw { from { stroke-dashoffset: 100; } to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { svg polyline { animation: none !important; } }`}</style>
    </svg>
  );
}

// The paper's central metric, made tangible (§5.3 view 2): shows the run's
// MEASURED alert-level precision at the nearest published budget ≤ k (never
// interpolated), counting up when the crossed breakpoint changes.
function PrecisionReadout({
  dataset,
  budget,
}: {
  dataset: string | undefined;
  budget: number;
}) {
  const { data } = useMetrics(dataset);
  if (!data) return null;

  let points: ReturnType<typeof parseQueue> = [];
  for (const run of data.runs) {
    const m = run.metrics as Record<string, Record<string, unknown>>;
    points = parseQueue(m.alert_level);
    if (points.length > 0) break;
  }
  if (points.length === 0) return null;
  const at = [...points].reverse().find((p) => p.k <= budget) ?? points[0];

  return (
    <span
      className="mono flex items-center gap-1.5 text-xs text-text-1"
      title="out of the cases you review, how many turned out to be real. Measured, not promised"
    >
      <span className="text-text-2">measured P@{at.k}</span>
      <span className="text-sm" style={{ color: UI_HUES.amber }}>
        <CountUp
          key={at.k}
          value={at.value}
          format={(n) => n.toFixed(2)}
          duration={0.5}
        />
      </span>
    </span>
  );
}
