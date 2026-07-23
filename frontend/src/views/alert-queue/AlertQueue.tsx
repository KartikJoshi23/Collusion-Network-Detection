import { motion } from "motion/react";
import { useAlerts, useExplanation, useMetrics, useSubgraph } from "../../api/hooks";
import type { AlertRow } from "../../api/types";
import { BudgetSlider } from "../../components/ui/BudgetSlider";
import { CountUp } from "../../components/ui/CountUp";
import { CopilotMark } from "../../components/copilot/CopilotMark";
import { FlagBadge, MotifChip, RiskChip } from "../../components/ui/Chips";
import { Glass } from "../../components/ui/Glass";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { fmtTimeWindow, shortId } from "../../lib/format";
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

export function AlertQueue() {
  const dataset = useConsole((s) => s.dataset);
  const budget = useConsole((s) => s.budget);
  const selected = useConsole((s) => s.selectedAlertId);
  const { data, isLoading, isError, error } = useAlerts(dataset, budget);

  return (
    <Glass className="flex h-full flex-col overflow-hidden">
      <div className="flex flex-wrap items-center gap-4 border-b border-hairline/60 px-4 py-2.5">
        <h2 className="display text-sm font-semibold">Alert Queue</h2>
        <BudgetSlider />
        <PrecisionReadout dataset={dataset} budget={budget} />
        {data && (
          <span className="mono ml-auto text-xs text-text-2">
            showing <span className="text-accent">{data.k_effective}</span> of
            top {budget}
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
        ) : !data || data.alerts.length === 0 ? (
          <Empty
            title="Queue is empty"
            hint="Run `collusiongraph score` for this dataset and point serving.json at the output."
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
                <th className="px-4 py-2 font-medium">Risk</th>
                <th className="px-4 py-2 font-medium">Motif</th>
                <th className="px-4 py-2 font-medium">Flags</th>
                <th className="px-4 py-2 font-medium">Members</th>
                <th className="px-4 py-2 font-medium">Activity</th>
                <th className="px-4 py-2 font-medium">Time window</th>
                <th className="px-4 py-2 font-medium">Alert ID</th>
              </tr>
            </thead>
            <tbody>
              {data.alerts.map((a, i) => (
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
        <MotifChip motif={a.motif_type} />
      </td>
      <td className="px-4 py-1.5">
        <FlagBadge count={flags} />
      </td>
      <td className="mono px-4 py-1.5 text-text-1">{a.n_members}</td>
      <td className="px-2 py-1.5">
        <ActivitySparkline dataset={dataset} alertId={a.alert_id} />
      </td>
      <td className="mono px-4 py-1.5 text-text-1">
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
      title="measured alert-level precision at the nearest published budget — a calibrated screening rate, not certainty"
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
