"""Find terms used in the report that are never defined in the Glossary."""

import re
from pathlib import Path

tex = Path(
    r"D:/MAIB/Term - 3/Deep Learning/Collusion-Network-Detection/docs/internal_report/collusiongraph_internal_report.tex"
).read_text(encoding="utf-8")

# glossary spans from the Glossary section to the next \section
gstart = tex.index(r"\section{Glossary")
gend = tex.index(r"\section{", gstart + 10)
glossary = tex[gstart:gend]
body = tex[:gstart] + tex[gend:]

# terms bolded in the glossary = the defined set
defined = set()
for m in re.finditer(r"\\textbf\{([^{}]*)\}", glossary):
    t = re.sub(r"\\[a-zA-Z]+|[{}\\]", "", m.group(1)).strip()
    defined.add(t.lower())
    # also index the parenthetical alias, e.g. "Graph (network)"
    for part in re.findall(r"\(([^)]*)\)", t):
        defined.add(part.strip().lower())
    defined.add(re.sub(r"\s*\([^)]*\)", "", t).strip().lower())

# candidate jargon in the body: all-caps acronyms 2-9 chars, and known terms
acronyms = set()
for m in re.finditer(r"\b([A-Z][A-Za-z]*(?:-[A-Z][A-Za-z]*)?)\b", body):
    w = m.group(1)
    if len(w) < 2:
        continue
    # acronym-ish: mostly uppercase
    caps = sum(1 for c in w if c.isupper())
    if caps >= 2 and caps / len(w.replace("-", "")) > 0.5:
        acronyms.add(w)

STOP = {
    "CollusionGraph",
    "The",
    "A",
    "In",
    "We",
    "It",
    "If",
    "This",
    "And",
    "But",
    "AWS",
    "PDF",
    "JSON",
    "CSV",
    "HTML",
    "CSS",
    "URL",
    "OK",
    "AI",
    "US",
    "EU",
    "UAE",
    "IBM",
    "PC",
    "GPU",
    "CPU",
    "TLS",
    "DNS",
    "HTTPS",
    "REST",
    "SQL",
    "API",
    "UI",
    "V1",
    "V2",
    "V3",
    "V4",
    "RGB",
    "SVG",
    "PNG",
    "ID",
    "IDs",
    "II",
    "III",
    "IV",
}
acronyms -= STOP

missing = sorted(a for a in acronyms if a.lower() not in defined)

print("=== ACRONYMS / TERMS USED IN BODY BUT NOT DEFINED IN GLOSSARY ===")
for a in missing:
    n = len(re.findall(r"\b" + re.escape(a) + r"\b", body))
    # first use, for context
    m = re.search(r"[^.\n]*\b" + re.escape(a) + r"\b[^.\n]*", body)
    ctx = " ".join(m.group(0).split())[:95] if m else ""
    print(f"  {a:<16} x{n:<3} {ctx}")

print(f"\n{len(missing)} undefined terms")
print(f"{len(defined)} glossary entries")

# readability probe: long sentences in the body
print("\n=== LONGEST SENTENCES (candidates for simplification) ===")
prose = re.sub(r"\\begin\{(longtable|tabular)\}.*?\\end\{\1\}", "", body, flags=re.S)
prose = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", prose)
prose = re.sub(r"[{}%&$\\]", " ", prose)
sents = [" ".join(s.split()) for s in re.split(r"(?<=[.!?])\s+", prose)]
sents = [s for s in sents if len(s.split()) > 5]
for s in sorted(sents, key=lambda x: -len(x.split()))[:12]:
    print(f"  [{len(s.split()):>3} words] {s[:110]}...")
