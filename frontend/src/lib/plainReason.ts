// Turn the numbers in an explanation bundle into sentences a 15-year-old can
// read without stopping.
//
// WHY THIS EXISTS: an alert can score 0.93 and still show "no motif matched"
// and "red flags (0)", because the pattern matcher only names shapes it can
// formally prove. A reviewer then sees a big number next to two blanks.
//
// LANGUAGE RULES (a professional reviewer said the first version was still
// written like a research paper — these are the rules that came out of that):
//   - No machine-learning words. No "signal", "attention", "model", "layering",
//     "topology", "structural", "attribution", "subgraph", "node", "edge".
//   - Short sentences. One idea each. Prefer a full stop over a dash.
//   - Say the everyday thing first ("money moves in a line, like a relay
//     race"), never the technical thing.
//   - Say plainly what it does NOT mean.
//
// HONESTY RULE (unchanged): every sentence describes a measured number. It
// never claims wrongdoing, never invents a pattern, and we say nothing at all
// when the numbers are missing.

export interface PlainReason {
  headline: string;
  points: string[];
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

/** Describe the arrangement of the connections using an everyday picture. */
function describeShape(nodes: number, edges: number, financial: boolean): string | null {
  if (!nodes || nodes < 3 || !edges) return null;
  const ratio = edges / nodes;

  if (ratio < 1.05) {
    // n-1 links for n things = a tree: no loops, everything hangs off a line
    return financial
      ? "The money moves in a line, like a relay race. It goes from one account " +
          "to the next, then the next. It does not go back and forth between the " +
          "same people. This is one of the ways money gets moved when someone " +
          "wants it to be hard to trace."
      : "The work passes along in a line, like a relay race. The same few " +
          "companies hand it on to each other. They are not competing against " +
          "one another for it.";
  }
  if (ratio > 2.5) {
    return financial
      ? "Almost every account here deals with almost every other one. Strangers " +
          "who have no reason to know each other are rarely this closely tied " +
          "together."
      : "Almost every company here appears alongside almost every other one. " +
          "Real competitors are rarely this closely tied together.";
  }
  return financial
    ? "The money goes round in loops. It can come back to where it started, " +
        "instead of moving on to someone new."
    : "The same companies keep turning up together, again and again.";
}

export function plainReason(f: Facts): PlainReason | null {
  const points: string[] = [];
  const n = f.nMembers ?? 0;
  const e = f.nMemberEdges ?? 0;
  const financial = f.domain !== "procurement";
  const thing = financial ? "bank accounts" : "companies";
  const thingOne = financial ? "account" : "company";

  if (n >= 2) {
    points.push(
      `There are ${n} ${thing} here. They are all joined to each other, so we ` +
        `look at them together as one case instead of ${n} separate ones.`,
    );
  }

  const shape = describeShape(n, e, financial);
  if (shape) points.push(shape);

  const sameWindow =
    f.windowStart !== undefined &&
    f.windowEnd !== undefined &&
    String(f.windowStart) === String(f.windowEnd);

  if (sameWindow) {
    points.push(
      `It all happened in one short stretch of time. A real business usually ` +
        `spreads its payments out over weeks or months. This whole group acted ` +
        `at once.`,
    );
  } else if (f.windowStart !== undefined && f.windowEnd !== undefined) {
    points.push(`The activity runs from ${f.windowStart} to ${f.windowEnd}.`);
  }

  if (f.minimalNodes && f.minimalNodes > 0) {
    const ml = f.minimalEdges ?? 0;
    points.push(
      `We asked the computer which parts actually made it suspicious. It pointed ` +
        `at just ${f.minimalNodes} of the ${thing} and ${ml} ` +
        `${ml === 1 ? "payment" : financial ? "payments" : "links"} between them. ` +
        `So the warning is about something specific, not just about the group ` +
        `being big.`,
    );
  }

  if (typeof f.maxAttention === "number" && f.maxAttention > 0) {
    points.push(
      `One single connection stood out far more than all the others — the ` +
        `computer treated it as ${(f.maxAttention * 100).toFixed(0)} out of 100 ` +
        `of what mattered here. That is the first place a person should look.`,
    );
  }

  if (points.length === 0) return null;

  const headline =
    n >= 2 ? `${n} ${thing}, all joined together` : `What made this ${thingOne} stand out`;

  return {
    headline,
    points,
    caveat:
      "None of these things is against the law on its own. Plenty of honest " +
      "businesses do each one. Together they are just a reason for a person to " +
      "take a closer look. Nothing here says anyone did anything wrong.",
  };
}
