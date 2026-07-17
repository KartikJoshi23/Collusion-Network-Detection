// Formatters (§5.1): amounts, ids, scores — all rendered with tabular numerals.

export function fmtScore(x: number): string {
  return x.toFixed(3);
}

export function fmtPct(x: number, digits = 1): string {
  return `${(x * 100).toFixed(digits)}%`;
}

export function shortId(id: string, head = 10): string {
  return id.length > head + 3 ? id.slice(0, head) + "…" : id;
}

// Risk band from a calibrated score. Coral is reserved for the top band (§5.2).
export type RiskBand = "high" | "med" | "low";

export function riskBand(score: number): RiskBand {
  if (score >= 0.66) return "high";
  if (score >= 0.33) return "med";
  return "low";
}

export const RISK_VAR: Record<RiskBand, string> = {
  high: "var(--risk-high)",
  med: "var(--risk-med)",
  low: "var(--benign)",
};

export function fmtTimeWindow(
  start: number | null,
  end: number | null,
): string {
  if (start === null && end === null) return "—";
  if (start === end) return String(start);
  return `${start ?? "?"} – ${end ?? "?"}`;
}
