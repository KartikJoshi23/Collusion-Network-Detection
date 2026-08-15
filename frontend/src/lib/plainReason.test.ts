import { describe, expect, it } from "vitest";
import { plainReason } from "./plainReason";

// Regression pin for the live 2026-07-25 complaint: an alert scoring 0.93 showed
// "no motif matched" and "red flags (0)" and nothing else, so a reviewer could
// not tell why it was risky.
//
// Attempt 1 was rejected as "written like a research paper".
// Attempt 2 passed a 14-term jargon test and was STILL judged too hard.
// Attempt 3 (these tests) changes the SUBJECT of every sentence: describe the
// situation, never the system. So alongside the jargon ban there is now a ban
// on talking about the machine at all, and the sentence cap drops 26 → 20.
describe("plain-language reasons", () => {
  // elliptic_pp:gatv2_multi_s0:16 — the case the stakeholder complained about
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

  // mendeley_eu:sage_struct_s0:1 — the two-firm procurement case
  const CASE_PAIR = {
    riskScore: 0.71,
    nMembers: 2,
    nMemberEdges: 1,
    windowStart: 2011,
    windowEnd: 2013,
    domain: "procurement",
  };

  it("leads with the striking fact, not with the count or the method", () => {
    const r = plainReason(CASE_16)!;
    // 85 things joined by 84 links cannot contain a loop — it is a chain
    expect(r.points[0]).toMatch(/^The money went through all of them in one go/);
    expect(r.headline).toBe("85 accounts, one after another");
  });

  it("explains a high-risk alert that matched no known shape", () => {
    const text = plainReason(CASE_16)!.points.join(" ");
    expect(text).toMatch(/one account to the next/i);
    expect(text).toMatch(/one short stretch of time/);
    expect(text).toContain("85 accounts are caught up in it");
    expect(text).toContain("That is where to start");
    // maxAttention > 0.5 → the dominant-link wording
    expect(text).toMatch(/matters more than everything else here put together/);
  });

  it("describes a situation, never the system that produced it", () => {
    const all = [
      plainReason(CASE_16)!,
      plainReason(CASE_PAIR)!,
      plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 90 })!,
      plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 40 })!,
    ]
      .flatMap((r) => [r.headline, ...r.points, r.caveat])
      .join(" ")
      .toLowerCase();

    // attempt 2 said "We asked the computer which parts made it suspicious"
    for (const machine of [
      "computer",
      "algorithm",
      "the system",
      "we asked",
      "we looked",
      "the software",
      "score",
      "flagged",
    ]) {
      expect(all, `must not talk about the machine: "${machine}"`).not.toContain(
        machine,
      );
    }
  });

  it("uses NO machine-learning jargon anywhere", () => {
    const all = [
      plainReason(CASE_16)!,
      plainReason(CASE_PAIR)!,
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

  it("keeps every sentence short enough to read once", () => {
    for (const facts of [CASE_16, CASE_PAIR, { ...CASE_16, domain: "procurement" }]) {
      const r = plainReason(facts)!;
      for (const p of [...r.points, r.caveat]) {
        for (const sentence of p.split(/(?<=\.)\s+/)) {
          const words = sentence.trim().split(/\s+/).length;
          expect(words, `too long: "${sentence}"`).toBeLessThanOrEqual(20);
        }
      }
    }
  });

  it("uses the right everyday words for each domain", () => {
    const fin = plainReason({ ...CASE_16, domain: "financial" })!;
    const proc = plainReason({ ...CASE_16, domain: "procurement" })!;
    expect(fin.points.join(" ")).toContain("accounts");
    expect(proc.points.join(" ")).toContain("companies");
    expect(fin.points.join(" ")).toMatch(/money went through all of them/);
    expect(proc.points.join(" ")).toMatch(/work was passed along a line/);
  });

  it("tells a chain, a tangle and a loop apart", () => {
    const chain = plainReason(CASE_16)!;
    const dense = plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 90 })!;
    const loops = plainReason({ ...CASE_16, nMembers: 20, nMemberEdges: 40 })!;
    expect(chain.points.join(" ")).toMatch(/one account to the next/i);
    expect(dense.points.join(" ")).toMatch(/deals with almost every other one/);
    expect(loops.points.join(" ")).toMatch(/goes round in circles/);
    expect(dense.headline).toBe("20 accounts, nearly all dealing with each other");
    expect(loops.headline).toBe("20 accounts, the same names going round");
  });

  it("handles the two-firm procurement case without sounding odd", () => {
    const r = plainReason(CASE_PAIR)!;
    expect(r.headline).toBe("2 companies, tied to each other");
    const text = r.points.join(" ");
    expect(text).toContain("Two companies, tied to each other");
    expect(text).toContain("It runs from 2011 through to 2013.");
    // fewer than three members ⇒ no shape claim is made at all
    expect(text).not.toMatch(/one after another|circles|almost every/);
  });

  it("gets singular and plural right", () => {
    const one = plainReason({ ...CASE_16, minimalNodes: 2, minimalEdges: 1 })!;
    expect(one.points.join(" ")).toContain("1 payment between them");
    expect(one.points.join(" ")).not.toContain("1 payments");
    const proc = plainReason({
      ...CASE_16,
      domain: "procurement",
      minimalNodes: 2,
      minimalEdges: 1,
    })!;
    expect(proc.points.join(" ")).toContain("1 deal between them");
  });

  it("says nothing rather than guessing when the facts are missing", () => {
    expect(plainReason({})).toBeNull();
  });
});
