import { useMetrics } from "../../api/hooks";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { useConsole } from "../../state/console";

// The figure factory (§5.3 view 5): renders published metrics runs. Full PR /
// precision@k curves + transfer-matrix heatmaps with SVG/PNG export are the
// visx build-out; this ships the metrics tables + a per-time-step bar (the
// step-43 shift, §4.3 D1) so the numbers are inspectable now.
export function ModelLab() {
  const dataset = useConsole((s) => s.dataset);
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
    <div className="min-h-0 flex-1 overflow-auto p-4">
      <h2 className="mb-3 text-sm font-medium">Model Lab</h2>
      <div className="grid gap-4">
        {data.runs.map((run) => (
          <div
            key={run.source}
            className="rounded-lg border border-hairline bg-bg-1 p-3"
          >
            <div className="mono mb-2 text-xs text-text-2">{run.source}</div>
            <MetricsTree node={run.metrics} />
          </div>
        ))}
      </div>
    </div>
  );
}

// Renders the headline scalar metrics (auc_pr, precision@k, …) as stat tiles;
// nested objects recurse one level so per-time-step blocks stay legible.
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
              className="min-w-24 rounded-md border border-hairline bg-bg-2 px-2.5 py-1.5"
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
        <details key={k} className="rounded-md border border-hairline bg-bg-2 p-2">
          <summary className="cursor-pointer text-xs text-text-1">{k}</summary>
          <div className="mt-2">
            <MetricsTree node={v} />
          </div>
        </details>
      ))}
    </div>
  );
}
