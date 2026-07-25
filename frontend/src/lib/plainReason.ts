// Turn the numbers in an explanation bundle into sentences a 15-year-old can
// read once, at normal speed, and repeat to a friend.
//
// WHY THIS EXISTS: an alert can score 0.93 and still show "no motif matched"
// and "red flags (0)", because the pattern matcher only names shapes it can
// formally prove. A reviewer then sees a big number next to two blanks.
//
// THIRD ATTEMPT (2026-07-25). The second attempt passed a 14-word jargon test
// and was STILL judged too hard. The diagnosis in
// docs/presentation_scripts_brief.md §5 was not vocabulary — it was SUBJECT:
//
//   Attempt 2 described THE SYSTEM.    "We asked the computer which parts
//                                       actually made it suspicious."
//   Attempt 3 describes THE SITUATION. "The money went through all of them in
//                                       one go, one after another."
//
// RULES THAT CAME OUT OF THAT:
//   - Lead with the striking fact. Never with the method.
//   - Delete every clause that explains HOW WE KNOW. That belongs in the
//     technical panel underneath, and it is already there.
//   - No machine-learning words, and no words about the machine at all — no
//     "computer", "model", "we asked", "the system pointed at".
//   - Short sentences. One idea each. A full stop beats a dash.
//
// HONESTY RULE (unchanged, and it outranks all of the above): every sentence
// describes a measured number. It never claims wrongdoing, never invents a
// pattern, and says nothing at all when the numbers are missing.

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

type Shape = "chain" | "dense" | "loops";

/** What arrangement the connections are in, as an everyday picture.
 *
 *  n things joined by fewer than n links cannot contain a loop, so the money
 *  or the work can only travel forwards — that is the "chain". Far more links
 *  than things means nearly everyone is joined to nearly everyone. In between,
 *  paths can return to where they began. */
function shapeOf(nodes: number, edges: number): Shape | null {
  if (!nodes || nodes < 3 || !edges) return null;
  const ratio = edges / nodes;
  if (ratio < 1.05) return "chain";
  if (ratio > 2.5) return "dense";
  return "loops";
}

const SHAPE_LINES: Record<Shape, { financial: string[]; procurement: string[] }> = {
  chain: {
    financial: [
      "The money went through all of them in one go.",
      "One account to the next, then the next, then the next.",
      "It never came back to where it started.",
      "Ordinary business money does not travel like that.",
    ],
    procurement: [
      "The work was passed along a line, one company to the next.",
      "It never came back to where it started.",
      "It also never left the group.",
    ],
  },
  dense: {
    financial: [
      "Almost every account here deals with almost every other one.",
      "People who have no reason to know each other are rarely this tangled up.",
    ],
    procurement: [
      "Almost every company here turns up alongside almost every other one.",
      "Real competitors are rarely this close.",
    ],
  },
  loops: {
    financial: [
      "The money goes round in circles.",
      "It comes back to where it started instead of moving on to someone new.",
    ],
    procurement: [
      "The same companies keep turning up together, again and again.",
      "The same few names, over and over.",
    ],
  },
};

const HEADLINE: Record<Shape, (n: number, thing: string) => string> = {
  chain: (n, thing) => `${n} ${thing}, one after another`,
  dense: (n, thing) => `${n} ${thing}, nearly all dealing with each other`,
  loops: (n, thing) => `${n} ${thing}, the same names going round`,
};

export function plainReason(f: Facts): PlainReason | null {
  const points: string[] = [];
  const n = f.nMembers ?? 0;
  const e = f.nMemberEdges ?? 0;
  const financial = f.domain !== "procurement";
  const thing = financial ? "accounts" : "companies";
  const thingOne = financial ? "account" : "company";
  const payment = financial ? "payment" : "deal";
  const payments = financial ? "payments" : "deals";

  // 1. THE STRIKING FACT — what the arrangement looks like, first.
  const shape = shapeOf(n, e);
  if (shape) {
    points.push(
      SHAPE_LINES[shape][financial ? "financial" : "procurement"].join(" "),
    );
  }

  // 2. WHEN — a single window is the second most striking thing about a case.
  const sameWindow =
    f.windowStart !== undefined &&
    f.windowEnd !== undefined &&
    String(f.windowStart) === String(f.windowEnd);

  if (sameWindow) {
    points.push(
      financial
        ? "All of it happened in one short stretch of time. A real business " +
            "spreads its payments over weeks. This lot moved at once."
        : "All of it happened in one short stretch of time. Public contracts " +
            "normally come round over months. These did not.",
    );
  } else if (f.windowStart !== undefined && f.windowEnd !== undefined) {
    points.push(`It runs from ${f.windowStart} through to ${f.windowEnd}.`);
  }

  // 3. HOW MANY — a count, not a lecture about why we grouped them.
  if (n >= 3) {
    points.push(
      `${n} ${thing} are caught up in it. They are one case here, not ${n}.`,
    );
  } else if (n === 2) {
    points.push(`Two ${thing}, tied to each other. They come as a pair.`);
  }

  // 4. WHERE TO START — the minimal evidence, said as a place to look rather
  //    than as a thing an explainer produced.
  if (f.minimalNodes && f.minimalNodes > 0) {
    const ml = f.minimalEdges ?? 0;
    points.push(
      `Most of it comes down to ${f.minimalNodes} of the ${thing} and ` +
        `${ml} ${ml === 1 ? payment : payments} between them. ` +
        `That is where to start.`,
    );
  }

  // 5. THE ONE THING — only when a single link genuinely dominates.
  if (typeof f.maxAttention === "number" && f.maxAttention > 0) {
    points.push(
      f.maxAttention > 0.5
        ? `One single link between two of them matters more than everything ` +
            `else here put together.`
        : `One single link between two of them stands out from the rest.`,
    );
  }

  if (points.length === 0) return null;

  const headline =
    shape && n >= 3
      ? HEADLINE[shape](n, thing)
      : n >= 2
        ? `${n} ${thing}, tied to each other`
        : `What made this ${thingOne} stand out`;

  return {
    headline,
    points,
    caveat:
      "None of this is against the law on its own. Plenty of honest " +
      "businesses do each of these things. Together they are a reason for a " +
      "person to take a closer look. Nothing here says anyone did anything " +
      "wrong.",
  };
}
