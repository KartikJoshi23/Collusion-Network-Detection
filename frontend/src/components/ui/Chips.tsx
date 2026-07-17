// Risk and motif chips (§5.3): motif vocabulary mirrors backend MotifType.
import { RISK_VAR, riskBand } from "../../lib/format";

export function RiskChip({ score }: { score: number }) {
  const band = riskBand(score);
  const color = RISK_VAR[band];
  return (
    <span
      className="mono inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 text-xs"
      style={{
        color,
        background: `color-mix(in srgb, ${color} 14%, transparent)`,
      }}
    >
      <span
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ background: color }}
      />
      {score.toFixed(3)}
    </span>
  );
}

const MOTIF_LABEL: Record<string, string> = {
  cycle: "cycle",
  fan_in: "fan-in",
  fan_out: "fan-out",
  common_control: "common control",
  pass_through: "pass-through",
  rotation: "rotation",
  cover_bid: "cover bid",
  partition: "partition",
  clique: "clique",
};

export function MotifChip({ motif }: { motif: string | null }) {
  if (!motif) return <span className="text-xs text-text-2">—</span>;
  return (
    <span className="rounded border border-hairline bg-bg-2 px-1.5 py-0.5 text-xs text-text-1">
      {MOTIF_LABEL[motif] ?? motif}
    </span>
  );
}
