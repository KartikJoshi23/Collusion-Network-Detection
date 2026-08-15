import { describe, expect, it } from "vitest";
import { deepLinkTarget } from "./deeplink";

const DATASETS = [
  { dataset: "elliptic_pp", domain: "financial" },
  { dataset: "mendeley_eu", domain: "procurement" },
];

describe("deepLinkTarget", () => {
  it("resolves a deep-linked alert to its own dataset and domain", () => {
    expect(deepLinkTarget("mendeley_eu:sage_struct_s0:1", DATASETS)).toEqual({
      dataset: "mendeley_eu",
      domain: "procurement",
    });
    expect(deepLinkTarget("elliptic_pp:gatv2_multi_s0:12", DATASETS)).toEqual({
      dataset: "elliptic_pp",
      domain: "financial",
    });
  });

  it("returns null when there is nothing to resolve", () => {
    expect(deepLinkTarget(undefined, DATASETS)).toBeNull();
    expect(deepLinkTarget("mendeley_eu:sage_struct_s0:1", undefined)).toBeNull();
    expect(deepLinkTarget("unknown_ds:run:1", DATASETS)).toBeNull();
    expect(deepLinkTarget("", DATASETS)).toBeNull();
  });
});
