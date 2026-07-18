import { motion } from "motion/react";
import { useAlerts } from "../../api/hooks";
import type { AlertRow } from "../../api/types";
import { BudgetSlider } from "../../components/ui/BudgetSlider";
import { MotifChip, RiskChip } from "../../components/ui/Chips";
import { Glass } from "../../components/ui/Glass";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { fmtTimeWindow, shortId } from "../../lib/format";
import { useConsole } from "../../state/console";

// The core operational surface (§5.3 view 2): ranked, deduplicated alerts at a
// user-adjustable budget. Selecting a row seeds the Graph Explorer / Case Detail.
export function AlertQueue() {
  const dataset = useConsole((s) => s.dataset);
  const budget = useConsole((s) => s.budget);
  const selected = useConsole((s) => s.selectedAlertId);
  const selectAlert = useConsole((s) => s.selectAlert);
  const setView = useConsole((s) => s.setView);
  const { data, isLoading, isError, error } = useAlerts(dataset, budget);

  const openAlert = (a: AlertRow) => {
    selectAlert(a.alert_id);
    setView("explorer");
  };

  return (
    <Glass className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center gap-4 border-b border-hairline/60 px-4 py-2.5">
        <h2 className="display text-sm font-semibold">Alert Queue</h2>
        <BudgetSlider />
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
                background:
                  "color-mix(in srgb, var(--bg-1) 88%, var(--accent))",
                backdropFilter: "blur(10px)",
              }}
            >
              <tr className="border-b border-hairline">
                <th className="px-4 py-2 font-medium">#</th>
                <th className="px-4 py-2 font-medium">Risk</th>
                <th className="px-4 py-2 font-medium">Motif</th>
                <th className="px-4 py-2 font-medium">Members</th>
                <th className="px-4 py-2 font-medium">Time window</th>
                <th className="px-4 py-2 font-medium">Alert ID</th>
              </tr>
            </thead>
            <tbody>
              {data.alerts.map((a, i) => {
                const active = a.alert_id === selected;
                return (
                  <motion.tr
                    key={a.alert_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      delay: Math.min(i, 14) * 0.022,
                      duration: 0.25,
                    }}
                    onClick={() => openAlert(a)}
                    className="cursor-pointer border-b border-hairline/40 transition-colors hover:bg-bg-2/60"
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
                    <td className="mono px-4 py-1.5 text-text-1">
                      {a.n_members}
                    </td>
                    <td className="mono px-4 py-1.5 text-text-1">
                      {fmtTimeWindow(a.time_window_start, a.time_window_end)}
                    </td>
                    <td className="mono px-4 py-1.5 text-text-2">
                      {shortId(a.alert_id, 22)}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </Glass>
  );
}
