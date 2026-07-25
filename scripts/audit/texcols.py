import re
import sys
from pathlib import Path

path = sys.argv[1]
src = Path(path).read_text(encoding="utf-8")


def balanced(text, i):
    """text[i] == '{'; return (content, index_after_close)."""
    depth, start = 0, i
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return "", i


def count_cols(spec):
    """Count actual column entries in a tabular preamble."""
    n, i = 0, 0
    while i < len(spec):
        c = spec[i]
        if c in "lcr":
            n += 1
            i += 1
        elif c in "pmb" and i + 1 < len(spec) and spec[i + 1] == "{":
            _, i = balanced(spec, i + 1)
            n += 1
        elif c in "@!>" and i + 1 < len(spec) and spec[i + 1] == "{":
            _, i = balanced(spec, i + 1)  # not a column
        elif c == "|" or c.isspace():
            i += 1
        else:
            i += 1
    return n


bad = 0
for m in re.finditer(r"\\begin\{(tabular|longtable)\}", src):
    i = m.end()
    if i < len(src) and src[i] == "[":
        i = src.index("]", i) + 1
    while i < len(src) and src[i].isspace():
        i += 1
    spec, after = balanced(src, i)
    ncol = count_cols(spec)

    endm = re.search(r"\\end\{" + m.group(1) + r"\}", src[after:])
    body = src[after : after + endm.start()] if endm else ""
    line_no = src[: m.start()].count("\n") + 1

    worst, worst_row = 0, ""
    for row in re.split(r"\\\\", body):
        if "&" not in row:
            continue
        r2 = re.sub(
            r"\\multicolumn\{(\d+)\}",
            lambda mm: "&" * (int(mm.group(1)) - 1) + "\\multicolumn{1}",
            row,
        )
        c = r2.count("&") + 1
        if c > worst:
            worst, worst_row = c, " ".join(row.split())[:70]
    status = "OK" if worst <= ncol else "MISMATCH"
    if worst > ncol:
        bad += 1
        print(f"  line {line_no:>4} {m.group(1):<10} declared={ncol} widest_row={worst}  {status}")
        print(f"       -> {worst_row}")

print(f"\ntables with column mismatches: {bad}")
