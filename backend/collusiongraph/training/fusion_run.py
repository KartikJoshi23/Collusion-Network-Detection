"""Calibrated fusion of stored supervised members (revision brief item B2).

The published ensemble fuses GATv2 with unsupervised members only. The brief
asks why the strongest model, the B3 tree, was left out. This runner fuses
supervised members from stored score files with the same isotonic
``calibrated_fusion`` the ensemble uses, so the comparison changes one thing:
which members are fused.

Calibration needs out-of-sample validation scores. GATv2 brings its own
(``scores_val.parquet``: confirmed nodes in steps loss_end+1 .. train_end,
scored on the train graph). A tree member must therefore be trained on steps
up to ``loss_end`` and scored on every later step. One score file per member
and seed then covers both the validation window and the test window, and this
runner splits it by ``time_first_seen``.

Every member, and the fusion, is evaluated on the same test nodes: those that
every member scored. Nothing is retrained here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from collusiongraph.eval import load_config, run_eval
from collusiongraph.models.ensemble import calibrated_fusion
from collusiongraph.schema import GraphStore, Label

_TIME = "time_first_seen"


def _member_frames(
    spec: dict[str, Any], seed: int, val_ids: pl.Series, test_ids: pl.Series
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(validation, test) score frames for one member and seed."""
    if "scores" in spec:
        frame = pl.read_parquet(str(spec["scores"]).format(seed=seed)).select("node_id", "score")
        val = frame.filter(pl.col("node_id").is_in(val_ids.implode()))
        test = frame.filter(pl.col("node_id").is_in(test_ids.implode()))
    else:
        val = pl.read_parquet(str(spec["val"]).format(seed=seed)).select("node_id", "score")
        test = (
            pl.read_parquet(str(spec["test"]).format(seed=seed))
            .select("node_id", "score")
            .filter(pl.col("node_id").is_in(test_ids.implode()))
        )
    if val.height == 0 or test.height == 0:
        raise ValueError(f"member spec {spec} gave an empty validation or test pool (seed {seed})")
    return val, test


def run_supervised_fusion(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    cfg = load_config(config)
    if not cfg.get("supervised_fusion"):
        raise ValueError("run_supervised_fusion expects a config with supervised_fusion: true")
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    split = cfg["split"]
    loss_end, train_end, test_start = split["loss_end"], split["train_end"], split["test_start"]
    if not loss_end < train_end < test_start:
        raise ValueError("split must satisfy loss_end < train_end < test_start")
    seeds = [int(s) for s in cfg["seeds"]]
    members_spec: dict[str, dict[str, Any]] = cfg["members"]
    if len(members_spec) < 2:
        raise ValueError("a fusion needs at least two members")
    out_root = Path(cfg["output_dir"])

    nodes = store.read(dataset, "nodes").select("node_id", _TIME)
    labels = store.read(dataset, "labels")
    val_ids = nodes.filter((pl.col(_TIME) > loss_end) & (pl.col(_TIME) <= train_end))["node_id"]
    test_ids = nodes.filter(pl.col(_TIME) >= test_start)["node_id"]
    val_labels = labels.filter(
        pl.col("label").is_in([Label.ILLICIT.value, Label.LICIT.value])
    ).select("node_id", (pl.col("label") == Label.ILLICIT.value).cast(pl.Int8).alias("y"))

    per_seed: list[dict[str, Any]] = []
    for seed in seeds:
        members_val: dict[str, pl.DataFrame] = {}
        members_test: dict[str, pl.DataFrame] = {}
        for name, spec in members_spec.items():
            members_val[name], members_test[name] = _member_frames(spec, seed, val_ids, test_ids)
        common = set.intersection(*(set(f["node_id"].to_list()) for f in members_test.values()))
        common_ids = pl.Series(sorted(common), dtype=pl.Utf8)
        members_test = {
            n: f.filter(pl.col("node_id").is_in(common_ids.implode()))
            for n, f in members_test.items()
        }
        fused = calibrated_fusion(members_test, members_val, val_labels)

        seed_dir = out_root / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Any] = {}
        for name, frame in {**members_test, "fused": fused}.items():
            path = seed_dir / f"scores_{name}.parquet"
            frame.write_parquet(path)
            metrics = run_eval(
                {
                    "dataset": dataset,
                    "store_root": str(store.root),
                    "budgets": cfg["budgets"],
                    "node_scores": str(path),
                    "output_dir": str(seed_dir / name),
                }
            )
            results[name] = metrics["node_level"]
        per_seed.append({"seed": seed, "n_test_nodes": len(common), "results": results})

    aggregate: dict[str, Any] = {}
    for name in [*members_spec, "fused"]:
        rows = [p["results"][name] for p in per_seed]
        keys = [
            k
            for k, v in rows[0].items()
            if isinstance(v, (int, float)) and (k == "auc_pr" or "@" in k)
        ]
        entry: dict[str, Any] = {"auc_pr_per_seed": [r["auc_pr"] for r in rows]}
        for key in keys:
            values = [r[key] for r in rows]
            entry[f"{key}_mean"] = float(np.mean(values))
            entry[f"{key}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        aggregate[name] = entry
    report = {
        "kind": "supervised_fusion_multiseed",
        "dataset": dataset,
        "seeds": seeds,
        "split": split,
        "members": list(members_spec),
        "prevalence_baseline": per_seed[0]["results"]["fused"]["prevalence_baseline"],
        "n_confirmed": per_seed[0]["results"]["fused"]["n_confirmed"],
        "per_seed": per_seed,
        "aggregate": aggregate,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "fusion_multiseed.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
