"""Find machine-learning jargon in text the USER actually sees on screen.

Only user-facing strings: JSX text, title=, label=, placeholder=. Not comments,
not variable names, not CSS.
"""

import re
from pathlib import Path

SRC = Path(r"D:/MAIB/Term - 3/Deep Learning/Collusion-Network-Detection/frontend/src")

JARGON = {
    "motif",
    "motifs",
    "subgraph",
    "sub-network",
    "node",
    "nodes",
    "edge",
    "edges",
    "attribution",
    "fidelity",
    "calibrated",
    "calibration",
    "prevalence",
    "inductive",
    "isotonic",
    "ensemble",
    "multiseed",
    "multi-seed",
    "seed",
    "auc",
    "auc-pr",
    "precision@k",
    "topology",
    "structural",
    "aggregation",
    "embedding",
    "embeddings",
    "attention",
    "inference",
    "artifact",
    "artifacts",
    "corpus",
    "heuristic",
    "amortized",
    "amortised",
    "leiden",
    "jaccard",
    "nms",
    "dedup",
    "deduplicated",
    "imputed",
    "channels",
    "regime",
    "budget",
    "ablation",
    "bootstrap",
    "significance",
    "quantile",
    "z-score",
    "k-core",
}


def user_strings(text: str):
    """Yield (line_no, string) for things a user reads."""
    for m in re.finditer(
        r'(?:title|label|placeholder|hint|message|subtitle)=\{?"([^"]{6,})"', text
    ):
        yield text[: m.start()].count("\n") + 1, m.group(1)
    # JSX text nodes: >...< with real words
    for m in re.finditer(r">\s*([A-Z][^<>{}\n]{14,})\s*<", text):
        yield text[: m.start()].count("\n") + 1, m.group(1)
    # multi-line JSX prose blocks
    for m in re.finditer(r"\n\s{10,}([A-Za-z][^<>{}\n]{25,})\n", text):
        yield text[: m.start()].count("\n") + 1, m.group(1)


hits = []
for p in sorted(SRC.rglob("*.tsx")):
    txt = p.read_text(encoding="utf-8")
    # strip block comments and // comments so we only judge shipped text
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    txt = re.sub(r"(?m)^\s*//.*$", "", txt)
    for ln, s in user_strings(txt):
        s2 = " ".join(s.split())
        words = {w.strip(".,;:()—-–\u2019's").lower() for w in s2.split()}
        found = sorted(words & JARGON)
        if found:
            hits.append((p.relative_to(SRC).as_posix(), ln, found, s2[:110]))

by_file = {}
for f, ln, found, s in hits:
    by_file.setdefault(f, []).append((ln, found, s))

total = 0
for f in sorted(by_file):
    print(f"\n{f}")
    for ln, found, s in by_file[f]:
        total += 1
        print(f"  L{ln:<4} [{','.join(found)}]  {s}")
print(f"\n{total} user-facing strings containing jargon")
