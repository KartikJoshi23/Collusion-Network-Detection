import { useExplanation } from "../../api/hooks";
import { SCREENING_CAVEAT } from "../../api/types";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { useConsole } from "../../state/console";

// The RQ3 surface (§5.3 view 4): the explanation bundle rendered as an evidence
// dossier — motif, evidence fields, red-flag cards, fidelity, JSON export.
export function CaseDetail() {
  const dataset = useConsole((s) => s.dataset);
  const alertId = useConsole((s) => s.selectedAlertId);
  const { data, isLoading, isError, error } = useExplanation(dataset, alertId);

  if (!alertId)
    return (
      <Empty
        title="No alert selected"
        hint="Open an alert to see its explanation bundle."
      />
    );
  if (isLoading) return <Loading label="Loading explanation bundle…" />;
  if (isError)
    return (
      <ErrorState
        message="No explanation bundle for this alert"
        detail={(error as Error)?.message}
      />
    );
  if (!data) return null;

  const bundle = data.bundle;
  const exportJson = () => {
    const blob = new Blob([JSON.stringify(bundle, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${alertId.replace(/[:]/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-hairline bg-bg-1 px-4 py-2">
        <h2 className="text-sm font-medium">Case Detail</h2>
        <span className="mono text-xs text-text-2">{alertId}</span>
        <button
          onClick={exportJson}
          className="ml-auto rounded-md border border-hairline bg-bg-2 px-3 py-1 text-xs text-text-1 hover:bg-bg-3"
        >
          Export JSON
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-3">
          {Object.entries(bundle).map(([key, value]) => (
            <Field key={key} label={key} value={value} />
          ))}
        </div>
        <p className="mt-4 text-xs text-text-2">
          AI-generated evidence bundle. {SCREENING_CAVEAT}.
        </p>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: unknown }) {
  const isObj = value !== null && typeof value === "object";
  return (
    <div className="rounded-lg border border-hairline bg-bg-1 p-3">
      <div className="mb-1 text-xs uppercase tracking-wide text-text-2">
        {label}
      </div>
      {isObj ? (
        <pre className="mono overflow-x-auto text-xs text-text-1">
          {JSON.stringify(value, null, 2)}
        </pre>
      ) : (
        <div className="mono text-sm text-text-0">{String(value)}</div>
      )}
    </div>
  );
}
