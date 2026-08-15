"""Find bare parameter choices in the report — every specific number stated as
a decision ("2 layers", "5 seeds", "0.5 threshold") is a place an evaluator asks
'why that value?'. List them so we can check each one is justified."""

import re
from pathlib import Path

tex = Path(
    r"D:/MAIB/Term - 3/Deep Learning/Collusion-Network-Detection/docs/internal_report/collusiongraph_internal_report.tex"
).read_text(encoding="utf-8")

# strip comments + tables (tables are results, not choices)
body = re.sub(r"(?m)^\s*%.*$", "", tex)

PATTERNS = [
    (r"\b(\d+)\s+layers?\b", "layer count"),
    (r"\b(\d+)\s+seeds?\b", "seed count"),
    (r"\b(\d+)\s+hops?\b", "hop count"),
    (r"\bcap(?:ped)?\s+(?:at\s+)?(\d+)\b", "size cap"),
    (r"\bJaccard[^.]{0,40}?(0\.\d+)", "dedup threshold"),
    (r"\btop[- ](\d+)\b", "budget/top-k"),
    (r"\bk\s*=\s*(\d+)", "budget k"),
    (r"\b(\d+)\s+attention heads\b", "attention heads"),
    (r"\b(\d+)\s+hidden units\b", "hidden units"),
    (r"\bthreshold[^.]{0,30}?(0\.\d+)", "threshold"),
    (r"\b(\d+)%\s+of\s+members\b", "member fraction"),
]

TERMS_THAT_JUSTIFY = (
    "because",
    "why",
    "reason",
    "so that",
    "chosen",
    "convention",
    "measured",
    "we tested",
    "bounds",
)

print("PARAMETER CHOICES STATED IN THE REPORT")
print("(checking whether a justification word appears within ~400 chars)\n")
seen = set()
for pat, what in PATTERNS:
    for m in re.finditer(pat, body, re.I):
        val = m.group(1)
        key = (what, val)
        if key in seen:
            continue
        seen.add(key)
        window = body[max(0, m.start() - 200) : m.end() + 400].lower()
        justified = any(t in window for t in TERMS_THAT_JUSTIFY)
        snippet = " ".join(body[max(0, m.start() - 60) : m.end() + 70].split())
        mark = "OK " if justified else "?? "
        print(f"{mark} {what:<18} = {val:<6} …{snippet[:96]}…")

print()
print("?? = no justification word nearby — candidate for an evaluator's 'why that value?'")
