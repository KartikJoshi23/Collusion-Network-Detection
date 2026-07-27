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
        {/* Name the actual crime. "Financial domain" alone never told a viewer
            this is anti-money-laundering screening — an audit found "AML"
            appeared nowhere in the console outside two buried About lines. */}
        <div className="text-xs uppercase tracking-[0.2em] text-text-2">
          {domain === "financial"
            ? "anti-money laundering (AML) · integrity screening"
            : "bid-rigging / cartel detection · integrity screening"}
        </div>
        <h1 className="display mt-1 text-3xl font-semibold leading-tight">
          Network <span className="text-grad">surveillance</span> deck
        </h1>
        <p className="mt-1 max-w-xl text-sm text-text-1">
          {domain === "financial"
            ? "Ranked money-laundering alerts — groups of accounts moving funds in coordinated patterns — over the "
            : "Ranked bid-rigging alerts — groups of firms coordinating on public contracts — over the "}
          <span className="mono text-text-0">{dataset}</span> ledger. Calibrated
          screening probabilities, never verdicts.
        </p>
        {/* A very short queue looks like a failure unless you say why. García
            yields 3 groups because its records link firms to tenders rather
            than to each other, so few multi-firm clusters form at all. */}
        {!isLoading && data && data.k_effective > 0 && data.k_effective < 10 && (
          <p className="mt-2 max-w-xl rounded-md bg-bg-2 px-3 py-2 text-xs leading-relaxed text-text-1">
            <strong className="text-text-0">
              Only {data.k_effective} group
              {data.k_effective === 1 ? "" : "s"} came out of this dataset.
            </strong>{" "}
            That is a property of the data, not a failure. Records here link
            each firm to the contracts it bid on rather than to other firms, so
            very few groups of firms form in the first place. A short, honest
            queue is better than a padded one.
          </p>
        )}
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
        {/* The slider can ask for more cases than a dataset actually produced.
            Showing the raw request ("50") beside a 3-alert queue reads as a
            bug — reported on García, which genuinely yields only 3 groups.
            Show what you will really review, and say why when they differ. */}
        <Kpi
          label="Cases to review"
          value={data ? Math.min(budget, data.k_effective) : budget}
          loading={isLoading}
          hue={UI_HUES.amber}
          note={
            data && data.k_effective < budget
              ? `you asked for ${budget} — this dataset has only ${data.k_effective}`
              : undefined
          }
        />
        <Kpi label={`${domain} datasets`} value={nDatasets} hue={UI_HUES.violet} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[3fr_2fr]">
        {/* hero — the queue as a constellation (beam = V3 hero affordance) */}
        <Glass strong neon beam className="overflow-hidden">
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
  note,
}: {
  label: string;
  value: number | undefined;
  loading?: boolean;
  hue: string;
  /** Shown under the number when it needs a caveat — e.g. the queue holds
   *  fewer cases than the review slider asked for. */
  note?: string;
}) {
  return (
    <Glass neon lift hue={hue} className="p-3.5">
      <div className="text-xs text-text-2">{label}</div>
      <div className="mono mt-1 text-2xl" style={{ color: hue }}>
        {loading || value === undefined ? "…" : <CountUp value={value} />}
      </div>
      {note && (
        <div className="mt-0.5 text-[10px] leading-snug text-text-2">{note}</div>
      )}
    </Glass>
  );
}
