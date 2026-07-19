// Pure-logic pins for the rigor extraction layer: shapes mirror the REAL
// artifact JSONs (multiseed.json / matrix.json / significance.json /
// noise_curve.json / label_efficiency.json / sensitivity.json).
import { describe, expect, it } from "vitest";
import {
  parseEnsembleMultiseed,
  parseLabelEfficiency,
  parseMultiseed,
  parseNoiseCurve,
  parseSensitivity,
  parseSignificance,
  parseTransferMatrix,
} from "./rigorExtract";

describe("parseMultiseed", () => {
  it("extracts aggregate and per-seed values", () => {
    const out = parseMultiseed(
      {
        aggregate: { auc_pr_mean: 0.4729, auc_pr_std: 0.0525 },
        per_seed: [{ auc_pr: 0.5492 }, { auc_pr: 0.4712 }],
      },
      "GATv2",
    );
    expect(out).toEqual({
      label: "GATv2",
      mean: 0.4729,
      std: 0.0525,
      perSeed: [0.5492, 0.4712],
    });
  });
  it("returns null on malformed payloads", () => {
    expect(parseMultiseed({}, "x")).toBeNull();
  });
});

describe("parseEnsembleMultiseed", () => {
  it("extracts members sorted by mean, skipping malformed", () => {
    const out = parseEnsembleMultiseed({
      members: {
        rank: { auc_pr_mean: 0.05, auc_pr_std: 0.002, auc_pr_per_seed: [0.05] },
        calibrated: { auc_pr_mean: 0.44, auc_pr_std: 0.05, auc_pr_per_seed: [0.44] },
        broken: { note: "no numbers" },
      },
    });
    expect(out.map((m) => m.label)).toEqual(["calibrated", "rank"]);
  });
});

describe("parseTransferMatrix", () => {
  it("keeps completed folds only and reads the macro lift", () => {
    const out = parseTransferMatrix({
      folds: [
        {
          test_group: "c1",
          val_group: "c7",
          status: "completed",
          n_confirmed_test: 30,
          prevalence_baseline: 0.767,
          auc_pr_mean: 0.8664,
          auc_pr_std: 0.0224,
          lift_mean: 1.13,
        },
        { test_group: "c9", status: "skipped", reason: "no viable val" },
      ],
      summary: { macro_lift_mean: 1.17 },
    });
    expect(out.folds).toHaveLength(1);
    expect(out.folds[0].group).toBe("c1");
    expect(out.macroLift).toBeCloseTo(1.17);
  });
});

describe("parseSignificance", () => {
  it("extracts comparison rows", () => {
    const rows = parseSignificance({
      comparisons: {
        gatv2_vs_xgb: {
          label_a: "GATv2",
          label_b: "XGB",
          auc_pr_a: 0.5492,
          auc_pr_b: 0.8104,
          delta: -0.2612,
          delta_ci_low: -0.2847,
          delta_ci_high: -0.2348,
          p_value: 0.001,
        },
      },
    });
    expect(rows).toHaveLength(1);
    expect(rows[0].delta).toBeCloseTo(-0.2612);
    expect(rows[0].labelB).toBe("XGB");
  });
});

describe("parseNoiseCurve", () => {
  it("maps rates to percent-x points, sorted", () => {
    const out = parseNoiseCurve({
      curve: [
        { rate: 0.1, auc_pr_mean: 0.4, auc_pr_std: 0.02 },
        { rate: 0.0, auc_pr_mean: 0.47, auc_pr_std: 0.05 },
      ],
    });
    expect(out.map((p) => p.k)).toEqual([0, 10]);
    expect(out[0].value).toBeCloseTo(0.47);
    expect(out[0].std).toBeCloseTo(0.05);
  });
});

describe("parseLabelEfficiency", () => {
  it("extracts source + gain curves and the full-label reference", () => {
    const out = parseLabelEfficiency({
      curve: [
        {
          k: 25,
          status: "completed",
          source_probe_auc_pr_mean: 0.266,
          transfer_gain_mean: -0.027,
        },
        {
          k: 10,
          status: "completed",
          source_probe_auc_pr_mean: 0.3,
          transfer_gain_mean: -0.009,
        },
      ],
      full_label_reference: { source_probe_auc_pr: 0.1501, raw_probe_auc_pr: 0.1084 },
    });
    expect(out.gain.map((p) => p.k)).toEqual([10, 25]);
    expect(out.source.map((p) => p.value)).toEqual([0.3, 0.266]);
    expect(out.reference).toEqual({ source: 0.1501, raw: 0.1084 });
  });
});

describe("parseSensitivity", () => {
  it("summarizes the grid invariances", () => {
    const out = parseSensitivity({
      results: [
        { jaccard_threshold: 0.3, min_fraction: null, n_kept: 254, n_hits_total: 27 },
        { jaccard_threshold: 0.5, min_fraction: 0.25, n_kept: 254, n_hits_total: 25 },
      ],
    });
    expect(out).toEqual({ nGrid: 2, keptValues: [254], hitsMin: 25, hitsMax: 27 });
  });
  it("returns null when empty", () => {
    expect(parseSensitivity({})).toBeNull();
  });
});
