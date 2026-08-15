// Motif vocabulary — mirrors backend MotifType (schema/types.py) exactly.
// Labels are display copy; every motif renders a distinct SVG glyph
// (components/ui/MotifGlyph.tsx). Pinned by lib/motifs.test.ts.

export const MOTIF_TYPES = [
  "cycle",
  "fan_in",
  "fan_out",
  "common_control",
  "pass_through",
  "rotation",
  "cover_bid",
  "partition",
  "clique",
] as const;

export type MotifId = (typeof MOTIF_TYPES)[number];

export const MOTIF_LABEL: Record<MotifId, string> = {
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

export function isMotifId(x: string): x is MotifId {
  return (MOTIF_TYPES as readonly string[]).includes(x);
}
