import { motion } from "motion/react";
import { useExplanation } from "../../api/hooks";
import { SCREENING_CAVEAT } from "../../api/types";
import { CopilotMark } from "../../components/copilot/CopilotMark";
import { Glass } from "../../components/ui/Glass";
import { MotifSchematic } from "../../components/ui/MotifSchematic";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { decodeAlertId } from "../../lib/alertLabel";
import { isMotifId } from "../../lib/motifs";
import { MOTIF_HUE, UI_HUES } from "../../lib/palette";
import { useConsole } from "../../state/console";

// The RQ3 surface (§5.3 view 4). V2: the bundle renders as DESIGNED evidence
// cards (typed rows, per-source labels, red-flag citations, fidelity tiles,
// DrawSVG schematic) — raw JSON survives only in the collapsible technical
// appendix and the export. Fields we don't recognize still render there, so
// nothing a bundle carries is ever hidden.
const KNOWN = new Set([
  "alert_id",
  "dataset",
  "domain",
  "rank",
  "risk_score",
  "community_id",
  "model_run_id",
  "member_node_ids",
  "motif",
  "evidence",
  "evidence_sources",
  "red_flags",
  "fidelity",
  "fidelity_sane",
  "attention_summary",
  "minimal_subgraph",
  "caveats",
  "created_at",
]);

type Bundle = Record<string, unknown>;

/** How to READ the two PyG fidelity numbers (docs/model_card.md, §7 step 27).
 *
 *  For a single alert both are hard 0/1 verdicts — PyG compares the model's
 *  hard predictions — so printing "0.000" told the reader nothing and, worse,
 *  hid that the two zeros mean OPPOSITE things:
 *    fidelity_minus = 0  → the highlighted evidence ALONE reproduces the
 *                          decision. This is the BEST possible value.
 *    fidelity_plus  = 0  → removing the evidence does NOT change the decision,
 *                          i.e. it was not necessary. This is the WEAK case.
 *  So each tile asks the question the number actually answers. */
const FIDELITY_TILES = [
  {
    key: "fidelity_minus",
    label: "fidelity−",
    question: "Is the highlighted evidence enough on its own?",
    goodWhen: "low" as const,
  },
  {
    key: "fidelity_plus",
    label: "fidelity+",
    question: "Does removing it change the decision?",
    goodWhen: "high" as const,
  },
];

