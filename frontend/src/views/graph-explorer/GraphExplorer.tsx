import gsap from "gsap";
import Graph from "graphology";
import Sigma from "sigma";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSubgraph } from "../../api/hooks";
import type { SubgraphResponse } from "../../api/types";
import { Glass } from "../../components/ui/Glass";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { useConsole } from "../../state/console";

// §5.3 view 3, V2 additions: GSAP temporal scrubber replaying the money
// flow / award sequence over REAL edge timestamps (edges appear as the
// playhead passes their timestamp; nodes light with their first edge),
// amount-scaled edge widths where amounts exist (§4.3 D1 — scaling simply
// stays uniform on datasets without amounts).
function tokens() {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string, fallback: string) =>
    css.getPropertyValue(name).trim() || fallback;
  return {
    member: v("--risk-high", "#ff5a5f"),
    context: "#46536e",
    edge: "#2b3450",
    edgeLit: v("--accent", "#22d3ee"),
    label: v("--text-1", "#9aa7bf"),
  };
}

function layout(data: SubgraphResponse): Graph {
  const c = tokens();
  const g = new Graph({ multi: true, type: "directed" });
  const members = data.nodes.filter((n) => n.is_member);
  const context = data.nodes.filter((n) => !n.is_member);
  const maxAmount = Math.max(
    ...data.edges.map((e) => e.amount ?? 0),
    0,
  );
  const place = (
    list: typeof data.nodes,
    radius: number,
    memberRing: boolean,
  ) =>
    list.forEach((n, i) => {
      const theta = (2 * Math.PI * i) / Math.max(list.length, 1);
      g.addNode(n.node_id, {
        x: radius * Math.cos(theta),
        y: radius * Math.sin(theta),
        size: memberRing ? 9 : 4,
        color: memberRing ? c.member : c.context,
        label: n.node_id,
        zIndex: memberRing ? 2 : 1,
      });
    });
  place(members, 1, true);
  place(context, 3, false);
  for (const e of data.edges) {
    if (g.hasNode(e.src) && g.hasNode(e.dst)) {
      g.addEdge(e.src, e.dst, {
        // amount-scaled width where amounts exist; uniform otherwise
        size:
          e.amount && maxAmount > 0
            ? 1 + 2.5 * Math.sqrt(e.amount / maxAmount)
            : 1,
        color: c.edge,
        type: "arrow",
        ts: e.timestamp,
      });
    }
  }
  return g;
}

