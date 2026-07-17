import { useAlerts, useDatasets } from "../../api/hooks";
import { RiskChip } from "../../components/ui/Chips";
import { Empty, Loading } from "../../components/ui/States";
import { useConsole } from "../../state/console";

// Command deck (§5.3 view 1): a KPI band for the active dataset + the top
// flagged alerts, as the demo-day landing surface.
export function Overview() {
  const dataset = useConsole((s) => s.dataset);
  const domain = useConsole((s) => s.domain);
  const budget = useConsole((s) => s.budget);
  const setView = useConsole((s) => s.setView);
  const selectAlert = useConsole((s) => s.selectAlert);
  const datasets = useDatasets();
  const { data, isLoading } = useAlerts(dataset, budget);

  if (!dataset) return <Empty title="No dataset selected" />;

  const nDatasets =
    datasets.data?.datasets.filter((d) => d.domain === domain).length ?? 0;
  const top = data?.alerts.slice(0, 8) ?? [];

  return (
    <div className="min-h-0 flex-1 overflow-auto p-4">
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Domain" value={domain} />
        <Kpi label="Dataset" value={dataset} mono />
        <Kpi label="Alerts in queue" value={String(data?.k_effective ?? "…")} mono />
        <Kpi label={`${domain} datasets`} value={String(nDatasets)} mono />
      </div>

      <div className="rounded-lg border border-hairline bg-bg-1">
        <div className="flex items-center border-b border-hairline px-3 py-2">
          <h3 className="text-sm font-medium">Top flagged communities</h3>
          <button
            onClick={() => setView("queue")}
            className="ml-auto text-xs text-text-2 hover:text-accent"
          >
            open full queue →
          </button>
        </div>
        {isLoading ? (
          <Loading />
        ) : top.length === 0 ? (
          <Empty title="No alerts published" />
        ) : (
          <ul>
            {top.map((a) => (
              <li
                key={a.alert_id}
                onClick={() => {
                  selectAlert(a.alert_id);
                  setView("explorer");
                }}
                className="flex cursor-pointer items-center gap-3 border-b border-hairline/50 px-3 py-2 hover:bg-bg-2"
              >
                <span className="mono w-6 text-xs text-text-2">{a.rank}</span>
                <RiskChip score={a.risk_score} />
                <span className="mono text-xs text-text-1">
                  {a.n_members} members
                </span>
                <span className="mono ml-auto text-xs text-text-2">
                  {a.motif_type ?? "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-hairline bg-bg-1 p-3">
      <div className="text-xs text-text-2">{label}</div>
      <div className={`mt-1 text-lg text-text-0 ${mono ? "mono" : ""}`}>
        {value}
      </div>
    </div>
  );
}
