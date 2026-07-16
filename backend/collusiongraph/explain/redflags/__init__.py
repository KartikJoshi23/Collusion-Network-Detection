"""Curated red-flag vocabularies (§4.4): FATF (financial), OECD (procurement).

The only domain-specific artifacts besides the adapters. ``map_red_flags``
turns matcher output into resolvable indicator citations — a red flag that
does not resolve to a curated indicator is unconstructable (§9.1 invariant).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from collusiongraph.explain.motif_matcher import MotifMatch

_DIR = Path(__file__).parent
_FRAMEWORK_FILES = {"financial": "fatf.yaml", "procurement": "oecd.yaml"}


def load_indicators(domain: str) -> dict:
    filename = _FRAMEWORK_FILES.get(domain)
    if filename is None:
        raise ValueError(f"unknown domain {domain!r}")
    return yaml.safe_load((_DIR / filename).read_text(encoding="utf-8"))


def map_red_flags(matches: list[MotifMatch], domain: str) -> list[dict]:
    """Motif matches → red-flag citations {framework, indicator_id,
    indicator_text, matched_because}, §4.4 bundle schema.

    One citation per indicator (audit F9): a dense subgraph with dozens of
    cycle instances yields ONE round-tripping flag carrying the instance
    count, not dozens of duplicate citations."""
    table = load_indicators(domain)
    flags: dict[str, dict] = {}
    counts: dict[str, int] = {}
    for match in matches:
        for indicator in table["indicators"]:
            if match.motif_type in indicator["motifs"]:
                key = indicator["id"]
                counts[key] = counts.get(key, 0) + 1
                if key not in flags:
                    flags[key] = {
                        "framework": table["framework"],
                        "indicator_id": key,
                        "indicator_text": indicator["text"].strip(),
                        "matched_because": match.because(),
                    }
    for key, flag in flags.items():
        if counts[key] > 1:
            flag["matched_because"] += f" [+{counts[key] - 1} more instances]"
    return list(flags.values())
