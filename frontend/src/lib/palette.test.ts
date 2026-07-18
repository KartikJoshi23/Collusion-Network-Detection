import { describe, expect, it } from "vitest";
import { CHART_SERIES, MOTIF_HUE, STATUS, UI_HUES } from "./palette";
import { MOTIF_TYPES } from "./motifs";

describe("V2 palette system", () => {
  it("assigns a fixed hue to every motif family", () => {
    for (const m of MOTIF_TYPES) {
      expect(MOTIF_HUE[m], m).toBeTruthy();
    }
  });

  it("keeps coral exclusive to flagged status — never a series color", () => {
    expect(STATUS.flagged).toBe(UI_HUES.coral);
    expect(CHART_SERIES).not.toContain(UI_HUES.coral);
    expect(Object.values(MOTIF_HUE)).not.toContain(UI_HUES.coral);
  });

  it("has five fixed-order categorical series", () => {
    expect(CHART_SERIES).toHaveLength(5);
    expect(new Set(CHART_SERIES).size).toBe(5);
  });
});
