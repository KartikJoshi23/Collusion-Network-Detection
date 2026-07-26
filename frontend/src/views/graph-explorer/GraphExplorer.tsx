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
    // V4: context/edge ink is NEUTRAL grey — on a black canvas the old
    // blue-grey (#46536e / #2b3450) made the whole graph read as a blue mesh,
    // and it competed with --accent, which is the one hue that means something
    // here (a lit edge). Flagged members stay coral, lit edges stay accent.
    member: v("--risk-high", "#ff5a5f"),
    context: "#4a4d55",
    edge: "#2e3036",
    edgeLit: v("--accent", "#22d3ee"),
    label: v("--text-1", "#a7a9ad"),
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
  // Rings grow with member/context count so a 100-member alert no longer
  // overlaps on a unit circle (the "cluttered" report); nodes shrink as the
  // graph gets busy. Sigma fits the camera to the bounds, so larger radii =
  // wider angular spacing on screen.
  const big = data.nodes.length > 40;
  const memberR = 1 + members.length / 14;
  const contextR = memberR + 2 + context.length / 40;
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
        size: memberRing ? (big ? 6 : 9) : big ? 3 : 4,
        color: memberRing ? c.member : c.context,
        label: n.node_id,
        zIndex: memberRing ? 2 : 1,
      });
    });
  place(members, memberR, true);
  place(context, contextR, false);

  // Per-edge reveal time in [0,1] for the replay. When edge timestamps vary
  // we animate in true time order; when they DON'T (Elliptic tx-graph edges
  // all live in a single time step, so span.min === span.max) we fall back to
  // sequence order — otherwise the scrubber lit everything at once and looked
  // like it "did nothing / ended instantly".
  const ts = data.edges
    .map((e) => e.timestamp)
    .filter((t): t is number => t != null);
  const tMin = ts.length ? Math.min(...ts) : 0;
  const tMax = ts.length ? Math.max(...ts) : 0;
  const timeVaries = tMax > tMin;
  const denom = Math.max(data.edges.length - 1, 1);
  data.edges.forEach((e, i) => {
    if (!g.hasNode(e.src) || !g.hasNode(e.dst)) return;
    const rt =
      timeVaries && e.timestamp != null
        ? (e.timestamp - tMin) / (tMax - tMin)
        : i / denom;
    g.addEdge(e.src, e.dst, {
      // amount-scaled width where amounts exist; uniform otherwise
      size:
        e.amount && maxAmount > 0
          ? 1 + 2.5 * Math.sqrt(e.amount / maxAmount)
          : 1,
      color: c.edge,
      type: "arrow",
      rt,
    });
  });
  return g;
}

