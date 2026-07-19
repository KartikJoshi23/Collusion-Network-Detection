"""§7 step 29 — multi-seed reruns of the headline GNN experiments.

``run_multiseed`` wraps ``train_gnn`` (v1 scope: the supervised GNN runner
only): one config + a ``seeds:`` list → per-seed runs under
``<output_dir>/seed_<s>/`` and a ``multiseed.json`` aggregate (mean ± std,
ddof=1). The published protocol is untouched — each seed run is an ordinary
``train_gnn`` call whose only differences are ``seed`` and ``output_dir``.

Resumable by design: ``train_gnn`` writes ``run.json`` as its LAST artifact,
so an existing ``seed_<s>/run.json`` is a completion marker — that seed is
loaded, not re-trained, and an interrupted campaign continues where it
stopped. A guard rejects resuming into a directory whose record disagrees
with the config (different dataset/model/features), so runs are never
silently mixed across protocols.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from collusiongraph.eval import load_config

from .trainer import train_gnn


def run_multiseed(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    if not cfg.get("multiseed"):
        raise ValueError("run_multiseed expects a config with multiseed: true")
    seeds = [int(s) for s in cfg["seeds"]]
    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate entries in seeds")
    out_root = Path(cfg["output_dir"])
    base = {k: v for k, v in cfg.items() if k not in ("multiseed", "seeds", "seed", "output_dir")}

    records: list[dict[str, Any]] = []
    for seed in seeds:
        seed_dir = out_root / f"seed_{seed}"
        marker = seed_dir / "run.json"
        if marker.is_file():
            record = json.loads(marker.read_text(encoding="utf-8"))
            expected = {
                "dataset": cfg["dataset"],
                "model": cfg.get("model", {}).get("name"),
                "features": cfg.get("features", "raw"),
                "seed": seed,
            }
            found = {
                "dataset": record.get("dataset"),
                "model": record.get("model", {}).get("name"),
                "features": record.get("features"),
                "seed": record.get("seed"),
            }
            if found != expected:
                raise ValueError(
                    f"refusing to resume {seed_dir}: existing run.json is from a "
                    f"different protocol ({found} != {expected})"
                )
            records.append(record)
            continue
        records.append(train_gnn({**base, "seed": seed, "output_dir": str(seed_dir)}))

    node_keys = [
        k
        for k, v in records[0]["node_level"].items()
        if isinstance(v, (int, float)) and (k == "auc_pr" or "@" in k)
    ]
    aggregate: dict[str, Any] = {}
    for key in node_keys:
        values = [r["node_level"][key] for r in records]
        aggregate[f"{key}_mean"] = float(np.mean(values))
        aggregate[f"{key}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    report = {
        "kind": "multiseed_gnn",
        "dataset": cfg["dataset"],
        "model": cfg.get("model", {}).get("name"),
        "features": cfg.get("features", "raw"),
        "seeds": seeds,
        "n_confirmed": records[0]["node_level"]["n_confirmed"],
        "prevalence_baseline": records[0]["node_level"]["prevalence_baseline"],
        "per_seed": [
            {
                "seed": r["seed"],
                "best_val_auc_pr": r["best_val_auc_pr"],
                "epochs_run": r["epochs_run"],
                "train_seconds": r["train_seconds"],
                "auc_pr": r["node_level"]["auc_pr"],
            }
            for r in records
        ],
        "aggregate": aggregate,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "multiseed.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
