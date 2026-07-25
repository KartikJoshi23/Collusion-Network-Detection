"""Find the genuinely hard sentences in the report.

Not a style opinion — three mechanical signals:
  1. long sentences (>30 words)
  2. sentences stacking multiple clauses (many commas / dashes / semicolons)
  3. sentences using rare/technical words with no plain gloss nearby
"""

import re
from pathlib import Path

tex = Path(
    r"D:/MAIB/Term - 3/Deep Learning/Collusion-Network-Detection/docs/internal_report/collusiongraph_internal_report.tex"
).read_text(encoding="utf-8")

# drop preamble, comments, tables (tables are reference, not prose)
body = tex[tex.find(r"\begin{document}") :]
body = re.sub(r"(?m)^\s*%.*$", "", body)
body = re.sub(r"\\begin\{(longtable|tabular)\}.*?\\end\{\1\}", " ", body, flags=re.S)
body = re.sub(r"\\(code|texttt)\{[^{}]*\}", " CODE ", body)
body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", body)
body = re.sub(r"[{}$&#_^~\\]", " ", body)
body = re.sub(r"\s+", " ", body)

HARD_WORDS = {
    "amortized",
    "amortised",
    "isotonic",
    "inductive",
    "stochastic",
    "heuristic",
    "orthogonal",
    "monotone",
    "monotonic",
    "canonical",
    "idempotent",
    "invariant",
    "instantiate",
    "instantiated",
    "parameterised",
    "parameterized",
    "regime",
    "granularity",
    "cardinality",
    "topology",
    "topological",
    "aggregation",
    "aggregates",
    "propagate",
    "propagation",
    "embedding",
    "embeddings",
    "calibrated",
    "calibration",
    "prevalence",
    "bipartite",
    "projection",
    "deduplication",
    "suppression",
    "attribution",
    "fidelity",
    "provenance",
    "adversarial",
    "artifact",
    "artifacts",
    "corpus",
    "retrieval",
    "degenerate",
}

sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.split()) > 4]
flagged = []
for s in sents:
    words = s.split()
    n = len(words)
    clauses = s.count(",") + s.count(";") + s.count("---") + s.count(":")
    hard = {w.strip(".,;:()").lower() for w in words} & HARD_WORDS
    score = 0
    why = []
    if n > 34:
        score += 2
        why.append(f"{n} words")
    elif n > 27:
        score += 1
        why.append(f"{n} words")
    if clauses >= 4:
        score += 2
        why.append(f"{clauses} clauses")
    elif clauses == 3:
        score += 1
        why.append(f"{clauses} clauses")
    if len(hard) >= 3:
        score += 2
        why.append("jargon: " + ",".join(sorted(hard)[:4]))
    elif len(hard) == 2:
        score += 1
        why.append("jargon: " + ",".join(sorted(hard)))
    if score >= 3:
        flagged.append((score, why, s))

flagged.sort(key=lambda x: -x[0])
print(f"prose sentences examined: {len(sents)}")
print(
    f"flagged as hard (score>=3): {len(flagged)}  ({100 * len(flagged) / max(len(sents), 1):.1f}%)\n"
)
for score, why, s in flagged[:22]:
    print(f"[{score}] {'; '.join(why)}")
    print(f"    {s[:190]}")
    print()
