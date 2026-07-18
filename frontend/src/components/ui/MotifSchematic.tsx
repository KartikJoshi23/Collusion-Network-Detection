// Animated motif schematic for the Case Detail dossier (§5.3 view 4, V2
// brief §3.4): the detected motif draws itself stroke-by-stroke (GSAP
// DrawSVG — free since the 2024/2025 licensing change), nodes pop in after
// their connecting strokes. Collapses to the finished static frame under
// prefers-reduced-motion. Geometry is schematic (pattern shape, not data).
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { useRef } from "react";
import { isMotifId, MOTIF_LABEL, type MotifId } from "../../lib/motifs";
import { MOTIF_HUE } from "../../lib/palette";

gsap.registerPlugin(DrawSVGPlugin, useGSAP);

// Node positions + directed strokes per family, on a 220x120 viewBox.
// `hot` nodes render coral (the flagged role in the pattern).
interface Scene {
  nodes: { x: number; y: number; r?: number; hot?: boolean }[];
  paths: string[];
}

const SCENES: Record<MotifId, Scene> = {
  cycle: {
    nodes: [
      { x: 110, y: 18, hot: true },
      { x: 48, y: 92 },
      { x: 172, y: 92 },
    ],
    paths: [
      "M99 27 57 82",
      "M62 96 158 96",
      "M164 82 121 27",
      "M121 20 a52 52 0 0 1 20 12",
    ],
  },
  fan_in: {
    nodes: [
      { x: 30, y: 22 },
      { x: 30, y: 60 },
      { x: 30, y: 98 },
      { x: 185, y: 60, r: 11, hot: true },
    ],
    paths: ["M40 26 172 54", "M42 60 170 60", "M40 94 172 66"],
  },
  fan_out: {
    nodes: [
      { x: 35, y: 60, r: 11, hot: true },
      { x: 190, y: 22 },
      { x: 190, y: 60 },
      { x: 190, y: 98 },
    ],
    paths: ["M48 54 180 26", "M50 60 178 60", "M48 66 180 94"],
  },
  common_control: {
    nodes: [
      { x: 110, y: 18, r: 11, hot: true },
      { x: 40, y: 98 },
      { x: 110, y: 98 },
      { x: 180, y: 98 },
    ],
    paths: ["M102 28 46 90", "M110 30 110 88", "M118 28 174 90"],
  },
  pass_through: {
    nodes: [
      { x: 25, y: 60 },
      { x: 83, y: 60, hot: true },
      { x: 141, y: 60, hot: true },
      { x: 199, y: 60 },
    ],
    paths: ["M35 60 72 60", "M94 60 130 60", "M152 60 188 60"],
  },
  rotation: {
    nodes: [
      { x: 110, y: 16, hot: true },
      { x: 178, y: 60 },
      { x: 110, y: 104 },
      { x: 42, y: 60 },
    ],
    paths: [
      "M110 16 a44 44 0 0 1 44 44 a44 44 0 0 1 -44 44 a44 44 0 0 1 -44 -44 a44 44 0 0 1 38 -43",
      "M96 15 l8 -4 3 9",
    ],
  },
  cover_bid: {
    nodes: [
      { x: 45, y: 100, r: 10, hot: true },
      { x: 110, y: 100 },
      { x: 175, y: 100 },
    ],
    paths: [
      "M45 92 45 62",
      "M110 92 110 30",
      "M175 92 175 44",
      "M25 108 195 108",
    ],
  },
  partition: {
    nodes: [
      { x: 74, y: 44 },
      { x: 146, y: 44 },
      { x: 110, y: 92, hot: true },
    ],
    paths: [
      "M110 60 m-46 0 a46 46 0 1 0 92 0 a46 46 0 1 0 -92 0",
      "M110 14 110 60",
      "M110 60 150 88",
      "M110 60 70 88",
    ],
  },
  clique: {
    nodes: [
      { x: 60, y: 25, hot: true },
      { x: 160, y: 25, hot: true },
      { x: 60, y: 95 },
      { x: 160, y: 95 },
    ],
    paths: [
      "M70 25 150 25",
      "M70 95 150 95",
      "M60 35 60 85",
      "M160 35 160 85",
      "M68 32 152 88",
      "M152 32 68 88",
    ],
  },
};

export function MotifSchematic({ motif }: { motif: string }) {
  const ref = useRef<SVGSVGElement>(null);

  useGSAP(
    () => {
      const svg = ref.current;
      if (!svg || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const tl = gsap.timeline({ defaults: { ease: "power2.inOut" } });
      tl.from(svg.querySelectorAll("path"), {
        drawSVG: "0%",
        duration: 0.55,
        stagger: 0.28,
      });
      tl.from(
        svg.querySelectorAll("circle"),
        { scale: 0, transformOrigin: "50% 50%", duration: 0.3, stagger: 0.1 },
        0.35,
      );
    },
    { scope: ref, dependencies: [motif] },
  );

  if (!isMotifId(motif)) return null;
  const scene = SCENES[motif];
  const hue = MOTIF_HUE[motif];

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        ref={ref}
        viewBox="0 0 220 120"
        className="w-full max-w-72"
        role="img"
        aria-label={`${MOTIF_LABEL[motif]} motif schematic`}
      >
        {scene.paths.map((d, i) => (
          <path
            key={`${motif}-p${i}`}
            d={d}
            fill="none"
            stroke={hue}
            strokeWidth={2}
            strokeLinecap="round"
            opacity={0.85}
          />
        ))}
        {scene.nodes.map((n, i) => (
          <circle
            key={`${motif}-n${i}`}
            cx={n.x}
            cy={n.y}
            r={n.r ?? 8}
            fill={n.hot ? "var(--risk-high)" : "var(--bg-3)"}
            stroke={n.hot ? "var(--risk-high)" : hue}
            strokeWidth={1.5}
            style={
              n.hot
                ? { filter: "drop-shadow(0 0 6px var(--risk-high))" }
                : undefined
            }
          />
        ))}
      </svg>
      <span className="text-xs" style={{ color: hue }}>
        {MOTIF_LABEL[motif]} pattern — schematic, not case data
      </span>
    </div>
  );
}
