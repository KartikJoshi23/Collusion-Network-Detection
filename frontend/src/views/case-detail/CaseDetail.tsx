import { motion } from "motion/react";
import { useAlerts, useExplanation } from "../../api/hooks";
import { SCREENING_CAVEAT } from "../../api/types";
import { CopilotMark } from "../../components/copilot/CopilotMark";
import { Glass } from "../../components/ui/Glass";
import { MotifSchematic } from "../../components/ui/MotifSchematic";
import { Empty, Loading } from "../../components/ui/States";
import { decodeAlertId } from "../../lib/alertLabel";
import { fmtTimeWindow } from "../../lib/format";
import { isMotifId } from "../../lib/motifs";
import { MOTIF_HUE, UI_HUES } from "../../lib/palette";
import { plainReason } from "../../lib/plainReason";
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

/** Plain names for the raw evidence keys. Without this the panel printed
 *  "N MEMBER EDGES" and "TIME WINDOW", which mean nothing to a reader. */
const EVIDENCE_LABEL: Record<string, string> = {
  n_members: "How many are in this group",
  n_member_edges: "Connections between them",
  time_window: "When it happened",
  member_time_span: "When the group was active",
  amounts: "Amounts involved",
  fees: "Fees paid",
  degrees: "How many links each one has",
  rotation_sequence: "Order the wins went round",
  price_stats: "Price patterns",
  co_bid_history: "How often they bid together",
  shared_links: "Things they share (address, director)",
};

/** Shown when an alert has no explanation bundle — which is the DESIGNED
 *  outcome for everything below the explanation budget, not a failure. It
 *  reads the alert row (already fetched for the queue) so the reviewer still
 *  gets rank, score, band, size and time window, and says plainly why there is
 *  no dossier. */
