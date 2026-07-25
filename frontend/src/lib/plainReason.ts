// Turn the numbers already in an explanation bundle into sentences a
// non-technical reviewer can read.
//
// WHY THIS EXISTS: an alert can score 0.93 and still show "no motif matched"
// and "red flags (0)", because the pattern matcher only names the nine shapes
// it can formally prove. A reviewer then sees a very high risk score next to
// two blanks and cannot tell why. But the bundle already carries the facts —
// group size, how the connections are arranged, whether everything happened at
// once. This turns those facts into plain English.
//
// HONESTY RULE: every sentence below is a DESCRIPTION of a measured number, not
// a claim about guilt and not an invented pattern. If the numbers are missing
// we say nothing rather than guessing.

export interface PlainReason {
  /** short headline, e.g. "85 accounts moving as one group" */
  headline: string;
  /** the observations, each safe to read aloud */
  points: string[];
  /** the honest limit of what these observations mean */
  caveat: string;
}

interface Facts {
  riskScore?: number;
  nMembers?: number;
  nMemberEdges?: number;
  windowStart?: number | string;
  windowEnd?: number | string;
  minimalNodes?: number;
  minimalEdges?: number;
  maxAttention?: number;
  domain?: string;
}

/** Describe how the connections are arranged, in words. */
function describeShape(nodes: number, edges: number, domain?: string): string | null {
  if (!nodes || nodes < 3 || !edges) return null;
  const ratio = edges / nodes;
  const isFinancial = domain !== "procurement";
  if (ratio < 1.05) {
    // n-1 edges for n nodes = a tree: no loops, everything hangs off a path
    return isFinancial
      ? "The connections form a chain or fan rather than a normal web — value passes " +
          "along a line instead of circulating between the same parties. Layering " +
          "and pass-through behaviour looks like this."
      : "The connections form a chain or fan rather than a normal web — the same " +
          "few parties hand work onward instead of competing against each other.";
  }
  if (ratio > 2.5) {
    return isFinancial
      ? "The accounts are densely interconnected — close to everyone dealing with " +
          "everyone. Ordinary unrelated accounts are rarely this tangled."
      : "The firms are densely interconnected — close to everyone appearing " +
          "alongside everyone. Genuine competitors are rarely this tangled.";
  }
  return isFinancial
    ? "Each account connects to roughly one or two others, forming loops — value " +
        "can return towards where it started."
    : "Each firm connects to roughly one or two others, forming loops — the same " +
      "parties reappear together.";
}

export function plainReason(f: Facts): PlainReason | null {
  const points: string[] = [];
  const n = f.nMembers ?? 0;
  const e = f.nMemberEdges ?? 0;
  const isFinancial = f.domain !== "procurement";
  const unit = isFinancial ? "accounts" : "firms";

  if (n >= 2) {
    points.push(
      `${n} ${unit} are involved, and they were pulled out as one connected group ` +
        `rather than as separate cases.`,
    );
  }

  const shape = describeShape(n, e, f.domain);
  if (shape) points.push(shape);

  // all activity inside a single time step = a burst, not steady behaviour
  if (
    f.windowStart !== undefined &&
    f.windowEnd !== undefined &&
    String(f.windowStart) === String(f.windowEnd)
  ) {
    points.push(
      `Everything happened inside a single time window (${f.windowStart}). Normal ` +
        `business activity is usually spread out; a whole group acting at once is not.`,
    );
  } else if (f.windowStart !== undefined && f.windowEnd !== undefined) {
    points.push(`Activity runs from ${f.windowStart} to ${f.windowEnd}.`);
  }

  if (f.minimalNodes && f.minimalNodes > 0) {
    const ml = f.minimalEdges ?? 0;
    points.push(
      `When asked which connections actually drove the decision, the model kept ` +
        `only ${f.minimalNodes} ${unit} and ${ml} ${ml === 1 ? "link" : "links"} — ` +
        `so the signal comes from a small, specific part of the group, not from ` +
        `its size alone.`,
    );
  }

  if (typeof f.maxAttention === "number" && f.maxAttention > 0) {
    points.push(
      `Its strongest single connection carried ${(f.maxAttention * 100).toFixed(0)}% ` +
        `of the model's attention, meaning one particular link mattered far more ` +
        `than the rest.`,
    );
  }

  if (points.length === 0) return null;

  const headline =
    n >= 2
      ? `${n} ${unit} moving as one group`
      : "What the model reacted to";

  return {
    headline,
    points,
    caveat:
      "These are descriptions of measured facts, not accusations. None of them is " +
      "illegal on its own — they are the reasons this group was put in front of a " +
      "human, who decides what happens next.",
  };
}
