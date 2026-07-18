// Risk and motif chips (§5.3): motif vocabulary mirrors backend MotifType.
import { RISK_VAR, riskBand } from "../../lib/format";
import { MOTIF_LABEL, isMotifId } from "../../lib/motifs";
import { MotifGlyph } from "./MotifGlyph";

export function RiskChip({ score }: { score: number }) {
  const band = riskBand(score);
  const color = RISK_VAR[band];
  return (
    <span
      className={`mono inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs ${
        band === "high" ? "risk-pulse" : ""
      }`}
      style={{
        color,
        background: `color-mix(in srgb, ${color} 13%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${color} 30%, transparent)`,
      }}
    >
      <span
        className="relative inline-block h-8 w-1 overflow-hidden rounded-full"
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
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs"
      style={{
        color: "var(--text-1)",
        background: "var(--glass-fill)",
        boxShadow: "inset 0 0 0 1px var(--hairline)",
      }}
    >
      <MotifGlyph motif={motif} size={13} className="text-accent" />
      {isMotifId(motif) ? MOTIF_LABEL[motif] : motif}
    </span>
  );
}
