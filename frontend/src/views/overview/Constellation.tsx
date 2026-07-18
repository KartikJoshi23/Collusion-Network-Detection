// Alert constellation — the Overview hero mini-map (§5.3 view 1, V2 §3.5.1).
// Each node IS a real ranked alert (size = community members, color = risk
// band, coral glow on the flagged band); layout is a deterministic
// golden-angle spiral by rank (presentation only — the DATA is real, and the
// caption says the layout isn't). Cursor spotlight follows the pointer
// (V2 §3.3); clicking a node opens its subgraph.
import { useRef } from "react";
import type { AlertRow } from "../../api/types";
import { riskBand } from "../../lib/format";
import { STATUS } from "../../lib/palette";
import { useConsole } from "../../state/console";

const GOLDEN = 2.399963; // golden angle, radians

export function Constellation({ alerts }: { alerts: AlertRow[] }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const selectAlert = useConsole((s) => s.selectAlert);
  const setView = useConsole((s) => s.setView);

  const W = 640;
  const H = 320;
  const cx = W / 2;
  const cy = H / 2;
  const maxMembers = Math.max(...alerts.map((a) => a.n_members), 1);

  const nodes = alerts.map((a, i) => {
    const r = 24 + 130 * Math.sqrt(i / Math.max(alerts.length - 1, 1));
    const th = i * GOLDEN;
    return {
      alert: a,
      x: cx + r * Math.cos(th) * 1.55,
      y: cy + r * Math.sin(th) * 0.82,
      size: 5 + 11 * Math.sqrt(a.n_members / maxMembers),
      color: STATUS[bandKey(a.risk_score)],
      hot: riskBand(a.risk_score) === "high",
    };
  });

  const spotlight = (e: React.MouseEvent) => {
    const el = boxRef.current;
    if (!el) return;
    const box = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - box.left}px`);
    el.style.setProperty("--my", `${e.clientY - box.top}px`);
  };

  return (
    <div
      ref={boxRef}
      onMouseMove={spotlight}
      className="relative overflow-hidden rounded-[inherit]"
    >
      {/* cursor-following spotlight */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 transition-opacity"
        style={{
          background:
            "radial-gradient(260px at var(--mx, 50%) var(--my, 40%), color-mix(in srgb, var(--accent) 14%, transparent), transparent 70%)",
        }}
      />
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {/* faint links from each node to its predecessor — queue order made
            visible; not graph edges */}
        {nodes.slice(1).map((n, i) => (
          <line
            key={n.alert.alert_id}
            x1={nodes[i].x}
            y1={nodes[i].y}
            x2={n.x}
            y2={n.y}
            stroke="var(--hairline)"
            strokeWidth={0.7}
            opacity={0.5}
          />
        ))}
        {nodes.map((n) => (
          <g
            key={n.alert.alert_id}
            className="cursor-pointer"
            onClick={() => {
              selectAlert(n.alert.alert_id);
              setView("explorer");
            }}
          >
            <title>
              {`#${n.alert.rank} · p=${n.alert.risk_score.toFixed(3)} · ${n.alert.n_members} members${n.alert.motif_type ? ` · ${n.alert.motif_type}` : ""} — click to open subgraph`}
            </title>
            {n.hot && (
              <circle
                cx={n.x}
                cy={n.y}
                r={n.size + 6}
                fill="none"
                stroke={n.color}
                strokeWidth={1}
                opacity={0.35}
                className="risk-halo"
              />
            )}
            <circle
              cx={n.x}
              cy={n.y}
              r={n.size}
              fill={n.color}
              opacity={0.85}
              style={{
                filter: n.hot ? `drop-shadow(0 0 8px ${n.color})` : undefined,
                transition: "r 0.15s ease",
              }}
            />
            <text
              x={n.x}
              y={n.y + 3}
              textAnchor="middle"
              fontSize={n.size > 10 ? 9 : 7}
              fill="var(--bg-0)"
              fontFamily="var(--font-mono)"
              fontWeight={600}
            >
              {n.alert.rank}
            </text>
          </g>
        ))}
      </svg>
      <div className="pointer-events-none absolute bottom-2 left-3 flex items-center gap-3 text-[10px] text-text-2">
        <span className="flex items-center gap-1">
          <Dot c={STATUS.flagged} /> high band
        </span>
        <span className="flex items-center gap-1">
          <Dot c={STATUS.medium} /> medium
        </span>
        <span className="flex items-center gap-1">
          <Dot c={STATUS.benign} /> low
        </span>
        <span>size = members · layout schematic, ranks real</span>
      </div>
    </div>
  );
}

function bandKey(score: number): keyof typeof STATUS {
  const b = riskBand(score);
  return b === "high" ? "flagged" : b === "med" ? "medium" : "benign";
}

function Dot({ c }: { c: string }) {
  return (
    <span
      className="inline-block h-2 w-2 rounded-full"
      style={{ background: c }}
    />
  );
}
