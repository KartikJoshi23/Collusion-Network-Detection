import { useEffect } from "react";
import { useDatasets } from "../api/hooks";
import { useConsole } from "../state/console";

export function DatasetSelector() {
  const domain = useConsole((s) => s.domain);
  const dataset = useConsole((s) => s.dataset);
  const setDataset = useConsole((s) => s.setDataset);
  const { data, isLoading, isError } = useDatasets();

  const inDomain =
    data?.datasets.filter((d) => d.domain === domain) ?? [];

  // Auto-select the first dataset in the active domain when none is chosen.
  useEffect(() => {
    if (!dataset && inDomain.length > 0) setDataset(inDomain[0].dataset);
  }, [dataset, inDomain, setDataset]);

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
      className="mono rounded-md border border-hairline bg-bg-1 px-2 py-1 text-xs text-text-0 outline-none focus:border-accent"
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
