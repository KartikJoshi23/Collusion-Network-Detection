import Graph from "graphology";
import Sigma from "sigma";
import { useEffect, useRef } from "react";
import { useSubgraph } from "../../api/hooks";
import type { SubgraphResponse } from "../../api/types";
import { Empty, ErrorState, Loading } from "../../components/ui/States";
import { useConsole } from "../../state/console";

// Deterministic radial layout: members on an inner ring, context nodes on an
// outer ring (server precomputed layouts arrive in Phase 2; this keeps the MVP
// self-contained and reproducible).
function layout(data: SubgraphResponse): Graph {
  const g = new Graph({ multi: true, type: "directed" });
  const members = data.nodes.filter((n) => n.is_member);
  const context = data.nodes.filter((n) => !n.is_member);
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
        color: memberRing ? "#ff5a5f" : "#3a4358",
        label: n.node_id,
        zIndex: memberRing ? 2 : 1,
      });
    });
  place(members, 1, true);
  place(context, 3, false);
  for (const e of data.edges) {
    if (g.hasNode(e.src) && g.hasNode(e.dst)) {
      g.addEdge(e.src, e.dst, {
        size: 1,
        color: "#232c40",
        type: "arrow",
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

  useEffect(() => {
    if (!data || !containerRef.current) return;
    const g = layout(data);
    const renderer = new Sigma(g, containerRef.current, {
      defaultEdgeType: "arrow",
      labelColor: { color: "#9aa7bf" },
      labelSize: 11,
      labelDensity: 0.4,
      renderLabels: true,
    });
    sigmaRef.current = renderer;
    return () => {
      renderer.kill();
      sigmaRef.current = null;
    };
  }, [data]);

  if (!alertId)
    return (
      <Empty
        title="No alert selected"
        hint="Pick an alert from the queue to explore its subgraph."
      >
        <button
          onClick={() => setView("queue")}
          className="mt-1 rounded-md border border-hairline bg-bg-2 px-3 py-1 text-xs text-text-1 hover:bg-bg-3"
        >
          Go to Alert Queue
        </button>
      </Empty>
    );

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-hairline bg-bg-1 px-4 py-2">
        <h2 className="text-sm font-medium">Graph Explorer</h2>
        <span className="mono text-xs text-text-2">{alertId}</span>
        {data?.truncated && (
          <span className="ml-auto rounded bg-risk-med/15 px-1.5 py-0.5 text-xs text-risk-med">
            view truncated at node cap
          </span>
        )}
        <button
          onClick={() => setView("case")}
          className="ml-auto rounded-md border border-hairline bg-bg-2 px-3 py-1 text-xs text-text-1 hover:bg-bg-3"
        >
          Explanation dossier →
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
          <div className="mono pointer-events-none absolute bottom-2 left-3 text-xs text-text-2">
            {data.nodes.length} nodes · {data.edges.length} edges · flagged in
            coral
          </div>
        )}
      </div>
    </div>
  );
}
