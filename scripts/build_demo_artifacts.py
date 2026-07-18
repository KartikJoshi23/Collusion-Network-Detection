"""Produce the artifacts the demo dashboard serves (§7 step 25, M5).

Given the IR stores (`poe data` + `collusiongraph ingest`) and GNN score runs,
this builds the two alert queues the serving index points at and writes a
fresh `eval_outputs/serving.json`. It is intentionally tolerant: a dataset
whose score run is absent on this machine is skipped with a note, so the demo
still comes up on whatever artifacts exist.

Run before `docker compose up` (or `poe demo`). Artifacts are gitignored and
regenerated per machine — only the code and configs travel in git.
"""

from __future__ import annotations

import json
from pathlib import Path

from collusiongraph.training import build_alert_queue

REPO = Path(__file__).resolve().parents[1]
EVAL = REPO / "eval_outputs"

# (dataset, domain, score_run, queue_out, split, budgets, extra) — score runs
# are whatever this machine has produced; edit to match local run dirs.
DEMOS = [
    {
        "dataset": "elliptic_pp",
        "domain": "financial",
        "scores_dir": "eval_outputs/elliptic_pp/gnn_gatv2_focal_multi",
        "output_dir": "eval_outputs/elliptic_pp/alert_queue_ensemble",
        "model_run_id": "gatv2_multi_s0",
        "split": {"test_start": 35, "train_end": 34},
        "budgets": [50, 100, 200],
        "metrics": ["eval_outputs/elliptic_pp/gnn_gatv2_focal_multi/metrics.json"],
    },
    {
        "dataset": "mendeley_eu",
        "domain": "procurement",
        "scores_dir": "eval_outputs/mendeley_eu/gnn_sage_structural_src",
        "output_dir": "eval_outputs/mendeley_eu/alert_queue",
        "model_run_id": "sage_struct_s0",
        "split": {"test_start": 2014, "train_end": 2013},
        "budgets": [4, 18, 36],
        "train_label_policy": "mendeley_as_of",
        "metrics": ["eval_outputs/mendeley_eu/transfer_loco_country_5/metrics.json"],
    },
]


def main() -> int:
    serving: dict[str, dict] = {}
    for spec in DEMOS:
        scores = REPO / spec["scores_dir"]
        if not (scores / "scores_test.parquet").is_file():
            print(f"skip {spec['dataset']}: no score run at {spec['scores_dir']}")
            continue
        cfg = {
            "dataset": spec["dataset"],
            "domain": spec["domain"],
            "store_root": "data/interim",
            "scores_dir": spec["scores_dir"],
            "output_dir": spec["output_dir"],
            "model_run_id": spec["model_run_id"],
            "seed": 0,
            "split": spec["split"],
            "resolution": 1.0,
            "min_community_size": 2,
            "top_p": 0.25,
            "budgets": spec["budgets"],
        }
        if "train_label_policy" in spec:
            cfg["train_label_policy"] = spec["train_label_policy"]
        summary = build_alert_queue(cfg)
        print(f"{spec['dataset']}: {summary['n_alerts']} alerts")

        expl = REPO / "eval_outputs" / spec["dataset"] / "explanations"
        # the queue's own metrics ride along: the alert-level precision@budget
        # block feeds the dashboard's measured precision readout (§5.3 view 2)
        metrics = [*spec["metrics"], f"{spec['output_dir']}/metrics.json"]
        serving[spec["dataset"]] = {
            "domain": spec["domain"],
            "store_root": "data/interim",
            "alerts": f"{spec['output_dir']}/alerts.parquet",
            "explanations": (
                f"eval_outputs/{spec['dataset']}/explanations" if expl.is_dir() else None
            ),
            "metrics": [m for m in metrics if (REPO / m).is_file()],
        }

    if not serving:
        print("no artifacts produced — run the score pipeline first")
        return 1
    EVAL.mkdir(parents=True, exist_ok=True)
    (EVAL / "serving.json").write_text(
        json.dumps({"datasets": serving}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {EVAL / 'serving.json'} ({len(serving)} datasets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
