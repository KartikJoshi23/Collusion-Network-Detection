import { describe, expect, it } from "vitest";
import { fmtTimeWindow, riskBand, shortId } from "./format";

describe("format", () => {
  it("bands scores with coral reserved for the top band", () => {
    expect(riskBand(0.9)).toBe("high");
    expect(riskBand(0.5)).toBe("med");
    expect(riskBand(0.1)).toBe("low");
  });

  it("collapses equal time windows and handles nulls", () => {
    expect(fmtTimeWindow(35, 35)).toBe("35");
    expect(fmtTimeWindow(35, 49)).toBe("35 – 49");
    expect(fmtTimeWindow(null, null)).toBe("—");
  });

  it("truncates long ids", () => {
    expect(shortId("tx:1234567890123", 10)).toBe("tx:1234567…");
    expect(shortId("tx:1")).toBe("tx:1");
  });
});
