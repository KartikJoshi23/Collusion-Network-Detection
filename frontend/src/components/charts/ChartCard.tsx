// Chart shell (§5.3 view 5: charts double as paper figures — SVG/PNG export
// on every chart). Marks follow the dataviz specs: thin marks, recessive
// grid, mono numerals, hover tooltips; series colors come from the validated
// CHART_SERIES tier, never the status colors.
import { useRef, useState } from "react";
import { Glass } from "../ui/Glass";

export function ChartCard({
  title,
  subtitle,
  hue,
  filename,
  children,
}: {
  title: string;
  subtitle?: string;
  hue?: string;
  filename: string;
  children: React.ReactNode;
}) {
  const boxRef = useRef<HTMLDivElement>(null);

  const svgEl = () => boxRef.current?.querySelector("svg") ?? null;

  const exportSvg = () => {
    const svg = svgEl();
    if (!svg) return;
    const blob = new Blob([new XMLSerializer().serializeToString(svg)], {
      type: "image/svg+xml",
    });
    download(URL.createObjectURL(blob), `${filename}.svg`);
  };

  const exportPng = () => {
    const svg = svgEl();
    if (!svg) return;
    const vb = svg.viewBox.baseVal;
    const scale = 3; // print-quality
    const canvas = document.createElement("canvas");
    canvas.width = vb.width * scale;
    canvas.height = vb.height * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const img = new Image();
    const url = URL.createObjectURL(
      new Blob([new XMLSerializer().serializeToString(svg)], {
        type: "image/svg+xml",
      }),
    );
    img.onload = () => {
      ctx.fillStyle = "#0a0e17"; // figures keep the console surface
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob((b) => {
        if (b) download(URL.createObjectURL(b), `${filename}.png`);
      });
    };
    img.src = url;
  };

  return (
    <Glass neon lift hue={hue} className="p-3.5">
      <div className="mb-2 flex items-baseline gap-2">
        <div>
          <div
            className="text-xs font-medium uppercase tracking-wide"
            style={{ color: hue ?? "var(--text-1)" }}
          >
            {title}
          </div>
          {subtitle && (
            <div className="mt-0.5 text-[10px] text-text-2">{subtitle}</div>
          )}
        </div>
        <div className="ml-auto flex gap-1.5">
          <button
            onClick={exportSvg}
            className="btn-sheen rounded px-1.5 py-0.5 text-[10px] text-text-2 hover:text-text-0"
            style={{ boxShadow: "inset 0 0 0 1px var(--hairline)" }}
          >
            SVG
          </button>
          <button
            onClick={exportPng}
            className="btn-sheen rounded px-1.5 py-0.5 text-[10px] text-text-2 hover:text-text-0"
            style={{ boxShadow: "inset 0 0 0 1px var(--hairline)" }}
          >
            PNG
          </button>
        </div>
      </div>
      <div ref={boxRef}>{children}</div>
    </Glass>
  );
}

function download(url: string, name: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** Shared hover tooltip state helper for the SVG charts. */
export function useChartTip() {
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(
    null,
  );
  return { tip, setTip };
}

export function ChartTip({
  tip,
}: {
  tip: { x: number; y: number; text: string } | null;
}) {
  if (!tip) return null;
  return (
    <div
      className="mono pointer-events-none absolute z-10 rounded-md px-2 py-1 text-[10px] text-text-0"
      style={{
        left: tip.x,
        top: tip.y,
        transform: "translate(-50%, -130%)",
        background: "var(--bg-3)",
        boxShadow: "0 4px 14px rgb(0 0 0 / .5), inset 0 0 0 1px var(--hairline)",
        whiteSpace: "pre",
      }}
    >
      {tip.text}
    </div>
  );
}