export function GraphExplorer() {
  const dataset = useConsole((s) => s.dataset);
  const alertId = useConsole((s) => s.selectedAlertId);
  const setView = useConsole((s) => s.setView);
  const { data, isLoading, isError, error } = useSubgraph(dataset, alertId, 1);
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const playheadRef = useRef(1); // 0..1 through the time span; 1 = everything
  const tweenRef = useRef<gsap.core.Tween | null>(null);
  const [progress, setProgress] = useState(1);
  const [playing, setPlaying] = useState(false);

  const span = useMemo(() => {
    const ts = (data?.edges ?? [])
      .map((e) => e.timestamp)
      .filter((t): t is number => t !== null);
    return ts.length
      ? { min: Math.min(...ts), max: Math.max(...ts), n: ts.length }
      : null;
  }, [data]);

  useEffect(() => {
    if (!data || !containerRef.current) return;
    const g = layout(data);
    const c = tokens();
    const renderer = new Sigma(g, containerRef.current, {
      defaultEdgeType: "arrow",
      labelColor: { color: c.label },
      labelFont: "JetBrains Mono Variable, ui-monospace, monospace",
      labelSize: 10,
      labelDensity: 0.4,
      renderLabels: true,
      edgeReducer: (_edge, attrs) => {
        const t = playheadRef.current;
        if (t >= 1 || !span || attrs.ts === null || attrs.ts === undefined)
          return attrs;
        const cutoff = span.min + t * (span.max - span.min);
        const lit = (attrs.ts as number) <= cutoff;
        return {
          ...attrs,
          color: lit ? c.edgeLit : "#1a2138",
          size: lit ? (attrs.size as number) + 0.5 : 0.5,
        };
      },
    });
    sigmaRef.current = renderer;
    return () => {
      tweenRef.current?.kill();
      renderer.kill();
      sigmaRef.current = null;
    };
  }, [data, span]);

  const seek = (t: number) => {
    playheadRef.current = t;
    setProgress(t);
    sigmaRef.current?.refresh();
  };

  const play = () => {
    if (!span) return;
    tweenRef.current?.kill();
    setPlaying(true);
    const proxy = { t: playheadRef.current >= 1 ? 0 : playheadRef.current };
    tweenRef.current = gsap.to(proxy, {
      t: 1,
      duration: 6,
      ease: "none",
      onUpdate: () => seek(proxy.t),
      onComplete: () => setPlaying(false),
    });
  };

  const pause = () => {
    tweenRef.current?.kill();
    setPlaying(false);
  };

  if (!alertId)
    return (
      <Empty
        title="No alert selected"
        hint="Pick an alert from the queue to explore its subgraph."
      >
        <button
          onClick={() => setView("queue")}
          className="btn-sheen mt-1 rounded-md px-3 py-1 text-xs text-text-1 hover:text-accent"
          style={{
            background: "var(--glass-fill-lo)",
            boxShadow: "inset 0 0 0 1px var(--hairline)",
          }}
        >
          Go to Alert Queue
        </button>
      </Empty>
    );

  return (
    <Glass className="flex h-full flex-col overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-hairline/60 px-4 py-2.5">
        <h2 className="display text-sm font-semibold">Graph Explorer</h2>
        <span className="mono text-xs text-text-2">{alertId}</span>
        {data?.truncated && (
          <span className="rounded bg-risk-med/15 px-1.5 py-0.5 text-xs text-risk-med">
            view truncated at node cap
          </span>
        )}
        <button
          onClick={() => setView("case")}
          className="btn-sheen ml-auto rounded-md px-3 py-1 text-xs"
          style={{
            color: "var(--accent)",
            background: "var(--accent-dim)",
            boxShadow:
              "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
          }}
        >
          Evidence dossier →
        </button>
      </div>

      <div className="relative min-h-0 flex-1">
        {isLoading && <Loading label="Windowing subgraph…" />}
        {isError && (
          <ErrorState
            message="Could not load subgraph"
            detail={(error as Error)?.message}
          />
        )}
        <div ref={containerRef} className="absolute inset-0" />
        {data && (
          <div className="pointer-events-none absolute bottom-2 left-3 flex items-center gap-3 text-xs text-text-2">
            <span className="mono">
              {data.nodes.length} nodes · {data.edges.length} edges
            </span>
            <span className="inline-flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{
                  background: "var(--risk-high)",
                  boxShadow: "0 0 6px var(--risk-high)",
                }}
              />
              flagged member
            </span>
            <span className="inline-flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: "#46536e" }}
              />
              context
            </span>
          </div>
        )}
      </div>

      {/* temporal playback scrubber (V2 §3.4) — real edge timestamps */}
      {span && (
        <div className="flex items-center gap-3 border-t border-hairline/60 px-4 py-2">
          <button
            onClick={playing ? pause : play}
            className="btn-sheen rounded-md px-2.5 py-1 text-xs"
            title={
              playing
                ? "pause playback"
                : "replay the flow in timestamp order"
            }
            style={{
              color: "var(--accent)",
              background: "var(--accent-dim)",
              boxShadow:
                "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
            }}
          >
            {playing ? "❚❚" : "▶"} replay flow
          </button>
          <input
            type="range"
            className="budget min-w-0 flex-1 cursor-pointer"
            min={0}
            max={1000}
            value={Math.round(progress * 1000)}
            onChange={(e) => {
              pause();
              seek(Number(e.target.value) / 1000);
            }}
            style={
              { "--fill": `${progress * 100}%` } as React.CSSProperties
            }
            aria-label="temporal playback position"
          />
          <span className="mono w-40 text-right text-xs text-text-2">
            {progress >= 1
              ? `full window ${span.min} – ${span.max}`
              : `t ≤ ${Math.round(span.min + progress * (span.max - span.min))}`}
          </span>
        </div>
      )}
    </Glass>
  );
}
