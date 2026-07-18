import { describe, expect, it } from "vitest";
import { isMotifId, MOTIF_LABEL, MOTIF_TYPES } from "./motifs";

// Backend MotifType vocabulary (schema/types.py §4.4) — if the backend enum
// grows, this list and the frontend must grow together.
const BACKEND_MOTIF_TYPES = [
  "cycle",
  "fan_in",
  "fan_out",
  "common_control",
  "pass_through",
  "rotation",
  "cover_bid",
  "partition",
  "clique",
];

describe("motif vocabulary", () => {
  it("mirrors the backend MotifType enum exactly", () => {
    expect([...MOTIF_TYPES].sort()).toEqual([...BACKEND_MOTIF_TYPES].sort());
  });

  it("labels every motif", () => {
    for (const m of MOTIF_TYPES) {
      expect(MOTIF_LABEL[m]).toBeTruthy();
    }
  });

  it("narrows unknown strings", () => {
    expect(isMotifId("cycle")).toBe(true);
    expect(isMotifId("not_a_motif")).toBe(false);
  });
});
