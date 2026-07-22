// Investigator Copilot dock (§5.3 view 7, §7 step 27b): a collapsible
// right-hand panel available on every view — message bubbles, LIVE agent
// trace (SSE events as tools fire), confidence + grounding badges, evidence
// panel, and the AI-generated label + screening caveat on every response
// (all copied from the backend payload, never re-derived). Not-configured
// machines get an honest setup note (health.configured=false).
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import {
  copilotHealth,
  streamChat,
  type CopilotHealth,
  type CopilotPayload,
} from "../../api/copilot";
import { UI_HUES } from "../../lib/palette";
import { useConsole } from "../../state/console";
import { CopilotMark } from "./CopilotMark";

interface Turn {
  question: string;
  seed?: string;
  liveTrace: string[];
  payload?: CopilotPayload;
  error?: string;
}

export function CopilotDock() {
  const open = useConsole((s) => s.copilotOpen);
  const seed = useConsole((s) => s.copilotSeed);
  const toggle = useConsole((s) => s.toggleCopilot);
  const clearSeed = useConsole((s) => s.clearCopilotSeed);
  const [health, setHealth] = useState<CopilotHealth | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && health === null)
      copilotHealth()
        .then(setHealth)
        .catch(() =>
          setHealth({ configured: false, provider: "?", model: "?", caveat: "" }),
        );
  }, [open, health]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns]);

  const send = async () => {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { question, seed, liveTrace: [] }]);
    try {
      for await (const ev of streamChat(question, seed)) {
        if (ev.event === "trace") {
          const step = ev.data.step;
          setTurns((t) =>
            t.map((turn, i) =>
              i === t.length - 1
                ? { ...turn, liveTrace: [...turn.liveTrace, step] }
                : turn,
            ),
          );
        } else if (ev.event === "final") {
          const payload = ev.data;
          setTurns((t) =>
            t.map((turn, i) => (i === t.length - 1 ? { ...turn, payload } : turn)),
          );
        } else {
          const detail = ev.data.detail;
          setTurns((t) =>
            t.map((turn, i) => (i === t.length - 1 ? { ...turn, error: detail } : turn)),
          );
        }
      }
    } catch (e) {
      setTurns((t) =>
        t.map((turn, i) =>
          i === t.length - 1 ? { ...turn, error: (e as Error).message } : turn,
        ),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ x: 40, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 40, opacity: 0 }}
          transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          className="glass glass-neon z-20 m-2 ml-0 flex w-96 shrink-0 flex-col overflow-hidden"
          style={{ "--panel-hue": UI_HUES.magenta } as React.CSSProperties}
          aria-label="Investigator Copilot"
        >
          <div className="flex items-center gap-2 border-b border-hairline/60 px-3 py-2.5">
            <span
              className="grid h-7 w-7 place-items-center rounded-md"
              style={{
                background: `color-mix(in srgb, ${UI_HUES.magenta} 12%, transparent)`,
                boxShadow: `0 0 16px -4px ${UI_HUES.magenta}`,
              }}
            >
              <CopilotMark size={19} active />
            </span>
            <div className="min-w-0">
              <div className="display text-sm font-semibold leading-tight">
                Investigator <span className="text-grad">Copilot</span>
              </div>
              <div className="mono truncate text-[10px] text-text-2">
                {health
                  ? health.configured
                    ? health.model
                    : "not configured on this machine"
                  : "…"}
              </div>
            </div>
            <button
              onClick={toggle}
              className="btn-sheen ml-auto rounded px-2 py-0.5 text-xs text-text-2 hover:text-text-0"
              aria-label="close copilot"
            >
              ✕
            </button>
          </div>

          {seed && (
            <div
              className="mono flex items-center gap-1.5 border-b border-hairline/40 px-3 py-1.5 text-[10px]"
              style={{ color: UI_HUES.amber }}
            >
              <span className="min-w-0 truncate">⌖ context: {seed}</span>
              <button
                onClick={clearSeed}
                title="clear the alert context (audit: stale seeds outlive dataset switches)"
                className="ml-auto shrink-0 rounded px-1 text-text-2 hover:text-text-0"
                aria-label="clear copilot context"
              >
                ✕
              </button>
            </div>
          )}

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto p-3">
            {health && !health.configured && (
              <div className="rounded-md p-3 text-xs leading-relaxed text-text-1"
                style={{ background: "var(--risk-med-dim)" }}
              >
                No LLM key on this machine. Add <span className="mono">NVIDIA_API_KEY</span>{" "}
                (an <span className="mono">nvapi-…</span> key from build.nvidia.com) to the
                repo-root <span className="mono">.env</span> and restart{" "}
                <span className="mono">collusiongraph serve</span>.
              </div>
            )}
            {turns.length === 0 && health?.configured && (
              <div className="p-3 text-center text-xs text-text-2">
                Ask about the served queues — every answer is tool-grounded and
                carries its evidence.
              </div>
            )}
            {turns.map((turn, i) => (
              <TurnBlock key={i} turn={turn} streaming={busy && i === turns.length - 1} />
            ))}
          </div>

          <div className="border-t border-hairline/60 p-2.5">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void send();
                }}
                placeholder={seed ? "Ask about this alert…" : "Ask the Copilot…"}
                disabled={busy}
                className="mono min-w-0 flex-1 rounded-md px-2.5 py-1.5 text-xs text-text-0 outline-none"
                style={{
                  background: "var(--bg-2)",
                  boxShadow: "inset 0 0 0 1px var(--hairline)",
                }}
              />
              <button
                onClick={() => void send()}
                disabled={busy || !input.trim()}
                className="btn-sheen rounded-md px-3 py-1.5 text-xs disabled:opacity-40"
                style={{
                  color: UI_HUES.magenta,
                  background: `color-mix(in srgb, ${UI_HUES.magenta} 14%, transparent)`,
                  boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${UI_HUES.magenta} 35%, transparent)`,
                }}
              >
                {busy ? "…" : "Ask"}
              </button>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function TurnBlock({ turn, streaming }: { turn: Turn; streaming: boolean }) {
  const p = turn.payload;
  return (
    <div className="mb-3">
      {/* user bubble */}
      <div className="mb-1.5 flex justify-end">
        <div
          className="max-w-[85%] rounded-lg rounded-br-sm px-2.5 py-1.5 text-xs text-text-0"
          style={{ background: "var(--accent-dim)" }}
        >
          {turn.question}
        </div>
      </div>

      {/* live agent trace — §5.3: the timeline streams as tools fire */}
      {(turn.liveTrace.length > 0 || streaming) && !p && (
        <div className="mb-1.5 rounded-md p-2" style={{ background: "var(--bg-2)" }}>
          <div className="mb-1 text-[10px] uppercase tracking-wide text-text-2">
            agent trace {streaming && <span className="animate-pulse">●</span>}
          </div>
          {turn.liveTrace.map((step, i) => (
            <div key={i} className="mono truncate text-[10px] text-text-1">
              → {step}
            </div>
          ))}
        </div>
      )}

      {turn.error && (
        <div
          className="rounded-md border-l-2 p-2 text-xs"
          style={{
            borderColor: "var(--risk-high)",
            background: "var(--risk-high-dim)",
            color: "var(--text-1)",
          }}
        >
          {turn.error}
        </div>
      )}

      {p && (
        <div className="rounded-lg rounded-bl-sm p-2.5" style={{ background: "var(--bg-2)" }}>
          <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
            <Badge
              label={`confidence ${p.confidence.toFixed(1)}`}
              hue={p.confidence >= 0.5 ? UI_HUES.teal : UI_HUES.amber}
              title="from the deterministic gates — numbers + typology grounding"
            />
            {!p.numbers_grounded && (
              <Badge label="numbers unverified" hue={UI_HUES.amber} title="a number in the answer was not found in tool evidence" />
            )}
            {!p.corpus_grounded && (
              <Badge label="typology ungrounded" hue={UI_HUES.amber} title="red-flag terms discussed without consulting the FATF/OECD corpus" />
            )}
            {p.guard_rewrites.length > 0 && (
              <Badge label={`guard ×${p.guard_rewrites.length}`} hue={UI_HUES.coral} title="guilt-language guard rewrote phrasing (§4.6)" />
            )}
          </div>
          <div className="whitespace-pre-wrap text-xs leading-relaxed text-text-0">
            {p.answer}
          </div>
          {p.evidence.length > 0 && (
            <details className="mt-2 rounded bg-bg-1/70 p-1.5">
              <summary className="cursor-pointer text-[10px] uppercase tracking-wide text-text-2 hover:text-accent">
                evidence — {p.evidence.length} tool call{p.evidence.length > 1 ? "s" : ""}
              </summary>
              {p.evidence.map((e, i) => (
                <div key={i} className="mt-1.5 border-t border-hairline/40 pt-1.5">
                  <div className="mono text-[10px]" style={{ color: UI_HUES.cyan }}>
                    {e.tool}({e.args})
                  </div>
                  <pre className="mono mt-0.5 max-h-32 overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-text-1">
                    {e.result}
                  </pre>
                </div>
              ))}
            </details>
          )}
          <div className="mt-2 flex items-start gap-1.5 border-t border-hairline/40 pt-1.5 text-[10px] text-text-2">
            <span
              className="rounded px-1 py-px font-medium"
              style={{
                color: UI_HUES.violet,
                background: `color-mix(in srgb, ${UI_HUES.violet} 14%, transparent)`,
              }}
            >
              AI-generated
            </span>
            <span className="min-w-0">{p.caveat}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function Badge({ label, hue, title }: { label: string; hue: string; title: string }) {
  return (
    <span
      className="mono rounded px-1.5 py-0.5 text-[10px]"
      title={title}
      style={{
        color: hue,
        background: `color-mix(in srgb, ${hue} 13%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${hue} 30%, transparent)`,
      }}
    >
      {label}
    </span>
  );
}
