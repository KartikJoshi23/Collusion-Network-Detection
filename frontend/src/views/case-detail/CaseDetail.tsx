import { motion } from "motion/react";
import { useExplanation } from "../../api/hooks";
import { SCREENING_CAVEAT } from "../../api/types";
import { Glass } from "../../components/ui/Glass";
import { MotifGlyph } from "../../components/ui/MotifGlyph";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { MOTIF_LABEL, isMotifId } from "../../lib/motifs";
import { useConsole } from "../../state/console";

// The RQ3 surface (§5.3 view 4): the explanation bundle rendered as an evidence
// dossier — motif, evidence fields, red-flag cards, fidelity, JSON export.
// Known bundle fields (explain/bundles.py) get designed cards; anything else
// falls through to the generic field renderer so new fields are never hidden.
const FIELD_ORDER = [
  "alert_id",
  "risk_score",
  "motif",
  "red_flags",
  "evidence",
  "evidence_sources",
  "fidelity",
  "fidelity_sane",
  "attention_summary",
];

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

  const keys = Object.keys(bundle)
    .filter((k) => k !== "caveats")
    .sort((a, b) => {
      const ia = FIELD_ORDER.indexOf(a);
      const ib = FIELD_ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });

  const motif = bundle["motif"] as Record<string, unknown> | null | undefined;
  const motifType =
    motif && typeof motif === "object"
      ? String(motif["motif_type"] ?? motif["type"] ?? "")
      : "";

  return (
    <Glass className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center gap-3 border-b border-hairline/60 px-4 py-2.5">
        <h2 className="display text-sm font-semibold">Case Detail</h2>
        <span className="mono text-xs text-text-2">{alertId}</span>
        {motifType && isMotifId(motifType) && (
          <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs text-accent"
            style={{ background: "var(--accent-dim)" }}
          >
            <MotifGlyph motif={motifType} size={13} />
            {MOTIF_LABEL[motifType]}
          </span>
        )}
        <button
          onClick={exportJson}
          className="ml-auto rounded-md px-3 py-1 text-xs text-text-1 transition-colors hover:text-accent"
          style={{
            background: "var(--glass-fill)",
            boxShadow: "inset 0 0 0 1px var(--hairline)",
          }}
        >
          Export JSON
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-3">
          {keys.map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i, 10) * 0.04, duration: 0.25 }}
            >
              {key === "red_flags" && Array.isArray(bundle[key]) ? (
                <RedFlags flags={bundle[key] as Record<string, string>[]} />
              ) : (
                <Field label={key} value={bundle[key]} />
              )}
            </motion.div>
          ))}
        </div>
        <p className="mt-4 flex items-center gap-2 text-xs text-text-2">
          <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden>
            <path
              d="M8 1.5 13.5 4v3.8c0 3.4-2.3 5.7-5.5 6.7-3.2-1-5.5-3.3-5.5-6.7V4L8 1.5Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.2"
            />
          </svg>
          AI-generated evidence bundle. {SCREENING_CAVEAT}.
        </p>
      </div>
    </Glass>
  );
}

// Red-flag indicator cards (FATF/OECD citations with evidence-source labels).
function RedFlags({ flags }: { flags: Record<string, string>[] }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--bg-2)" }}>
      <div className="mb-2 text-xs uppercase tracking-wide text-text-2">
        red flags
      </div>
      {flags.length === 0 ? (
        <div className="text-xs text-text-2">none matched</div>
      ) : (
        <div className="grid gap-2">
          {flags.map((f, i) => (
            <div
              key={i}
              className="rounded-md border-l-2 p-2.5 text-xs"
              style={{
                borderColor: "var(--risk-med)",
                background: "var(--risk-med-dim)",
              }}
            >
              {Object.entries(f).map(([k, v]) => (
                <div key={k} className="mb-0.5 flex gap-2">
                  <span className="shrink-0 uppercase tracking-wide text-text-2">
                    {k.replace(/_/g, " ")}
                  </span>
                  <span className="text-text-0">{String(v)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: unknown }) {
  const isObj = value !== null && typeof value === "object";
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--bg-2)" }}>
      <div className="mb-1 text-xs uppercase tracking-wide text-text-2">
        {label.replace(/_/g, " ")}
      </div>
      {isObj ? (
        <pre className="mono overflow-x-auto text-xs leading-relaxed text-text-1">
          {JSON.stringify(value, null, 2)}
        </pre>
      ) : (
        <div className="mono text-sm text-text-0">{String(value)}</div>
      )}
    </div>
  );
}
