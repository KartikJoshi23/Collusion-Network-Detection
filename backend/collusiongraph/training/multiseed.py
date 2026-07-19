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


def run_ensemble_multiseed(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """§7 step 29: multi-seed rerun of the M3 ensemble. Per seed,
    ``run_ensemble`` runs with ``seed=s`` (driving the unsupervised member
    refits) and ``supervised_scores_dir=<supervised_scores_root>/seed_<s>`` —
    the supervised member REUSES the GATv2 multi-seed campaign's per-seed
    scores instead of retraining. Resumable: ``ensemble_report.json`` is
    ``run_ensemble``'s last artifact, so it is the completion marker.
    Aggregates mean ± std AUC-PR per member (fusions included) into
    ``ensemble_multiseed.json``."""
    from .ensemble_run import run_ensemble

    cfg = load_config(config)
    if not cfg.get("ensemble_multiseed"):
        raise ValueError("run_ensemble_multiseed expects a config with ensemble_multiseed: true")
    seeds = [int(s) for s in cfg["seeds"]]
    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate entries in seeds")
    out_root = Path(cfg["output_dir"])
    supervised_root = Path(cfg["supervised_scores_root"])
    base = {
        k: v
        for k, v in cfg.items()
        if k
        not in (
            "ensemble_multiseed",
            "seeds",
            "seed",
            "output_dir",
            "supervised_scores_root",
            "supervised_scores_dir",
        )
    }

    reports: list[dict[str, Any]] = []
    for seed in seeds:
        supervised_dir = supervised_root / f"seed_{seed}"
        if not (supervised_dir / "scores_test.parquet").is_file():
            raise ValueError(
                f"supervised member scores missing for seed {seed}: {supervised_dir} — "
                "run the GNN multi-seed campaign first"
            )
        seed_dir = out_root / f"seed_{seed}"
        marker = seed_dir / "ensemble_report.json"
        if marker.is_file():
            report = json.loads(marker.read_text(encoding="utf-8"))
            if report.get("seed") != seed:
                raise ValueError(
                    f"refusing to resume {seed_dir}: existing report is from "
                    f"seed {report.get('seed')}"
                )
            reports.append(report)
            continue
        reports.append(
            run_ensemble(
                {
                    **base,
                    "seed": seed,
                    "output_dir": str(seed_dir),
                    "supervised_scores_dir": str(supervised_dir),
                }
            )
        )

    member_names = sorted(reports[0]["members"])
    aggregate: dict[str, Any] = {}
    for name in member_names:
        values = [r["members"][name]["auc_pr"] for r in reports]
        aggregate[name] = {
            "auc_pr_per_seed": values,
            "auc_pr_mean": float(np.mean(values)),
            "auc_pr_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        }
    summary = {
        "kind": "ensemble_multiseed",
        "dataset": cfg["dataset"],
        "seeds": seeds,
        "members": aggregate,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "ensemble_multiseed.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def run_label_noise(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """§7 step 29 (iv): label-noise robustness curve — ``rates:`` × ``seeds:``,
    each point an ordinary ``train_gnn`` run with ``label_noise`` injected
    (TRAIN labels only; evaluation reads stored labels — pinned by test).
    Resumable exactly like ``run_multiseed``; aggregates mean ± std AUC-PR per
    rate into ``noise_curve.json``. Include rate 0.0 as the clean anchor."""
    cfg = load_config(config)
    if not cfg.get("label_noise_curve"):
        raise ValueError("run_label_noise expects a config with label_noise_curve: true")
    rates = [float(r) for r in cfg["rates"]]
    if len(set(rates)) != len(rates):
        raise ValueError("duplicate entries in rates")
    seeds = [int(s) for s in cfg.get("seeds", [cfg.get("seed", 0)])]
    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate entries in seeds")
    out_root = Path(cfg["output_dir"])
    base = {
        k: v
        for k, v in cfg.items()
        if k not in ("label_noise_curve", "rates", "seeds", "seed", "output_dir", "label_noise")
    }

    curve: list[dict[str, Any]] = []
    for rate in rates:
        records: list[dict[str, Any]] = []
        for seed in seeds:
            run_dir = out_root / f"rate_{rate}_seed_{seed}"
            marker = run_dir / "run.json"
            if marker.is_file():
                record = json.loads(marker.read_text(encoding="utf-8"))
                stored_rate = record.get("label_noise", {}).get("rate", 0.0)
                if record.get("seed") != seed or stored_rate != rate:
                    raise ValueError(
                        f"refusing to resume {run_dir}: run.json is from a different "
                        f"grid point (seed {record.get('seed')}, rate {stored_rate})"
                    )
                records.append(record)
                continue
            records.append(
                train_gnn(
                    {
                        **base,
                        "seed": seed,
                        "output_dir": str(run_dir),
                        "label_noise": {"rate": rate, "seed": seed},
                    }
                )
            )
        aucs = [r["node_level"]["auc_pr"] for r in records]
        curve.append(
            {
                "rate": rate,
                "n_flipped": records[0].get("label_noise", {}).get("n_flipped", 0),
                "auc_pr_per_seed": aucs,
                "auc_pr_mean": float(np.mean(aucs)),
                "auc_pr_std": float(np.std(aucs, ddof=1)) if len(aucs) > 1 else 0.0,
                "val_auc_pr_mean": float(np.mean([r["best_val_auc_pr"] for r in records])),
            }
        )

    report = {
        "kind": "label_noise_curve",
        "dataset": cfg["dataset"],
        "model": cfg.get("model", {}).get("name"),
        "rates": rates,
        "seeds": seeds,
        "curve": curve,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "noise_curve.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
