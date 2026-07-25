import { describe, expect, it } from "vitest";
import { plainReason } from "./plainReason";

// Regression pin for the live 2026-07-25 complaint: an alert scoring 0.93 showed
// "no motif matched" and "red flags (0)" and nothing else, so a reviewer could
// not tell why it was risky. The bundle already held the facts; they just were
// never put into words.
describe("plain-language reasons", () => {
  const CASE_16 = {
    riskScore: 0.9265,
    nMembers: 85,
    nMemberEdges: 84,
    windowStart: 45,
    windowEnd: 45,
    minimalNodes: 3,
    minimalEdges: 4,
    maxAttention: 0.5334,
    domain: "financial",
  };

  it("explains a high-risk alert that matched no motif", () => {
    const r = plainReason(CASE_16)!;
    expect(r).toBeTruthy();
    expect(r.headline).toContain("85 accounts");
    const text = r.points.join(" ");
    expect(text).toContain("85 accounts are involved");
    // 85 nodes / 84 edges is a tree — must be described as a chain/fan
    expect(text).toMatch(/chain or fan/);
    // single time window must be called out as a burst
    expect(text).toContain("single time window (45)");
    expect(text).toMatch(/53%.*attention/);
  });

  it("never states or implies guilt", () => {
    const r = plainReason(CASE_16)!;
    const all = [r.headline, ...r.points, r.caveat].join(" ").toLowerCase();
    for (const banned of ["guilty", "criminal", "fraud", "proves", "illegal activity"]) {
      // "illegal" appears only in the caveat's "none of them is illegal on its own"
      if (banned === "illegal activity") continue;
      expect(all, `must not assert "${banned}"`).not.toContain(banned);
    }
    expect(r.caveat).toContain("not accusations");
  });

  it("uses the right words for each domain", () => {
    const fin = plainReason({ ...CASE_16, domain: "financial" })!;
    const proc = plainReason({ ...CASE_16, domain: "procurement" })!;
    expect(fin.points.join(" ")).toContain("accounts");
    expect(proc.points.join(" ")).toContain("firms");
    // and the shape wording must be domain-appropriate, not copy-pasted
    expect(fin.points.join(" ")).toMatch(/value passes/);
    expect(proc.points.join(" ")).toMatch(/hand work onward/);
  });

  it("describes a dense group differently from a chain", () => {
    const dense = plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 90 })!;
    expect(dense.points.join(" ")).toMatch(/densely interconnected/);
  });

  it("gets singular/plural right", () => {
    const r = plainReason({ ...CASE_16, minimalNodes: 2, minimalEdges: 1 })!;
    expect(r.points.join(" ")).toContain("1 link ");
    expect(r.points.join(" ")).not.toContain("1 links");
  });

  it("says nothing rather than guessing when the facts are missing", () => {
    expect(plainReason({})).toBeNull();
  });
});
