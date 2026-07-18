// Risk and motif chips (§5.3): motif vocabulary mirrors backend MotifType.
// V2: chips carry per-family hues (multi-hue rule), bloom on hover, and name
// their family in a tooltip. Scores read as calibrated probabilities (F30).
import { RISK_VAR, riskBand } from "../../lib/format";
import { MOTIF_LABEL, isMotifId } from "../../lib/motifs";
import { MOTIF_HUE } from "../../lib/palette";
import { MotifGlyph } from "./MotifGlyph";

export function RiskChip({ score }: { score: number }) {
  const band = riskBand(score);
  const color = RISK_VAR[band];
  return (
    <span
      className={`mono chip-bloom inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs ${
        band === "high" ? "risk-pulse" : ""
      }`}
      title={`calibrated probability ${score.toFixed(3)} — ${band} band`}
      style={{
        color,
        background: `color-mix(in srgb, ${color} 13%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${color} 30%, transparent)`,
      }}
    >
      <span
        className="relative inline-block overflow-hidden rounded-full"
        style={{
          height: 10,
          width: 3,
          background: `color-mix(in srgb, ${color} 22%, transparent)`,
        }}
      >
        <span
          className="absolute inset-x-0 bottom-0 rounded-full"
          style={{ height: `${Math.round(score * 100)}%`, background: color }}
        />
      </span>
      {score.toFixed(3)}
    </span>
  );
}

export function MotifChip({ motif }: { motif: string | null }) {
  if (!motif) return <span className="text-xs text-text-2">—</span>;
  const hue = MOTIF_HUE[motif] ?? "var(--text-1)";
  const label = isMotifId(motif) ? MOTIF_LABEL[motif] : motif;
  return (
    <span
      className="chip-bloom inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs"
      title={`${label} motif family`}
      style={{
        color: hue,
        background: `color-mix(in srgb, ${hue} 12%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${hue} 28%, transparent)`,
      }}
    >
      <MotifGlyph motif={motif} size={13} />
      {label}
    </span>
  );
}

/** Red-flag count badge (amber — warnings live in the amber family). */
export function FlagBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span
      className="mono chip-bloom inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs"
      title={`${count} red-flag indicator${count > 1 ? "s" : ""} cited`}
      style={{
        color: "var(--hue-amber)",
        background: "color-mix(in srgb, var(--hue-amber) 13%, transparent)",
        boxShadow:
          "inset 0 0 0 1px color-mix(in srgb, var(--hue-amber) 30%, transparent)",
      }}
    >
      <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden>
        <path
          d="M2.5 1.5v9M2.5 2h6.5l-1.8 2.2L9 6.5H2.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {count}
    </span>
  );
}
