import { useEffect } from "react";
import { useDatasets } from "../api/hooks";
import type { Domain } from "../api/types";
import { deepLinkTarget } from "../lib/deeplink";
import { useConsole } from "../state/console";

export function DatasetSelector() {
  const domain = useConsole((s) => s.domain);
  const dataset = useConsole((s) => s.dataset);
  const setDataset = useConsole((s) => s.setDataset);
  const selectedAlertId = useConsole((s) => s.selectedAlertId);
  const hydrateFromAlert = useConsole((s) => s.hydrateFromAlert);
  const { data, isLoading, isError } = useDatasets();

  const inDomain =
    data?.datasets.filter((d) => d.domain === domain) ?? [];

  // Auto-select when none is chosen: a deep-linked alert names its own
  // dataset+domain (lib/deeplink.ts) and wins over the domain default —
  // otherwise a procurement deep link would resolve under `financial`.
  useEffect(() => {
    if (dataset) return;
    const linked = deepLinkTarget(selectedAlertId, data?.datasets);
    if (linked) {
      hydrateFromAlert(linked.domain as Domain, linked.dataset);
      return;
    }
    if (inDomain.length > 0) setDataset(inDomain[0].dataset);
  }, [dataset, selectedAlertId, data, hydrateFromAlert, inDomain, setDataset]);

  if (isLoading)
    return <span className="text-xs text-text-2">loading datasets…</span>;
  if (isError)
    return <span className="text-xs text-risk-high">API unreachable</span>;
  if (inDomain.length === 0)
    return (
      <span className="text-xs text-text-2">no {domain} datasets published</span>
    );

  return (
    <select
      value={dataset ?? ""}
      onChange={(e) => setDataset(e.target.value)}
      className="mono rounded-md px-2 py-1 text-xs text-text-0 outline-none focus:border-accent"
      style={{
        background: "var(--glass-fill)",
        border: "1px solid var(--hairline)",
      }}
    >
      {inDomain.map((d) => (
        <option key={d.dataset} value={d.dataset}>
          {d.dataset}
          {d.has_alerts ? "" : " (no queue)"}
        </option>
      ))}
    </select>
  );
}
