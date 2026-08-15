import { describe, expect, it } from "vitest";
import { describeTimeWindow, fmtTimeWindow, riskBand, shortId } from "./format";

describe("format", () => {
  it("bands scores with coral reserved for the top band", () => {
    expect(riskBand(0.9)).toBe("high");
    expect(riskBand(0.5)).toBe("med");
    expect(riskBand(0.1)).toBe("low");
  });

  // A bare "35 – 35" told a first-time viewer nothing: they cannot know 35 is a
  // step index rather than a date, and the repeated value reads as a bug rather
  // than "it all happened at once". Step-style and year-style windows must now
  // be distinguishable on sight.
  it("labels step-style windows as steps", () => {
    expect(fmtTimeWindow(35, 35)).toBe("step 35");
    expect(fmtTimeWindow(35, 49)).toBe("steps 35 – 49");
  });

  it("leaves calendar years alone — they already read as dates", () => {
    expect(fmtTimeWindow(2015, 2015)).toBe("2015");
    expect(fmtTimeWindow(2004, 2021)).toBe("2004 – 2021");
  });

  it("says so plainly when there is no time at all", () => {
    expect(fmtTimeWindow(null, null)).toBe("not recorded");
  });

  it("describes a window in a full sentence for tooltips", () => {
    // the single-step case is the one that confused a reviewer
    expect(describeTimeWindow(35, 35)).toMatch(/single time step/);
    expect(describeTimeWindow(35, 35)).toMatch(/not calendar dates/);
    expect(describeTimeWindow(2015, 2015)).toBe(
      "Everything here happened during 2015.",
    );
    expect(describeTimeWindow(2004, 2021)).toMatch(/2004 through to 2021/);
    expect(describeTimeWindow(null, null)).toMatch(/does not record/);
  });

  it("truncates long ids", () => {
    expect(shortId("tx:1234567890123", 10)).toBe("tx:1234567…");
    expect(shortId("tx:1")).toBe("tx:1");
  });
});
