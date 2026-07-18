// Temporal sparkline math (pure, tested): bucket real event timestamps into
// a fixed-width histogram and emit SVG polyline points. Sparklines render
// ONLY from real timestamps (subgraph edges) — never synthesized activity.

export function bucketTimestamps(
  timestamps: (number | null)[],
  buckets = 16,
): number[] {
  const ts = timestamps.filter((t): t is number => t !== null);
  const counts = new Array<number>(buckets).fill(0);
  if (ts.length === 0) return counts;
  const min = Math.min(...ts);
  const max = Math.max(...ts);
  const span = max - min;
  for (const t of ts) {
    const i =
      span === 0
        ? 0
        : Math.min(buckets - 1, Math.floor(((t - min) / span) * buckets));
    counts[i] += 1;
  }
  return counts;
}

export function sparklinePoints(
  counts: number[],
  width: number,
  height: number,
  pad = 1,
): string {
  if (counts.length === 0) return "";
  const peak = Math.max(...counts, 1);
  const step = (width - 2 * pad) / Math.max(counts.length - 1, 1);
  return counts
    .map((c, i) => {
      const x = pad + i * step;
      const y = height - pad - (c / peak) * (height - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
