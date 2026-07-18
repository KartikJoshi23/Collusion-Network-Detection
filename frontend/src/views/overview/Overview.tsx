import { motion } from "motion/react";
import { useAlerts, useDatasets } from "../../api/hooks";
import { CountUp } from "../../components/ui/CountUp";
import { RiskChip } from "../../components/ui/Chips";
import { Glass } from "../../components/ui/Glass";
import { MotifGlyph } from "../../components/ui/MotifGlyph";
import { Empty, Loading } from "../../components/ui/States";
import { MOTIF_LABEL, isMotifId } from "../../lib/motifs";
import { MOTIF_HUE, UI_HUES } from "../../lib/palette";
import { useConsole } from "../../state/console";

// Command deck (§5.3 view 1). V2 rules applied: ≥3 hue families at rest
// (cyan KPI, coral flagged, amber budget, violet datasets), the alert
// constellation as the hero with a cursor spotlight, staggered top-flagged
// list with per-family motif hues.
import { Constellation } from "./Constellation";

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
  const flagged = data?.alerts.filter((a) => a.risk_score >= 0.66).length ?? 0;

  return (
    <div className="h-full min-h-0 overflow-auto p-2">
      <div className="mb-4 px-2 pt-3">
        <div className="text-xs uppercase tracking-[0.2em] text-text-2">
          {domain} domain · integrity screening
        </div>
        <h1 className="display mt-1 text-3xl font-semibold leading-tight">
          Network <span className="text-grad">surveillance</span> deck
        </h1>
        <p className="mt-1 max-w-xl text-sm text-text-1">
          Ranked collusion-pattern alerts over the{" "}
          <span className="mono text-text-0">{dataset}</span> ledger — calibrated
          screening probabilities, never verdicts.
        </p>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi
          label="Alerts in queue"
          value={data?.k_effective}
          loading={isLoading}
          hue={UI_HUES.cyan}
        />
        <Kpi
          label="High-band alerts"
          value={isLoading ? undefined : flagged}
          hue={UI_HUES.coral}
        />
        <Kpi label="Budget k" value={budget} hue={UI_HUES.amber} />
        <Kpi label={`${domain} datasets`} value={nDatasets} hue={UI_HUES.violet} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[3fr_2fr]">
        {/* hero — the queue as a constellation */}
        <Glass strong neon className="overflow-hidden">
          <div className="flex items-center border-b border-hairline/60 px-4 py-2.5">
            <h3 className="text-sm font-medium">
              Flagged-community constellation
            </h3>
            <span className="mono ml-auto text-xs text-text-2">
              top {Math.min(data?.alerts.length ?? 0, 60)} alerts
            </span>
          </div>
          {isLoading ? (
            <Loading />
          ) : !data || data.alerts.length === 0 ? (
            <Empty title="No alerts published" />
          ) : (
            <Constellation alerts={data.alerts.slice(0, 60)} />
          )}
        </Glass>

        {/* top flagged list */}
        <Glass className="overflow-hidden">
          <div className="flex items-center border-b border-hairline/60 px-4 py-2.5">
            <h3 className="text-sm font-medium">Top flagged communities</h3>
            <button
              onClick={() => setView("queue")}
              className="btn-sheen ml-auto rounded px-2 py-0.5 text-xs text-text-2 hover:text-accent"
            >
              full queue →
            </button>
          </div>
          {isLoading ? (
            <Loading />
          ) : top.length === 0 ? (
            <Empty title="No alerts published" />
          ) : (
            <ul>
              {top.map((a, i) => (
                <motion.li
                  key={a.alert_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 + i * 0.045, duration: 0.3 }}
                  onClick={() => {
                    selectAlert(a.alert_id);
                    setView("explorer");
                  }}
                  className="hover-row group flex cursor-pointer items-center gap-3 border-b border-hairline/40 px-4 py-2"
                >
                  <span className="mono w-6 text-xs text-text-2">{a.rank}</span>
                  <RiskChip score={a.risk_score} />
                  <span className="mono text-xs text-text-1">
                    {a.n_members} members
                  </span>
                  <span className="ml-auto inline-flex items-center gap-1.5 text-xs">
                    {a.motif_type ? (
                      <span
                        className="inline-flex items-center gap-1.5"
                        style={{
                          color: MOTIF_HUE[a.motif_type] ?? "var(--text-2)",
                        }}
                      >
                        <MotifGlyph motif={a.motif_type} size={13} />
                        {isMotifId(a.motif_type)
                          ? MOTIF_LABEL[a.motif_type]
                          : a.motif_type}
                      </span>
                    ) : (
                      <span className="text-text-2">—</span>
                    )}
                  </span>
                  <span className="text-xs text-text-2 opacity-0 transition-opacity group-hover:opacity-100">
                    →
                  </span>
                </motion.li>
              ))}
            </ul>
          )}
        </Glass>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  loading,
  hue,
}: {
  label: string;
  value: number | undefined;
  loading?: boolean;
  hue: string;
}) {
  return (
    <Glass neon lift hue={hue} className="p-3.5">
      <div className="text-xs text-text-2">{label}</div>
      <div className="mono mt-1 text-2xl" style={{ color: hue }}>
        {loading || value === undefined ? "…" : <CountUp value={value} />}
      </div>
    </Glass>
  );
}
