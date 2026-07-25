import { motion } from "motion/react";
import { useMetrics } from "../../api/hooks";
import { ChartCard } from "../../components/charts/ChartCard";
import { AtKChart, StepBarChart } from "../../components/charts/Charts";
import { Glass } from "../../components/ui/Glass";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import {
  parseAtK,
  parsePerTimeStep,
  parseQueue,
} from "../../lib/metricsExtract";
import { CHART_SERIES, UI_HUES } from "../../lib/palette";
import { useConsole } from "../../state/console";
import { RigorSection } from "./RigorSection";

// The figure factory (§5.3 view 5). V2: published runs render as REAL charts
// (per-time-step AUC-PR bars — the temporal-shift figure; measured
// precision@k lines with the live budget marker; queue precision) with
// SVG/PNG export, plus the scalar tiles and the full collapsible tree so
// every number a run published stays inspectable.

/** Headline AUC-PR read against its own prevalence baseline, plus one compact
 *  per-budget table. Replaces the old flat dump of every numeric key (see the
 *  call site) — the numbers are identical, the ordering is now meaningful and
 *  a presenter can point at one row. */
function HeadlineBlock({ nodeLevel }: { nodeLevel: Record<string, unknown> }) {
  const num = (k: string) =>
    typeof nodeLevel[k] === "number" ? (nodeLevel[k] as number) : undefined;
  const auc = num("auc_pr");
  const prev = num("prevalence_baseline");
  const nConf = num("n_confirmed");
  const budgets = [
    ...new Set(
      Object.keys(nodeLevel)
        .map((k) => /^precision@(\d+)$/.exec(k)?.[1])
        .filter((x): x is string => Boolean(x)),
    ),
  ].sort((a, b) => Number(a) - Number(b));

  return (
    <div className="grid gap-3 px-2 lg:grid-cols-[minmax(0,20rem)_1fr]">
      <div
        className="hover-lift rounded-md px-3 py-2.5"
        style={{
          background: "var(--bg-2)",
          boxShadow: "inset 0 0 0 1px var(--hairline)",
        }}
      >
        <div className="text-[10px] uppercase tracking-wide text-text-2">
          AUC-PR
        </div>
        <div className="mono text-2xl" style={{ color: UI_HUES.cyan }}>
          {auc !== undefined ? auc.toFixed(4) : "—"}
        </div>
        {prev !== undefined && (
          <div className="mt-0.5 text-[11px] leading-snug text-text-2">
            blind guessing scores{" "}
            <span className="mono" style={{ color: "var(--text-1)" }}>
              {prev.toFixed(4)}
            </span>
            {auc !== undefined && prev > 0 && (
              <>
                {" "}
                → <span style={{ color: UI_HUES.teal }}>
                  {(auc / prev).toFixed(1)}× better than guessing
                </span>
              </>
            )}
          </div>
        )}
        {nConf !== undefined && (
          <div className="mt-1 text-[11px] text-text-2">
            over{" "}
            <span className="mono" style={{ color: "var(--text-1)" }}>
              {nConf.toLocaleString()}
            </span>{" "}
            confirmed-label nodes
          </div>
        )}
      </div>

      {budgets.length > 0 && (
        <div
          className="overflow-x-auto rounded-md"
          style={{
            background: "var(--bg-2)",
            boxShadow: "inset 0 0 0 1px var(--hairline)",
          }}
        >
          <table className="w-full text-xs">
            <thead>
              <tr className="text-text-2">
                <th className="px-3 py-1.5 text-left font-normal">
                  review budget
                </th>
                <th className="px-3 py-1.5 text-right font-normal">
                  precision
                </th>
                <th className="px-3 py-1.5 text-right font-normal">recall</th>
                <th className="px-3 py-1.5 text-right font-normal">
                  false-positive rate
                </th>
              </tr>
            </thead>
            <tbody>
              {budgets.map((k) => (
                <tr key={k} className="hover-row">
                  <td className="mono px-3 py-1.5 text-text-1">top {k}</td>
                  <td
                    className="mono px-3 py-1.5 text-right"
                    style={{ color: UI_HUES.amber }}
                  >
                    {num(`precision@${k}`)?.toFixed(3) ?? "—"}
                  </td>
                  <td
                    className="mono px-3 py-1.5 text-right"
                    style={{ color: UI_HUES.violet }}
                  >
                    {num(`recall@${k}`)?.toFixed(3) ?? "—"}
                  </td>
                  <td className="mono px-3 py-1.5 text-right text-text-1">
                    {num(`fpr@${k}`)?.toFixed(4) ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
export function ModelLab() {
  const dataset = useConsole((s) => s.dataset);
  const budget = useConsole((s) => s.budget);
  const { data, isLoading, isError, error } = useMetrics(dataset);

  if (!dataset) return <Empty title="No dataset selected" />;
  if (isLoading) return <Loading label="Loading metrics…" />;
  if (isError)
    return (
      <ErrorState
        message="No metrics published for this dataset"
        detail={(error as Error)?.message}
      />
    );
  if (!data) return null;

  return (
    <div className="h-full min-h-0 overflow-auto p-2">
      <div className="mb-3 px-2 pt-2">
        <h2 className="display text-lg font-semibold">
          Model <span className="text-grad">Lab</span>
        </h2>
        <p className="text-xs text-text-2">
          Published metrics for <span className="mono">{dataset}</span> — every
          chart exports as SVG/PNG (paper figures). AUC-PR always reads against
          its prevalence baseline.
        </p>
      </div>

      <div className="grid gap-4">
        <RigorSection dataset={dataset} />
        {data.runs.map((run, i) => {
          const m = run.metrics as Record<string, Record<string, unknown>>;
          const steps = parsePerTimeStep(m.node_level);
          const precK = parseAtK(m.node_level, "precision");
          const queueK = parseQueue(m.alert_level);
          const shortSrc = run.source.split(/[\\/]/).slice(-2).join("/");

          return (
            <motion.div
              key={run.source}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.3 }}
              className="grid gap-3"
            >
              <div className="mono px-2 text-xs text-text-2">{shortSrc}</div>

              {/* Headline + budget table.
                  Previously this dumped EVERY numeric key as its own tile in
                  dict order — 12 unlabelled tiles per run, with counts run
                  through toFixed(4) so n_confirmed read "16670.0000". Nobody
                  could present from that. Now: one hero number read against its
                  own prevalence baseline, plus a proper per-budget table. */}
              {m.node_level && <HeadlineBlock nodeLevel={m.node_level} />}

              <div className="grid gap-3 xl:grid-cols-2">
                {steps.length > 0 && (
                  <ChartCard
                    title="AUC-PR by time step"
                    subtitle="temporal shift, per-step vs its own prevalence (dashed) — the step-43 regime change is the finding"
                    hue={UI_HUES.cyan}
                    filename={`${dataset}_auc_pr_by_step`}
                  >
                    <StepBarChart points={steps} color={CHART_SERIES[0]} />
                  </ChartCard>
                )}
                {precK.length > 0 && (
                  <ChartCard
                    title="Node-level precision@k"
                    subtitle="measured at the run's published budgets only"
                    hue={UI_HUES.violet}
                    filename={`${dataset}_precision_at_k`}
                  >
                    <AtKChart
                      points={precK}
                      color={CHART_SERIES[1]}
                      budget={budget}
                      label="P"
                    />
                  </ChartCard>
                )}
                {queueK.length > 0 && (
                  <ChartCard
                    title="Alert-level queue precision"
                    subtitle="deduplicated community alerts; unconfirmed ≠ false (77% unknown labels on Elliptic++)"
                    hue={UI_HUES.magenta}
                    filename={`${dataset}_queue_precision`}
                  >
                    <AtKChart
                      points={queueK}
                      color={CHART_SERIES[3]}
                      budget={budget}
                      label="P"
                    />
                  </ChartCard>
                )}
              </div>

              {/* the complete tree stays inspectable */}
              <Glass className="p-3">
                <details>
                  <summary className="cursor-pointer text-xs text-text-1 transition-colors hover:text-accent">
                    full metrics tree
                  </summary>
                  <div className="mt-2">
                    <MetricsTree node={run.metrics} />
                  </div>
                </details>
              </Glass>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function MetricsTree({ node }: { node: Record<string, unknown> }) {
  const scalars: [string, number | string][] = [];
  const nested: [string, Record<string, unknown>][] = [];
  for (const [k, v] of Object.entries(node)) {
    if (v !== null && typeof v === "object") {
      nested.push([k, v as Record<string, unknown>]);
    } else if (typeof v === "number" || typeof v === "string") {
      scalars.push([k, v]);
    }
  }
  return (
    <div className="grid gap-3">
      {scalars.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {scalars.map(([k, v]) => (
            <div
              key={k}
              className="min-w-24 rounded-md px-2.5 py-1.5"
              style={{
                background: "var(--bg-2)",
                boxShadow: "inset 0 0 0 1px var(--hairline)",
              }}
            >
              <div className="text-[10px] uppercase tracking-wide text-text-2">
                {k}
              </div>
              <div className="mono text-sm text-text-0">
                {typeof v === "number" ? v.toFixed(4) : v}
              </div>
            </div>
          ))}
        </div>
      )}
      {nested.map(([k, v]) => (
        <details
          key={k}
          className="rounded-md p-2"
          style={{
            background: "var(--bg-2)",
            boxShadow: "inset 0 0 0 1px var(--hairline)",
          }}
        >
          <summary className="cursor-pointer text-xs text-text-1 transition-colors hover:text-accent">
            {k}
          </summary>
          <div className="mt-2">
            <MetricsTree node={v} />
          </div>
        </details>
      ))}
    </div>
  );
}