function NoBundlePanel({ alertId }: { alertId: string }) {
  const dataset = useConsole((s) => s.dataset);
  const setView = useConsole((s) => s.setView);
  // Wide fetch: these alerts live past the review budget by definition.
  // 500 is the API's hard maximum (validated server-side) — asking for more
  // returns a 422 and the panel silently loses its data.
  const { data } = useAlerts(dataset, 500);
  const row = data?.alerts.find((a) => a.alert_id === alertId);
  const label = decodeAlertId(alertId);
  const score = row?.risk_score;
  const band =
    score === undefined
      ? undefined
      : score >= 0.6
        ? { name: "High", hue: "var(--risk-high)" }
        : score >= 0.2
          ? { name: "Medium", hue: "var(--hue-amber)" }
          : { name: "Low / ordinary", hue: "var(--benign)" };

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
          <span className="mono text-[10px] text-text-2">{alertId}</span>
        </div>
        {score !== undefined && band && (
          <span
            className="mono rounded-md px-2 py-0.5 text-xs"
            style={{
              color: band.hue,
              background: `color-mix(in srgb, ${band.hue} 15%, transparent)`,
            }}
          >
            p = {score.toFixed(3)}
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-3 lg:grid-cols-2">
          <Card title="Why there is no case file" hue={UI_HUES.teal} delay={0}>
            {band?.name === "Low / ordinary" ? (
              <p className="text-xs leading-relaxed text-text-1">
                <span style={{ color: "var(--benign)" }}>
                  This group looks <strong>ordinary</strong>.
                </span>{" "}
                The system did not think it was worth anyone&rsquo;s time, so it
                did not write up a case file. That is the right outcome. This is
                the comparison case — it shows you what the system does{" "}
                <em>not</em> worry about.
              </p>
            ) : (
              <p className="text-xs leading-relaxed text-text-1">
                This case sits further down the list. We only write up the full
                evidence for the cases at the top, because doing that takes real
                computing time. Cases further down still get a score and a
                network you can look at — just not a written-up file.
              </p>
            )}
            <p className="mt-2 text-[11px] leading-snug text-text-2">
              Nothing is hidden here: the network itself is still fully
              inspectable in the Graph Explorer, and the score below comes from
              exactly the same scoring as every other case.
            </p>
            <button
              onClick={() => setView("explorer")}
              className="btn-sheen mt-3 rounded-md px-3 py-1 text-xs"
              style={{
                color: "var(--accent)",
                background: "var(--accent-dim)",
                boxShadow:
                  "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
              }}
            >
              Inspect the network →
            </button>
          </Card>

          <Card title="What we do know" hue={UI_HUES.cyan} delay={1}>
            {row ? (
              <div className="grid gap-1.5 text-xs">
                {[
                  ["Rank in queue", `${row.rank}`],
                  ["Risk score", score?.toFixed(4) ?? "—"],
                  ["Risk band", band?.name ?? "—"],
                  ["Members in group", `${row.n_members}`],
                  [
                    "Time window",
                    fmtTimeWindow(row.time_window_start, row.time_window_end),
                  ],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3">
                    <span className="text-text-2">{k}</span>
                    <span className="mono text-text-1">{v}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-2">
                This alert is not in the currently loaded queue page.
              </p>
            )}
          </Card>
        </div>
        <p className="mt-3 text-[11px] text-text-2">{SCREENING_CAVEAT}</p>
      </div>
    </Glass>
  );
}

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
    question: "Is this evidence enough on its own?",
    goodWhen: "low" as const,
  },
  {
    key: "fidelity_plus",
    label: "fidelity+",
    question: "If we take this evidence away, does the warning go away?",
    goodWhen: "high" as const,
  },
];

export function CaseDetail() {
  const dataset = useConsole((s) => s.dataset);
  const alertId = useConsole((s) => s.selectedAlertId);
  const setView = useConsole((s) => s.setView);
  const askCopilotAbout = useConsole((s) => s.askCopilotAbout);
  const { data, isLoading, isError } = useExplanation(dataset, alertId);

  if (!alertId)
    return (
      <Empty
        title="No alert selected"
        hint="Open an alert to see its explanation bundle."
      />
    );
  if (isLoading) return <Loading label="Loading explanation bundle…" />;
  // A missing bundle is NORMAL, not an error. Detailed explanations are
  // produced for the head of the queue because they cost computation, so every
  // lower-ranked (typically ordinary) group has none. Showing a red error there
  // told the reviewer the system was broken when it was working as designed —
  // and it became reachable the moment the queue gained a "Low / normal"
  // filter. Render what the alert row DOES tell us instead.
  if (isError) return <NoBundlePanel alertId={alertId} />;
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
  const win = (evidence.time_window ?? []) as unknown[];
  const reason = plainReason({
    riskScore: bundle.risk_score as number | undefined,
    nMembers: evidence.n_members as number | undefined,
    nMemberEdges: evidence.n_member_edges as number | undefined,
    windowStart: win[0] as number | undefined,
    windowEnd: win[1] as number | undefined,
    minimalNodes,
    minimalEdges,
    maxAttention: attention?.max_incoming_attention as number | undefined,
    domain: bundle.domain as string | undefined,
  });
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
            title="How strongly this group stands out, on a scale of 0 to 1. It is a reason to look, not proof of anything."
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
                {reason && (
                  <p
                    className="mb-2 text-sm font-medium"
                    style={{ color: "var(--text-0)" }}
                  >
                    {reason.headline}
                  </p>
                )}
                <p className="mb-2 text-xs leading-snug text-text-2">
                  This group does not match any of the nine known cheating
                  patterns by name. We only put a name on a pattern when we can
                  prove it, and we never make one up. The reasons it was still
                  flagged are written out in plain words in the next panel.
                </p>
                <div className="grid gap-1.5 text-xs">
                  {minimalNodes > 0 && (
                    <div className="flex justify-between gap-3">
                      <span className="text-text-2">
                        The few connections that mattered most
                      </span>
                      <span className="mono text-text-1">
                        {minimalNodes} of them ·{" "}
                        {minimalEdges}{" "}
                        {minimalEdges === 1 ? "connection" : "connections"}
                      </span>
                    </div>
                  )}
                  {typeof attention?.max_incoming_attention === "number" && (
                    <div className="flex justify-between gap-3">
                      <span className="text-text-2">
                        Strongest single connection
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
                  Having no named pattern is an honest answer, not a gap. See
                  &ldquo;How solid is this?&rdquo; below for whether this
                  evidence holds up on its own.
                </p>
              </div>
            )}
          </Card>

          {/* red flags — indicator citations */}
          <Card title={`Red flags (${flags.length})`} hue={UI_HUES.amber} delay={1}>
            {flags.length === 0 ? (
              /* An alert can score 0.93 and still cite nothing, because the
                 matcher only names shapes it can formally prove. Showing "no
                 citations" and stopping left a reviewer staring at a high score
                 with no reason. The bundle already holds the facts — say them
                 in plain words instead of leaving the card blank. */
              reason ? (
                <div>
                  <p className="mb-2 text-xs text-text-2">
                    This group matches no official indicator by name. Here is
                    what made it stand out, in plain words:
                  </p>
                  <ul className="grid list-disc gap-1.5 pl-4 text-xs leading-relaxed text-text-1">
                    {reason.points.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                  <p className="mt-2 text-[11px] leading-snug text-text-2">
                    {reason.caveat}
                  </p>
                </div>
              ) : (
                <p className="py-6 text-center text-xs text-text-2">
                  No indicator citations for this alert.
                </p>
              )
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
                  <span className="w-36 shrink-0 text-text-2">
                    {EVIDENCE_LABEL[k] ?? k.replace(/_/g, " ")}
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
                  each fact is labelled with where it came from. If a fact is
                  missing, it is genuinely missing — we never fill in a guess
                </p>
              )}
            </div>
          </Card>

          {/* fidelity + members */}
          <Card title="How solid is this?" hue={UI_HUES.violet} delay={3}>
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
                  We check this by running the case twice more: once showing the
                  computer only this evidence, and once hiding it. Then we see
                  whether the warning still comes out the same. For one case the
                  answer is a plain yes or no, not a score.
                </p>
              </div>
            ) : (
              <p className="mb-3 text-xs text-text-2">
                This kind of model cannot show which links it used. The pattern rules and
                the standard checks carry the evidence here instead.
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
              For the technical team: every raw value behind this case
              {unknownKeys.length > 0 ? ` (incl. ${unknownKeys.join(", ")})` : ""}
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