export function CaseDetail() {
  const dataset = useConsole((s) => s.dataset);
  const alertId = useConsole((s) => s.selectedAlertId);
  const setView = useConsole((s) => s.setView);
  const askCopilotAbout = useConsole((s) => s.askCopilotAbout);
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

  const bundle = data.bundle as Bundle;
  const motif = bundle.motif as Bundle | null | undefined;
  const motifType = motif ? String(motif.motif_type ?? motif.type ?? "") : "";
  const evidence = (bundle.evidence ?? {}) as Bundle;
  const sources = (bundle.evidence_sources ?? {}) as Record<string, string[]>;
  const flags = (bundle.red_flags ?? []) as Record<string, string>[];
  const fidelity = bundle.fidelity as Record<string, number> | null | undefined;
  const members = (bundle.member_node_ids ?? []) as string[];
  const attention = bundle.attention_summary as Bundle | null | undefined;
  const minimal = (bundle.minimal_subgraph ?? {}) as {
    nodes?: unknown[];
    edges?: unknown[];
  };
  const minimalNodes = minimal.nodes?.length ?? 0;
  const minimalEdges = minimal.edges?.length ?? 0;
  const label = decodeAlertId(alertId ?? "");
  const unknownKeys = Object.keys(bundle).filter((k) => !KNOWN.has(k));

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
    <Glass className="flex h-full flex-col overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-hairline/60 px-4 py-2.5">
        <h2 className="display text-sm font-semibold">
          Evidence <span className="text-grad">Dossier</span>
        </h2>
        <div className="flex flex-col leading-tight">
          <span className="text-xs text-text-0">
            {label.caseName}
            <span className="text-text-2">
              {" "}
              · {label.dataset} · scored by the {label.scorer}
              {label.attempt ? ` (${label.attempt})` : ""}
            </span>
          </span>
          <span
            className="mono text-[10px] text-text-2"
            title="the machine id — used by the API, the exported JSON and the Copilot"
          >
            {alertId}
          </span>
        </div>
        {typeof bundle.risk_score === "number" && (
          <span
            className="mono rounded-md px-2 py-0.5 text-xs"
            title="calibrated probability — a screening score, not certainty"
            style={{
              color: "var(--risk-high)",
              background: "var(--risk-high-dim)",
            }}
          >
            p = {(bundle.risk_score as number).toFixed(3)}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => askCopilotAbout(alertId)}
            title="open the Copilot seeded with this alert (§5.3 view 7)"
            className="btn-sheen rounded-md px-3 py-1 text-xs"
            style={{
              color: "var(--hue-magenta)",
              background: "color-mix(in srgb, var(--hue-magenta) 14%, transparent)",
              boxShadow:
                "inset 0 0 0 1px color-mix(in srgb, var(--hue-magenta) 35%, transparent)",
            }}
          >
            <span className="inline-flex items-center gap-1.5">
              <CopilotMark size={14} /> Ask Copilot
            </span>
          </button>
          <button
            onClick={() => setView("explorer")}
            className="btn-sheen rounded-md px-3 py-1 text-xs text-text-1"
            style={{
              background: "var(--glass-fill-lo)",
              boxShadow: "inset 0 0 0 1px var(--hairline)",
            }}
          >
            ← Subgraph
          </button>
          <button
            onClick={exportJson}
            className="btn-sheen rounded-md px-3 py-1 text-xs"
            style={{
              color: "var(--accent)",
              background: "var(--accent-dim)",
              boxShadow:
                "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
            }}
          >
            Export JSON
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-3 lg:grid-cols-2">
          {/* motif schematic — the pattern that fired, drawing itself */}
          <Card
            title="Detected pattern"
            hue={motifType ? MOTIF_HUE[motifType] : undefined}
            delay={0}
          >
            {motifType && isMotifId(motifType) ? (
              <>
                <MotifSchematic motif={motifType} />
                {typeof motif?.n_instances === "number" && (
                  <p className="mt-2 text-center text-xs text-text-2">
                    <span className="mono text-text-1">
                      {String(motif.n_instances)}
                    </span>{" "}
                    instance{(motif.n_instances as number) > 1 ? "s" : ""} matched
                    in this community
                  </p>
                )}
              </>
            ) : (
              /* No textbook shape matched. The learned evidence still exists —
                 it used to sit collapsed in the technical appendix, which made
                 the dossier LOOK empty on exactly the alerts a reviewer most
                 needs to justify. Surface it here instead. */
              <div className="py-2">
                <p className="mb-2 text-xs leading-snug text-text-2">
                  No nameable motif matched. The matcher only names the nine
                  shapes it can prove; it never invents one. What the model
                  actually keyed on is below.
                </p>
                <div className="grid gap-1.5 text-xs">
                  {minimalNodes > 0 && (
                    <div className="flex justify-between gap-3">
                      <span className="text-text-2">
                        Minimal sub-network the explainer kept
                      </span>
                      <span className="mono text-text-1">
                        {minimalNodes} nodes · {minimalEdges} links
                      </span>
                    </div>
                  )}
                  {typeof attention?.max_incoming_attention === "number" && (
                    <div className="flex justify-between gap-3">
                      <span className="text-text-2">
                        Strongest single incoming link (attention)
                      </span>
                      <span className="mono text-text-1">
                        {(attention.max_incoming_attention as number).toFixed(3)}
                      </span>
                    </div>
                  )}
                  {members.length > 0 && (
                    <div className="flex justify-between gap-3">
                      <span className="text-text-2">Community size</span>
                      <span className="mono text-text-1">
                        {members.length} members
                      </span>
                    </div>
                  )}
                </div>
                <p className="mt-2 text-[11px] leading-snug text-text-2">
                  An absent motif is an honest answer, never fabricated — see
                  Attribution quality for whether this evidence reproduces the
                  decision.
                </p>
              </div>
            )}
          </Card>

          {/* red flags — indicator citations */}
          <Card title={`Red flags (${flags.length})`} hue={UI_HUES.amber} delay={1}>
            {flags.length === 0 ? (
              <p className="py-6 text-center text-xs text-text-2">
                No indicator citations for this alert.
              </p>
            ) : (
              <div className="grid gap-2">
                {flags.map((f, i) => (
                  <div
                    key={i}
                    className="hover-lift rounded-md border-l-2 p-2.5 text-xs"
                    style={
                      {
                        borderColor: "var(--hue-amber)",
                        background:
                          "color-mix(in srgb, var(--hue-amber) 8%, transparent)",
                        "--panel-hue": "var(--hue-amber)",
                      } as React.CSSProperties
                    }
                  >
                    {(f.indicator ?? f.indicator_id) && (
                      <div className="mb-1 flex items-center gap-2">
                        <span className="font-medium text-text-0">
                          {f.indicator ?? f.indicator_id}
                        </span>
                        {f.source && <SourceTag source={f.source} />}
                      </div>
                    )}
                    {Object.entries(f)
                      .filter(([k]) => !["indicator", "source"].includes(k))
                      .map(([k, v]) => (
                        <div key={k} className="mb-0.5 flex gap-2">
                          <span className="shrink-0 uppercase tracking-wide text-text-2">
                            {k.replace(/_/g, " ")}
                          </span>
                          <span className="text-text-1">{String(v)}</span>
                        </div>
                      ))}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* evidence fields with per-source labels (§4.4 scope honesty) */}
          <Card title="Evidence" hue={UI_HUES.cyan} delay={2}>
            <div className="grid gap-1.5">
              {Object.entries(evidence).map(([k, v]) => (
                <div
                  key={k}
                  className="flex items-baseline gap-2 border-b border-hairline/30 pb-1.5 text-xs"
                >
                  <span className="w-36 shrink-0 uppercase tracking-wide text-text-2">
                    {k.replace(/_/g, " ")}
                  </span>
                  <span className="mono min-w-0 flex-1 break-words text-text-0">
                    {fmtValue(v)}
                  </span>
                  {sources[k] && (
                    <span className="shrink-0 text-[10px] text-text-2">
                      {sources[k].join(" · ")}
                    </span>
                  )}
                </div>
              ))}
              {Object.keys(sources).length > 0 && (
                <p className="pt-1 text-[10px] text-text-2">
                  labels name each field's evidence source — absent channels are
                  absent, not imputed
                </p>
              )}
            </div>
          </Card>

          {/* fidelity + members */}
          <Card title="Attribution quality" hue={UI_HUES.violet} delay={3}>
            {fidelity ? (
              <div className="mb-3 flex flex-wrap gap-2">
                {FIDELITY_TILES.map(({ key, label, question, goodWhen }) => {
                  const v = fidelity[key];
                  if (typeof v !== "number") return null;
                  // PyG fidelity is a HARD 0/1 verdict for a single alert
                  // (it compares hard predictions), so a bare "0.000" is
                  // unreadable — and worse, ambiguous: fidelity_minus = 0 is
                  // the BEST value while fidelity_plus = 0 is the WORST.
                  const good = goodWhen === "low" ? v === 0 : v > 0;
                  return (
                    <div
                      key={key}
                      className="min-w-[13.5rem] rounded-md px-2.5 py-1.5"
                      title={`${label} = ${v.toFixed(3)} — for one alert this is a yes/no verdict, not a sliding scale`}
                      style={{
                        background: "var(--bg-2)",
                        boxShadow: `inset 0 0 0 1px ${
                          good ? "color-mix(in srgb, var(--benign) 42%, transparent)" : "var(--hairline)"
                        }`,
                      }}
                    >
                      <div className="text-[10px] uppercase tracking-wide text-text-2">
                        {question}
                      </div>
                      <div
                        className="text-sm font-medium"
                        style={{ color: good ? "var(--benign)" : "var(--hue-amber)" }}
                      >
                        {good ? "Yes" : "No"}
                        <span className="mono ml-1.5 text-[11px] text-text-2">
                          ({label} {v.toFixed(2)})
                        </span>
                      </div>
                    </div>
                  );
                })}
                {bundle.fidelity_sane === false && (
                  <div
                    className="flex items-center rounded-md px-2.5 py-1.5 text-xs"
                    title="fidelity− ≥ fidelity+: the learned mask explains poorly here (measured, flagged, never hidden)"
                    style={{
                      color: "var(--hue-amber)",
                      background: "var(--risk-med-dim)",
                    }}
                  >
                    ⚠ fidelity check failed — treat attribution cautiously
                  </div>
                )}
                <p className="w-full text-[11px] leading-snug text-text-2">
                  For a single alert these are yes/no verdicts, not scores: the
                  test re-runs the model with the highlighted evidence alone, and
                  again with it removed, and checks whether the decision holds.
                </p>
              </div>
            ) : (
              <p className="mb-3 text-xs text-text-2">
                No learned attribution for this model family (R12) — matcher and
                screen evidence carry this bundle.
              </p>
            )}
            {members.length > 0 && (
              <>
                <div className="mb-1 text-[10px] uppercase tracking-wide text-text-2">
                  {members.length} community members
                </div>
                <div className="flex flex-wrap gap-1">
                  {members.slice(0, 14).map((m) => (
                    <span
                      key={m}
                      className="mono rounded bg-bg-2 px-1.5 py-0.5 text-[10px] text-text-1"
                    >
                      {m}
                    </span>
                  ))}
                  {members.length > 14 && (
                    <span className="text-[10px] text-text-2">
                      +{members.length - 14} more
                    </span>
                  )}
                </div>
              </>
            )}
          </Card>
        </div>

        {/* technical appendix — full payload, nothing hidden */}
        {(attention || bundle.minimal_subgraph || unknownKeys.length > 0) && (
          <details className="mt-3 rounded-md bg-bg-1/60 p-2">
            <summary className="cursor-pointer text-xs text-text-1 transition-colors hover:text-accent">
              Technical appendix (attention summary, minimal subgraph
              {unknownKeys.length > 0 ? `, ${unknownKeys.join(", ")}` : ""})
            </summary>
            <pre className="mono mt-2 overflow-x-auto text-[11px] leading-relaxed text-text-1">
              {JSON.stringify(
                {
                  attention_summary: attention ?? undefined,
                  minimal_subgraph: bundle.minimal_subgraph ?? undefined,
                  ...Object.fromEntries(unknownKeys.map((k) => [k, bundle[k]])),
                },
                null,
                2,
              )}
            </pre>
          </details>
        )}

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

function Card({
  title,
  hue,
  delay,
  children,
}: {
  title: string;
  hue?: string;
  delay: number;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.07, duration: 0.3 }}
    >
      <Glass neon lift hue={hue} className="h-full p-3.5">
        <div
          className="mb-2 text-xs font-medium uppercase tracking-wide"
          style={{ color: hue ?? "var(--text-2)" }}
        >
          {title}
        </div>
        {children}
      </Glass>
    </motion.div>
  );
}

function SourceTag({ source }: { source: string }) {
  return (
    <span
      className="rounded px-1 py-px text-[10px] font-medium"
      title={`indicator source: ${source}`}
      style={{
        color: "var(--hue-magenta)",
        background: "color-mix(in srgb, var(--hue-magenta) 14%, transparent)",
      }}
    >
      {source}
    </span>
  );
}

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.map(fmtValue).join(" – ");
  if (typeof v === "number")
    return Number.isInteger(v) ? String(v) : v.toFixed(4);
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