export function GraphExplorer() {
  const dataset = useConsole((s) => s.dataset);
  const alertId = useConsole((s) => s.selectedAlertId);
  const setView = useConsole((s) => s.setView);
  // Context depth. The report used to claim "clicking a dot expands its
  // neighbours" — it never did, and the API is alert-scoped rather than
  // node-scoped, so per-dot expansion does not exist. What DOES exist is this:
  // the server can widen the whole picture by one more hop. Measured on
  // elliptic_pp alert 2: 1 hop = 50 dots / 49 lines, 2 hops = 62 / 62.
  const [hops, setHops] = useState<1 | 2>(1);
  const { data, isLoading, isError, error } = useSubgraph(dataset, alertId, hops);
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const playheadRef = useRef(1); // 0..1 through the time span; 1 = everything
  const tweenRef = useRef<gsap.core.Tween | null>(null);
  const [progress, setProgress] = useState(1);
  const [playing, setPlaying] = useState(false);

  // Replay descriptor: whether there is anything to replay, and whether edge
  // timestamps actually vary (they don't on single-time-window subgraphs).
  const timeline = useMemo(() => {
    const ts = (data?.edges ?? [])
      .map((e) => e.timestamp)
      .filter((t): t is number => t !== null);
    const min = ts.length ? Math.min(...ts) : 0;
    const max = ts.length ? Math.max(...ts) : 0;
    return {
      hasEdges: (data?.edges?.length ?? 0) > 0,
      varies: max > min,
      min,
      max,
    };
  }, [data]);

  useEffect(() => {
    if (!data || !containerRef.current) return;
    const g = layout(data);
    const c = tokens();
    // thin the labels out on busy graphs so 100 members don't smear together
    const busy = data.nodes.length > 40;
    const renderer = new Sigma(g, containerRef.current, {
      defaultEdgeType: "arrow",
      labelColor: { color: c.label },
      labelFont: "JetBrains Mono Variable, ui-monospace, monospace",
      labelSize: 10,
      labelDensity: busy ? 0.05 : 0.4,
      labelRenderedSizeThreshold: busy ? 12 : 6,
      renderLabels: true,
      edgeReducer: (_edge, attrs) => {
        const t = playheadRef.current;
        if (t >= 1) return attrs;
        const rt = (attrs.rt as number) ?? 0;
        const lit = rt <= t;
        return {
          ...attrs,
          color: lit ? c.edgeLit : "#1c1e22",
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
  }, [data]);

  const seek = (t: number) => {
    playheadRef.current = t;
    setProgress(t);
    sigmaRef.current?.refresh();
  };

  const play = () => {
    if (!timeline.hasEdges) return;
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
            showing only part of the network, to keep it readable
          </span>
        )}
        {/* context depth — the honest replacement for "click a dot to expand" */}
        <div className="ml-auto flex items-center gap-1">
          <span className="text-xs text-text-2">Context</span>
          {([1, 2] as const).map((h) => (
            <button
              key={h}
              onClick={() => setHops(h)}
              title={
                h === 1
                  ? "Just the flagged group and who they deal with directly."
                  : "Widen the picture by one more step out — shows who those neighbours deal with too."
              }
              className="chip-bloom rounded-md px-2 py-0.5 text-[11px] transition-colors"
              style={{
                color: hops === h ? "var(--text-0)" : "var(--text-2)",
                background:
                  hops === h
                    ? "color-mix(in srgb, var(--accent) 18%, transparent)"
                    : "transparent",
                boxShadow:
                  hops === h
                    ? "inset 0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent)"
                    : "inset 0 0 0 1px var(--hairline)",
              }}
            >
              {h === 1 ? "1 step out" : "2 steps out"}
            </button>
          ))}
        </div>
        <button
          onClick={() => setView("case")}
          className="btn-sheen rounded-md px-3 py-1 text-xs"
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
                style={{ background: "#4a4d55" }}
              />
              context
            </span>
          </div>
        )}
      </div>

      {/* replay scrubber — by timestamp when they vary, else in sequence order
          (single-time-window subgraphs like Elliptic tx-graphs) */}
      {timeline.hasEdges && (
        <div className="flex items-center gap-3 border-t border-hairline/60 px-4 py-2">
          <button
            onClick={playing ? pause : play}
            className="btn-sheen rounded-md px-2.5 py-1 text-xs"
            title={
              playing
                ? "pause playback"
                : timeline.varies
                  ? "replay the flow in timestamp order"
                  : "all activity in one time window — replay reveals edges in sequence order"
            }
            style={{
              color: "var(--accent)",
              background: "var(--accent-dim)",
              boxShadow:
                "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
            }}
          >
            {playing ? "❚❚" : "▶"} replay {timeline.varies ? "flow" : "order"}
          </button>
          {/* Which of the two modes is running, and WHY it is that one. Before
              this the button just said "replay order" and a first-time viewer
              had no idea a second mode existed, or that the choice is forced
              by the data rather than by a setting. */}
          <span
            className="hidden max-w-[26rem] text-[11px] leading-snug text-text-2 sm:inline"
            title={
              timeline.varies
                ? "The connections in this group carry different dates, so the replay follows real time."
                : "Every connection in this group is stamped with the same time step, so there is no time order to follow. Rather than invent dates, we reveal them in the order they are recorded and say so."
            }
          >
            {timeline.varies
              ? "by time — these connections carry different dates"
              : "in order — every connection here shares one time step, so there is no time order to show"}
          </span>
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
            aria-label="replay position"
          />
          <span className="mono w-44 text-right text-xs text-text-2">
            {timeline.varies
              ? progress >= 1
                ? `full window ${timeline.min} – ${timeline.max}`
                : `t ≤ ${Math.round(timeline.min + progress * (timeline.max - timeline.min))}`
              : progress >= 1
                ? `all edges${timeline.min ? ` · window ${timeline.min}` : ""}`
                : `${Math.round(progress * 100)}% revealed`}
          </span>
        </div>
      )}
    </Glass>
  );
}
