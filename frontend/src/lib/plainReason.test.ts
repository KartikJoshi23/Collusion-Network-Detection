import { describe, expect, it } from "vitest";
import { plainReason } from "./plainReason";

// Regression pin for the live 2026-07-25 complaint: an alert scoring 0.93 showed
// "no motif matched" and "red flags (0)" and nothing else, so a reviewer could
// not tell why it was risky. A professional reviewer then said the first fix was
// STILL written like a research paper. These tests pin both the content and the
// reading level.
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
    expect(r.headline).toContain("85 bank accounts");
    const text = r.points.join(" ");
    expect(text).toContain("There are 85 bank accounts here");
    // 85 things joined by 84 links is a tree — describe it as a line/relay
    expect(text).toMatch(/relay race/);
    // everything in one period must be called out
    expect(text).toMatch(/one short stretch of time/);
    // the standout connection, as a plain fraction not "attention"
    expect(text).toMatch(/53 out of 100/);
  });

  it("uses NO machine-learning jargon anywhere", () => {
    const all = [
      plainReason(CASE_16)!,
      plainReason({ ...CASE_16, domain: "procurement" })!,
      plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 90 })!,
    ]
      .flatMap((r) => [r.headline, ...r.points, r.caveat])
      .join(" ")
      .toLowerCase();

    for (const jargon of [
      "attention",
      "signal",
      "model",
      "layering",
      "topology",
      "structural",
      "attribution",
      "subgraph",
      "node",
      "edge",
      "motif",
      "calibrated",
      "prevalence",
      "embedding",
    ]) {
      expect(all, `must not use the word "${jargon}"`).not.toContain(jargon);
    }
  });

  it("never states or implies guilt", () => {
    const r = plainReason(CASE_16)!;
    const all = [r.headline, ...r.points, r.caveat].join(" ").toLowerCase();
    for (const banned of ["guilty", "criminal", "fraud", "proves", "laundering"]) {
      expect(all, `must not assert "${banned}"`).not.toContain(banned);
    }
    expect(r.caveat).toContain("against the law on its own");
    expect(r.caveat).toContain("Nothing here says anyone did anything wrong");
  });

  it("keeps sentences short enough to read once", () => {
    const r = plainReason(CASE_16)!;
    for (const p of r.points) {
      for (const sentence of p.split(/(?<=\.)\s+/)) {
        const words = sentence.trim().split(/\s+/).length;
        expect(words, `too long: "${sentence}"`).toBeLessThanOrEqual(26);
      }
    }
  });

  it("uses the right everyday words for each domain", () => {
    const fin = plainReason({ ...CASE_16, domain: "financial" })!;
    const proc = plainReason({ ...CASE_16, domain: "procurement" })!;
    expect(fin.points.join(" ")).toContain("bank accounts");
    expect(proc.points.join(" ")).toContain("companies");
    expect(fin.points.join(" ")).toMatch(/money moves in a line/);
    expect(proc.points.join(" ")).toMatch(/work passes along in a line/);
  });

  it("describes a dense group differently from a chain", () => {
    const dense = plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 90 })!;
    expect(dense.points.join(" ")).toMatch(/deals with almost every other one/);
  });

  it("gets singular and plural right", () => {
    const r = plainReason({ ...CASE_16, minimalNodes: 2, minimalEdges: 1 })!;
    const t = r.points.join(" ");
    expect(t).toContain("1 payment ");
    expect(t).not.toContain("1 payments");
  });

  it("says nothing rather than guessing when the facts are missing", () => {
    expect(plainReason({})).toBeNull();
  });
});
