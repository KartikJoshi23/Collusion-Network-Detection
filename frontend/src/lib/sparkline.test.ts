import { describe, expect, it } from "vitest";
import { bucketTimestamps, sparklinePoints } from "./sparkline";

describe("sparkline math", () => {
  it("buckets timestamps across the span and ignores nulls", () => {
    const counts = bucketTimestamps([10, 10, 20, 30, null], 4);
    expect(counts).toHaveLength(4);
    expect(counts.reduce((a, b) => a + b, 0)).toBe(4);
    expect(counts[0]).toBe(2); // both 10s in the first bucket
    expect(counts[3]).toBe(1); // max lands in the last bucket
  });

  it("handles empty and single-instant windows", () => {
    expect(bucketTimestamps([], 8)).toEqual(new Array(8).fill(0));
    const single = bucketTimestamps([5, 5, 5], 8);
    expect(single[0]).toBe(3);
    expect(single.slice(1).every((c) => c === 0)).toBe(true);
  });

  it("emits one svg point per bucket, inside the box", () => {
    const pts = sparklinePoints([0, 2, 1], 30, 10);
    const pairs = pts.split(" ").map((p) => p.split(",").map(Number));
    expect(pairs).toHaveLength(3);
    for (const [x, y] of pairs) {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(30);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(10);
    }
    expect(pairs[1][1]).toBeLessThan(pairs[2][1]); // peak sits higher
  });
});
