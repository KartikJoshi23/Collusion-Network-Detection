// V2 functional multi-hue system (docs/frontend_overhaul.md §3.1).
// Two tiers: UI hues (bright — glow, chips, ink accents) and the CHART
// categorical tier, validated with the dataviz six-checks against #0a0e17
// (L band 0.48–0.67 dark, chroma ≥ 0.1, worst adjacent CVD ΔE 25+, ≥3:1).
// Assign categorical hues in FIXED order, never cycled.

export const UI_HUES = {
  cyan: "#22d3ee",
  violet: "#a78bfa",
  magenta: "#e879f9",
  amber: "#fbbf24",
  teal: "#2dd4bf",
  coral: "#ff5a5f", // flagged/high-risk ONLY (§5.2 exclusivity rule)
} as const;

/** Fixed-order categorical series colors for charts (validated). */
export const CHART_SERIES = [
  "#0891b2", // cyan
  "#8b5cf6", // violet
  "#d97706", // amber
  "#c026d3", // magenta
  "#0d9488", // teal
] as const;

/** Status colors are reserved and never reused as series colors. */
export const STATUS = {
  benign: UI_HUES.teal,
  medium: UI_HUES.amber,
  flagged: UI_HUES.coral,
} as const;

/** Per-motif family hue (identity, fixed): financial motifs cool, procurement
    motifs warm-violet, common_control shared. Used by glyph chips. */
export const MOTIF_HUE: Record<string, string> = {
  cycle: UI_HUES.cyan,
  fan_in: UI_HUES.cyan,
  fan_out: UI_HUES.cyan,
  pass_through: UI_HUES.teal,
  common_control: UI_HUES.amber,
  rotation: UI_HUES.violet,
  cover_bid: UI_HUES.magenta,
  partition: UI_HUES.violet,
  clique: UI_HUES.magenta,
};
