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

// Time is recorded differently by different sources: the Bitcoin data uses
// numbered steps (1..49), the contract data uses calendar years, and some
// sources record nothing at all. Printing a bare "35 – 35" for the first case
// was unreadable — a viewer has no way to know 35 is a step index, and the
// repeated value looks like a bug rather than "it all happened at once".
const YEAR_FLOOR = 1900;

export function isCalendarYear(v: number | null): boolean {
  return v !== null && v >= YEAR_FLOOR;
}

export function fmtTimeWindow(
  start: number | null,
  end: number | null,
): string {
  if (start === null && end === null) return "not recorded";
  if (start === null || end === null) {
    const v = (start ?? end) as number;
    return isCalendarYear(v) ? String(v) : `step ${v}`;
  }
  if (isCalendarYear(start) || isCalendarYear(end)) {
    return start === end ? String(start) : `${start} – ${end}`;
  }
  return start === end ? `step ${start}` : `steps ${start} – ${end}`;
}

/** A full sentence for a tooltip / dossier line — says what the number IS. */
export function describeTimeWindow(
  start: number | null,
  end: number | null,
): string {
  if (start === null && end === null)
    return "This source does not record when things happened.";
  if (isCalendarYear(start) || isCalendarYear(end)) {
    return start === end
      ? `Everything here happened during ${start}.`
      : `Activity runs from ${start} through to ${end}.`;
  }
  if (start === end)
    return (
      `All of it lands in a single time step — step ${start}. ` +
      `This data is stamped with numbered steps in order, not calendar dates, ` +
      `so one step means one short stretch of time.`
    );
  return (
    `Activity spans steps ${start} to ${end}. ` +
    `This data is stamped with numbered steps in order, not calendar dates.`
  );
}
