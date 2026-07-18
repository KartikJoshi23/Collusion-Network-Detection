// Hand-rolled SVG charts (§5.1 allows D3-direct/hand-rolled; visx deferred).
// Dataviz specs applied: thin marks with rounded data-ends anchored to the
// baseline, 2px lines, ≥8px markers, recessive grid, text in text tokens,
// selective direct labels, per-mark hover tooltips, single axis.
import type { KPoint, StepPoint } from "../../lib/metricsExtract";
import { ChartTip, useChartTip } from "./ChartCard";

const W = 560;
const H = 200;
const PAD = { l: 44, r: 12, t: 14, b: 26 };

function yScale(v: number, max: number) {
  return PAD.t + (1 - v / max) * (H - PAD.t - PAD.b);
}

function Grid({ max, fmt }: { max: number; fmt: (v: number) => string }) {
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  return (
    <g>
      {ticks.map((t) => (
        <g key={t}>
          <line
            x1={PAD.l}
            x2={W - PAD.r}
            y1={yScale(t, max)}
            y2={yScale(t, max)}
            stroke="var(--hairline)"
            strokeWidth={t === 0 ? 1 : 0.5}
            opacity={t === 0 ? 0.9 : 0.45}
          />
          <text
            x={PAD.l - 6}
            y={yScale(t, max) + 3}
            textAnchor="end"
            fontSize={9}
            fill="var(--text-2)"
            fontFamily="var(--font-mono)"
          >
            {fmt(t)}
          </text>
        </g>
      ))}
    </g>
  );
}

/** Per-time-step AUC-PR bars + dashed per-step prevalence baseline ticks —
    the temporal-shift figure (the step-43 crater is the finding). */
export function StepBarChart({
  points,
  color,
}: {
  points: StepPoint[];
  color: string;
}) {
  const { tip, setTip } = useChartTip();
  if (points.length === 0) return null;
  const max = 1;
  const span = W - PAD.l - PAD.r;
  const bw = Math.min(22, (span / points.length) * 0.72);
  const step = span / points.length;
  const y0 = yScale(0, max);

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <Grid max={max} fmt={(v) => v.toFixed(2)} />
        {points.map((p, i) => {
          const x = PAD.l + i * step + step / 2;
          const y = yScale(p.aucPr, max);
          return (
            <g
              key={p.step}
              onMouseEnter={(e) => {
                const box = (
                  e.currentTarget.ownerSVGElement as SVGSVGElement
                ).getBoundingClientRect();
                setTip({
                  x: ((x / W) * box.width) | 0,
                  y: ((y / H) * box.height) | 0,
                  text: `step ${p.step}\nAUC-PR ${p.aucPr.toFixed(3)}${
                    p.prevalence !== null
                      ? `\nprevalence ${p.prevalence.toFixed(3)}`
                      : ""
                  }`,
                });
              }}
              onMouseLeave={() => setTip(null)}
            >
              {/* generous hit target behind the thin mark */}
              <rect
                x={x - step / 2}
                y={PAD.t}
                width={step}
                height={H - PAD.t - PAD.b}
                fill="transparent"
              />
              <rect
                x={x - bw / 2}
                y={y}
                width={bw}
                height={Math.max(y0 - y, 1)}
                rx={2}
                fill={color}
                opacity={0.9}
              />
              {p.prevalence !== null && (
                <line
                  x1={x - bw / 2 - 2}
                  x2={x + bw / 2 + 2}
                  y1={yScale(p.prevalence, max)}
                  y2={yScale(p.prevalence, max)}
                  stroke="var(--text-1)"
                  strokeWidth={1.2}
                  strokeDasharray="3 2"
                />
              )}
              <text
                x={x}
                y={H - PAD.b + 12}
                textAnchor="middle"
                fontSize={8.5}
                fill="var(--text-2)"
                fontFamily="var(--font-mono)"
              >
                {p.step}
              </text>
            </g>
          );
        })}
      </svg>
      <ChartTip tip={tip} />
      <div className="mt-1 flex items-center gap-3 text-[10px] text-text-2">
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-sm"
            style={{ background: color }}
          />
          AUC-PR per step
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block w-3 border-t border-dashed"
            style={{ borderColor: "var(--text-1)" }}
          />
          prevalence baseline
        </span>
      </div>
    </div>
  );
}

/** Measured value-at-k line with ≥8px markers and the active budget marker.
    Points are the run's published budgets — never interpolated between. */
export function AtKChart({
  points,
  color,
  budget,
  label,
}: {
  points: KPoint[];
  color: string;
  budget?: number;
  label: string;
}) {
  const { tip, setTip } = useChartTip();
  if (points.length === 0) return null;
  const max = 1;
  const kMax = points[points.length - 1].k;
  const kMin = points[0].k;
  const xScale = (k: number) =>
    PAD.l +
    (kMax === kMin ? 0.5 : (k - kMin) / (kMax - kMin)) * (W - PAD.l - PAD.r);

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${xScale(p.k)} ${yScale(p.value, max)}`)
    .join(" ");

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <Grid max={max} fmt={(v) => v.toFixed(2)} />
        {budget !== undefined && budget >= kMin && budget <= kMax && (
          <line
            x1={xScale(budget)}
            x2={xScale(budget)}
            y1={PAD.t}
            y2={H - PAD.b}
            stroke="var(--hue-amber)"
            strokeWidth={1}
            strokeDasharray="4 3"
            opacity={0.8}
          />
        )}
        <path d={path} fill="none" stroke={color} strokeWidth={2} />
        {points.map((p) => (
          <g
            key={p.k}
            onMouseEnter={(e) => {
              const box = (
                e.currentTarget.ownerSVGElement as SVGSVGElement
              ).getBoundingClientRect();
              setTip({
                x: ((xScale(p.k) / W) * box.width) | 0,
                y: ((yScale(p.value, max) / H) * box.height) | 0,
                text: `${label}@${p.k} = ${p.value.toFixed(3)}`,
              });
            }}
            onMouseLeave={() => setTip(null)}
          >
            <circle cx={xScale(p.k)} cy={yScale(p.value, max)} r={9} fill="transparent" />
            <circle
              cx={xScale(p.k)}
              cy={yScale(p.value, max)}
              r={4}
              fill={color}
              stroke="var(--bg-0)"
              strokeWidth={2}
            />
            <text
              x={xScale(p.k)}
              y={H - PAD.b + 12}
              textAnchor="middle"
              fontSize={9}
              fill="var(--text-2)"
              fontFamily="var(--font-mono)"
            >
              {p.k}
            </text>
            <text
              x={xScale(p.k)}
              y={yScale(p.value, max) - 9}
              textAnchor="middle"
              fontSize={9}
              fill="var(--text-1)"
              fontFamily="var(--font-mono)"
            >
              {p.value.toFixed(2)}
            </text>
          </g>
        ))}
      </svg>
      <ChartTip tip={tip} />
      {budget !== undefined && (
        <div className="mt-1 flex items-center gap-1 text-[10px] text-text-2">
          <span
            className="inline-block w-3 border-t border-dashed"
            style={{ borderColor: "var(--hue-amber)" }}
          />
          current budget k = {budget}
        </div>
      )}
    </div>
  );
}
