import { describe, expect, it } from "vitest";
import { parseAtK, parsePerTimeStep, parseQueue } from "./metricsExtract";

describe("metrics extraction", () => {
  it("parses per-time-step blocks sorted by step", () => {
    const pts = parsePerTimeStep({
      per_time_step: {
        "43": { auc_pr: 0.04, prevalence_baseline: 0.017 },
        "35": { auc_pr: 0.9, prevalence_baseline: 0.135 },
      },
    });
    expect(pts.map((p) => p.step)).toEqual([35, 43]);
    expect(pts[1].aucPr).toBeCloseTo(0.04);
    expect(pts[0].prevalence).toBeCloseTo(0.135);
  });

  it("parses precision@k keys only, sorted by k", () => {
    const pts = parseAtK(
      { "precision@200": 0.4, "precision@50": 0.9, "recall@50": 0.1, auc_pr: 0.5 },
      "precision",
    );
    expect(pts).toEqual([
      { k: 50, value: 0.9 },
      { k: 200, value: 0.4 },
    ]);
  });

  it("parses queue blocks and tolerates absence", () => {
    expect(parseQueue(undefined)).toEqual([]);
    const pts = parseQueue({
      queue: { "@50": { precision: 0.32 }, "@100": { precision: 0.23 } },
    });
    expect(pts).toEqual([
      { k: 50, value: 0.32 },
      { k: 100, value: 0.23 },
    ]);
  });
});
