"""Serving index — which precomputed artifacts the API exposes (§3.2).

The API is read-only over batch outputs: a small JSON index maps each dataset
to its IR store, alert queue, explanation-bundle directory, and metrics files.
The index is produced by the batch side (or by hand) and mounted next to the
artifacts; the API never computes, trains, or writes. Serving code must never
import torch (deployment rule, docs/deployment.md §2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ServingEntry:
    dataset: str
    domain: str
    store_root: str
    alerts: str | None = None
    explanations: str | None = None
    metrics: list[str] = field(default_factory=list)
    # Phase-2 rigor artifacts (§7 steps 28–29, 32): name → JSON path
    # (multi-seed aggregates, transfer matrices, sensitivity sweeps,
    # label-noise / label-efficiency curves, significance tests)
    rigor: dict[str, str] = field(default_factory=dict)

    def store_dir(self) -> Path:
        return Path(self.store_root) / self.dataset


@dataclass(frozen=True)
class StressTestStudy:
    """One injection-recovery study (§7 step 30): fake cartels of known shapes
    planted into a real UNLABELED network, with measured recall per shape. Its
    home is the ``stress_test`` section of the index, NOT ``datasets`` — the
    substrate has no alert queue by construction, so it must never enter the
    domain/dataset machinery. ``recovery`` points at the injection artifact
    (multi-seed ``injection_multiseed.json`` or single-seed report)."""

    name: str
    title: str
    recovery: str
    reproduce: str = ""
    note: str = ""


@dataclass(frozen=True)
class ServingIndex:
    entries: dict[str, ServingEntry]
    stress_test: dict[str, StressTestStudy] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> ServingIndex:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = {
            name: ServingEntry(dataset=name, **spec)
            for name, spec in raw.get("datasets", {}).items()
        }
        stress = {
            name: StressTestStudy(name=name, **spec)
            for name, spec in raw.get("stress_test", {}).items()
        }
        return cls(entries=entries, stress_test=stress)

    def get(self, dataset: str) -> ServingEntry | None:
        return self.entries.get(dataset)

    def domains(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for name, entry in sorted(self.entries.items()):
            out.setdefault(entry.domain, []).append(name)
        return out


def write_serving_index(
    path: str | Path,
    entries: dict[str, dict],
    stress_test: dict[str, dict] | None = None,
) -> Path:
    """Helper for batch pipelines/tests: write a conforming index file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    index: dict[str, dict] = {"datasets": entries}
    if stress_test:
        index["stress_test"] = stress_test
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
