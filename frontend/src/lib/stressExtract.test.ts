import { describe, expect, it } from "vitest";
import { parseStress } from "./stressExtract";

describe("parseStress", () => {
  it("normalises the multi-seed artifact and keeps the best arm per shape", () => {
    const payload = {
      population: 163327,
      seeds: [0, 1, 2, 3, 4],
      n_injected_instances: 100,
      n_injected_members: 940,
      recovery_multiseed: {
        gae: {
          coordinated_cluster: {
            n_members: 160,
            "recall@2000": { mean: 0.79, std: 0.1 },
          },
        },
        ensemble_rank: {
          coordinated_cluster: {
            n_members: 160,
            "recall@2000": { mean: 0.92, std: 0.17 },
          },
        },
      },
    };
    const m = parseStress(payload)!;
    expect(m.population).toBe(163327);
    expect(m.nSeeds).toBe(5);
    expect(m.nMembers).toBe(940);
    const clique = m.shapes.find((s) => s.motif === "coordinated_cluster")!;
    // best arm at 2000 is ensemble_rank (0.92 > 0.79)
    expect(clique.byBudget[2000].recall).toBeCloseTo(0.92);
    expect(clique.byBudget[2000].arm).toBe("ensemble_rank");
    expect(clique.byBudget[2000].std).toBeCloseTo(0.17);
  });

  it("normalises the single-seed report shape (std defaults to 0)", () => {
    const payload = {
      population: 500,
      recovery: {
        dominant: [
          { motif_type: "rotation", n_members: 240, "recall@2000": 0.09 },
          { motif_type: "cover_bid", n_members: 120, "recall@2000": 0.0 },
        ],
      },
    };
    const m = parseStress(payload)!;
    expect(m.nSeeds).toBe(1);
    // shapes sorted by top-budget recall desc
    expect(m.shapes[0].motif).toBe("rotation");
    expect(m.shapes[0].byBudget[2000]).toEqual({ recall: 0.09, std: 0, arm: "dominant" });
  });

  it("returns null when the payload has neither recovery shape", () => {
    expect(parseStress({ population: 1 })).toBeNull();
    expect(parseStress({ recovery_multiseed: {} })).toBeNull();
  });
});
