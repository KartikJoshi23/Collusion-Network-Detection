import re
import sys
from collections import Counter
from pathlib import Path

path = sys.argv[1]
src = Path(path).read_text(encoding="utf-8")

# strip comment lines for structural checks
lines = src.split("\n")

s = re.sub(r"\\[{}]", "", src)
print("brace balance (0 = ok):", s.count("{") - s.count("}"))

begins = re.findall(r"\\begin\{([A-Za-z]+\*?)\}", src)
ends = re.findall(r"\\end\{([A-Za-z]+\*?)\}", src)
b, e = Counter(begins), Counter(ends)
diff = {k: b[k] - e[k] for k in set(b) | set(e) if b[k] != e[k]}
print("unmatched environments:", diff or "none")

stack, bad = [], []
for m in re.finditer(r"\\(begin|end)\{([A-Za-z]+\*?)\}", src):
    if m.group(1) == "begin":
        stack.append(m.group(2))
    else:
        if not stack or stack[-1] != m.group(2):
            bad.append((m.group(2), stack[-1] if stack else None))
        elif stack:
            stack.pop()
print("nesting errors:", bad or "none")
print("left open:", stack or "none")

# packages used vs loaded
loaded = set(re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]*)\}", src))
loaded = {p.strip() for grp in loaded for p in grp.split(",")}
print("packages loaded:", len(loaded))

# commands defined
defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", src))
defined |= set(re.findall(r"\\newtcolorbox\{([A-Za-z]+)\}", src))
print("custom macros/envs defined:", sorted(defined))

# custom envs actually used must be defined
custom_env_used = {x for x in set(begins) if x in ("plain", "keybox", "warnbox")}
missing = custom_env_used - defined
print("custom envs used but undefined:", missing or "none")

# bare specials outside code/math
problems = []
for i, line in enumerate(lines, 1):
    if line.lstrip().startswith("%"):
        continue
    t = re.sub(r"\\(?:code|texttt|url|href)\{[^{}]*\}", "", line)
    t = re.sub(r"\$[^$]*\$", "", t)
    t = re.sub(r"%.*$", "", t)
    t = re.sub(r"\\[%&#_$~^]", "", t)
    for ch in ["_", "#"]:
        if ch in t:
            problems.append((i, ch, line.strip()[:80]))
    # bare & outside tabular/longtable rows is fine to skip; check # and _
print("bare special chars outside code/math:", problems or "none")

# label/ref consistency
labels = set(re.findall(r"\\label\{([^}]*)\}", src))
refs = set(re.findall(r"\\ref\{([^}]*)\}", src))
print("refs with no label:", (refs - labels) or "none")

# tabular column counts vs rows
print("\n--- tabular/longtable column sanity ---")
for m in re.finditer(r"\\begin\{(tabular|longtable)\}(?:\[[^\]]*\])?\{([^}]*)\}", src):
    spec = m.group(2)
    ncol = len(re.findall(r"[lcr]|p\{[^}]*\}|>\{[^}]*\}", spec.replace("@{}", "")))
    ncol = len(re.findall(r"p\{[^}]*\}|[lcr]", spec))
    start = m.end()
    endm = re.search(r"\\end\{" + m.group(1) + r"\}", src[start:])
    body = src[start : start + endm.start()] if endm else ""
    line_no = src[: m.start()].count("\n") + 1
    maxcols = 0
    for row in body.split(r"\\"):
        row_clean = re.sub(r"\\multicolumn\{(\d+)\}\{[^}]*\}\{[^{}]*\}", "X", row)
        if (
            any(k in row for k in ("toprule", "midrule", "bottomrule", "endhead", "addlinespace"))
            and "&" not in row
        ):
            continue
        c = row_clean.count("&") + 1
        maxcols = max(maxcols, c)
    flag = "OK" if maxcols <= ncol else "!! TOO MANY"
    print(f"  line {line_no:>4} {m.group(1):<10} declared={ncol} max_row_cols={maxcols}  {flag}")
