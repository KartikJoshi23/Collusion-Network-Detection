"""Check every result number in the paper against the artifact that holds it.

Reads ``paper/numbers_manifest.yaml``. Each entry names the printed value, the
artifact file (JSON, under the repository root), a key path into it and the
format used to print it. The checker recomputes the printed string from the
artifact and confirms that the string appears in the manuscript. It then lists
every decimal number in the manuscript body that no entry and no allowlist
item explains.

Key paths are dot-separated. ``*`` matches every key of a mapping or every
item of a list, and ``reduce`` (min, max, mean, sum, count) folds the matches
to one value. ``op`` combines the value with a second source ``b`` (sub, div,
add). ``scale`` multiplies the result (for example 100 for a percentage).

Usage::

    uv run python scripts/audit/verify_numbers.py            # report, exit 1 on any failure
    uv run python scripts/audit/verify_numbers.py --strict   # also fail on unlisted numbers

The artifacts are gitignored, so this runs on a machine that holds
``eval_outputs/``; it is not part of CI.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
# a leading minus counts unless it is the second dash of a range ("11.3--81.8")
NUMBER = re.compile(r"(?<![\w.])(?:(?<!-)-)?\d+\.\d+(?![\d])")


def resolve(obj: Any, path: str) -> list[Any]:
    """All values at a dot path; ``*`` fans out over mappings and lists."""
    current = [obj]
    for part in path.split("."):
        nxt: list[Any] = []
        for node in current:
            if part == "*":
                nxt.extend(node.values() if isinstance(node, dict) else node)
            elif isinstance(node, list):
                nxt.append(node[int(part)])
            else:
                nxt.append(node[part])
        current = nxt
    return current


REDUCERS = {
    "min": min,
    "max": max,
    "mean": statistics.mean,
    "stdev": statistics.stdev,
    "sum": sum,
    "count": len,
}


def value_of(source: dict[str, Any], cache: dict[str, Any]) -> float:
    path = source["file"]
    if path not in cache:
        cache[path] = json.loads((REPO / path).read_text(encoding="utf-8"))
    values = resolve(cache[path], str(source["key"]))
    if "reduce" in source:
        return float(REDUCERS[source["reduce"]](values))
    if len(values) != 1:
        raise ValueError(f"{source['key']} matched {len(values)} values; add a reduce")
    return float(values[0])


def compute(entry: dict[str, Any], cache: dict[str, Any]) -> float:
    value = value_of(entry, cache)
    if "op" in entry:
        other = value_of(entry["b"], cache)
        value = {"sub": value - other, "div": value / other, "add": value + other}[entry["op"]]
    return value * float(entry.get("scale", 1))


LENGTH = re.compile(
    r"\d*\.?\d+(?:pt|em|ex|mm|cm|in|bp)\b|\d*\.?\d+\\(?:textwidth|columnwidth|linewidth)"
)


URL = re.compile(r"\\url\{[^}]*\}")
BIBLIOGRAPHY = (r"\begin{thebibliography}", r"\bibliography{")


def manuscript_body(tex: str) -> str:
    """The text between \\begin{document} and the bibliography (an inline
    thebibliography or a BibTeX \\bibliography{}), with comments, URLs and
    LaTeX lengths (2.5pt, 0.94\\textwidth) removed."""
    start = tex.index(r"\begin{document}")
    end = min(tex.index(marker, start) for marker in BIBLIOGRAPHY if marker in tex[start:])
    kept = []
    for line in tex[start:end].splitlines():
        cut = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        kept.append(LENGTH.sub(" ", URL.sub(" ", cut)))
    return "\n".join(kept)


def expand(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups share ``file`` (and optionally fmt, reduce, scale) across
    ``items``; each item carries its own id, printed value and key."""
    out: list[dict[str, Any]] = []
    for entry in entries:
        if "items" not in entry:
            out.append(entry)
            continue
        shared = {k: v for k, v in entry.items() if k not in ("items", "id")}
        for item in entry["items"]:
            out.append({**shared, **item, "id": f"{entry['id']}.{item['id']}"})
    return out


def check(manifest_path: Path, tex_path: Path) -> tuple[list[str], list[str]]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    body = manuscript_body(tex_path.read_text(encoding="utf-8"))
    present = NUMBER.findall(body)
    cache: dict[str, Any] = {}
    failures: list[str] = []
    explained: set[str] = set()
    for entry in expand(manifest["numbers"]):
        printed = str(entry["v"])
        try:
            got = str(entry.get("fmt", "{:.4f}")).format(compute(entry, cache))
            if got.startswith("-") and float(got) == 0:
                got = got[1:]  # a rounded negative zero prints as 0
        except (KeyError, IndexError, ValueError, FileNotFoundError) as exc:
            failures.append(f"{entry['id']}: cannot read artifact ({exc})")
            continue
        if got != printed:
            failures.append(f"{entry['id']}: artifact gives {got}, manifest prints {printed}")
        if printed not in present:
            failures.append(f"{entry['id']}: {printed} not found in the manuscript")
        explained.add(printed)
    for item in manifest.get("allow", []):
        explained.update(str(v) for v in item["values"])
    unlisted = sorted({n for n in present if n not in explained}, key=lambda s: float(s))
    return failures, unlisted


MANUSCRIPTS = ("collusiongraph_paper.tex", "collusiongraph_paper_springer.tex")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default=str(REPO / "paper" / "numbers_manifest.yaml"))
    parser.add_argument(
        "--tex",
        action="append",
        help="manuscript to check (repeatable); default: the IEEE and Springer versions",
    )
    parser.add_argument("--strict", action="store_true", help="fail on unlisted numbers too")
    args = parser.parse_args()
    texs = args.tex or [
        str(REPO / "paper" / name) for name in MANUSCRIPTS if (REPO / "paper" / name).is_file()
    ]
    bad = False
    for tex in texs:
        failures, unlisted = check(Path(args.manifest), Path(tex))
        print(f"== {Path(tex).name}")
        for line in failures:
            print(f"FAIL  {line}")
        if unlisted:
            print(f"UNLISTED ({len(unlisted)}): {' '.join(unlisted)}")
        print(f"{len(failures)} failure(s), {len(unlisted)} unlisted number(s)")
        bad = bad or bool(failures) or (args.strict and bool(unlisted))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
