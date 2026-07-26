"""Find machine-learning jargon in text a HUMAN actually receives.

Two passes:

1. THE SCREEN — user-facing strings in the console: JSX text, title=, label=,
   placeholder=. Not comments, not variable names, not CSS.
2. THE SPOKEN SCRIPTS — the `> **SAY THIS**` blocks in
   docs/presentation_script_*.md. These are read ALOUD to an evaluator, so they
   are held to a stricter bar than the screen: no jargon at all (the screen
   list plus the brief's banned vocabulary), no printed decimals ("about a
   third", never "0.32"), no bullet lists (nobody speaks bullet points), and no
   sentence long enough to run the speaker out of breath.

Exit code is 1 if any SAY THIS violation exists; the screen count is reported
but does not fail, because its five remaining hits are accepted (chart axis
labels where the metric's real name belongs — see scripts/audit/README.md).
"""

import re
import sys
from pathlib import Path

ROOT = Path(r"D:/MAIB/Term - 3/Deep Learning/Collusion-Network-Detection")
SRC = ROOT / "frontend" / "src"
DOCS = ROOT / "docs"

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
    # SHORT JSX text nodes too. The rule above wanted a capital and 14+ chars,
    # which is how the alert queue shipped a slider labelled "budget k" through
    # a whole plain-English pass: eight lowercase characters, invisible to the
    # audit that was supposed to be measuring exactly this.
    for m in re.finditer(r">\s*([A-Za-z][^<>{}\n]{2,13})\s*<", text):
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

print("=" * 70)
print("PASS 1 — text on the screen")
print("=" * 70)
total = 0
for f in sorted(by_file):
    print(f"\n{f}")
    for ln, found, s in by_file[f]:
        total += 1
        print(f"  L{ln:<4} [{','.join(found)}]  {s}")
print(f"\n{total} user-facing strings containing jargon")


# ------------------------------------------------------------- spoken pass
# docs/presentation_scripts_brief.md §4. The screen list above is the floor;
# these are the extra words that only ever surface in a spoken explanation.
SPOKEN_ONLY = {
    "precision@k",
    "recall@k",
    "roc-auc",
    "multi-seed",
    "leiden",
    "jaccard",
    "isotonic",
    "inductive",
    "amortized",
    "amortised",
    "stochastic",
    "hyperparameter",
    "hyperparameters",
    "gnn",
    "gnns",
    "pgexplainer",
    "gnnexplainer",
    "loco",
    "lomo",
    "parquet",
    "typology",
    "typologies",
}
SPOKEN_BANNED = JARGON | SPOKEN_ONLY

SENTENCE_WORD_CAP = 30  # a spoken sentence longer than this loses the room
STRIP = ".,;:!?()[]\"“”—-–’'s"


def say_this_blocks(text: str):
    r"""Yield (line_no, block_text) for every spoken block.

    Two shapes, because the scripts moved from Markdown to LaTeX on
    2026-07-25 when the stakeholder asked for the reference slide format:
    a `> **SAY THIS**` blockquote, or a `\begin{saythis}` environment.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if re.match(r"^\s*>\s*\*\*SAY THIS\*\*", lines[i]):
            start, body = i + 1, []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                body.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            yield start, "\n".join(body)
        elif re.match(r"^\s*\\begin\{saythis\}", lines[i]):
            start, body = i + 1, []
            i += 1
            while i < len(lines) and not re.match(r"^\s*\\end\{saythis\}", lines[i]):
                body.append(lines[i])
                i += 1
            yield start, strip_tex("\n".join(body))
        else:
            i += 1


def strip_tex(s: str) -> str:
    r"""Reduce a LaTeX spoken block to the words that are actually said.

    Stage directions (\stage{...}) are removed entirely — they are things the
    speaker DOES, not words. Everything else keeps its argument text.
    """
    s = re.sub(r"\\stage\{[^{}]*\}", "", s)  # [click the switch]
    s = re.sub(r"\\bt\b", " ", s)  # breath marker
    s = re.sub(r"\\blank\b", "NAME", s)  # the fill-in-your-name rule
    s = re.sub(r"\\textbullet\b", "", s)
    s = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r"\1", s)  # \emph{x} -> x
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)  # bare macros
    s = s.replace("---", "—").replace("``", '"').replace("''", '"')
    return re.sub(r"[{}]", "", s)


def script_pass() -> int:
    files = sorted(DOCS.glob("presentation_script_*.md")) + sorted(
        (DOCS / "presentation_scripts").glob("*.tex")
    )
    if not files:
        print("\nno presentation scripts found — spoken pass skipped")
        return 0

    violations = 0
    for p in files:
        print(f"\n{p.relative_to(ROOT).as_posix()}")
        n_blocks = 0
        for ln, block in say_this_blocks(p.read_text(encoding="utf-8")):
            n_blocks += 1
            flat = " ".join(block.split())

            words = {w.strip(STRIP).lower() for w in flat.split()}
            hit = sorted(words & SPOKEN_BANNED)
            if hit:
                violations += 1
                print(f"  L{ln:<5} JARGON [{','.join(hit)}]  {flat[:88]}")

            # a spoken number is "about a third", never "0.32"
            for dec in sorted(set(re.findall(r"\d+\.\d+", flat))):
                violations += 1
                print(f"  L{ln:<5} PRINTED NUMBER [{dec}] — say it in words")

            # nobody speaks bullet points
            for raw in block.splitlines():
                if re.match(r"^\s*(?:[-*•]\s|\d+[.)]\s)", raw):
                    violations += 1
                    print(f"  L{ln:<5} LIST  {raw.strip()[:80]}")

            for sentence in re.split(r"(?<=[.!?])\s+", flat):
                n_words = len(sentence.split())
                if n_words > SENTENCE_WORD_CAP:
                    violations += 1
                    print(f"  L{ln:<5} LONG ({n_words} words)  {sentence[:88]}")

        print(f"  {n_blocks} SAY THIS blocks scanned")
    print(f"\n{violations} spoken-script violations")
    return violations


print()
print("=" * 70)
print("PASS 2 — text read aloud (SAY THIS blocks)")
print("=" * 70)
sys.exit(1 if script_pass() else 0)
