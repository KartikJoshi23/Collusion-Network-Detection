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

import yaml
from collusiongraph.training import build_alert_queue

REPO = Path(__file__).resolve().parents[1]
EVAL = REPO / "eval_outputs"

# Each served queue is built from its COMMITTED experiment config, so the demo
# serves exactly the queue the paper reports. (Until 2026-11 this file carried
# its own copies of the queue settings. They had drifted to other models,
# gatv2_multi_s0 and sage_struct_s0, and overwrote the published queue
# folders; see revision-plan.md, Section 0.2.) "metrics" lists the run
# metrics the dashboard shows beside each queue.
DEMOS = [
    {
        "config": "configs/experiment/alert_queue_elliptic_pp_ensemble.yaml",
        "metrics": ["eval_outputs/elliptic_pp/ensemble/ensemble_calibrated/metrics.json"],
    },
    {
        "config": "configs/experiment/alert_queue_mendeley_eu.yaml",
        "metrics": [
            "eval_outputs/mendeley_eu/gnn_rgcn_focal_multiseed/seed_0/metrics.json",
            "eval_outputs/mendeley_eu/transfer_loco_country_5/metrics.json",
        ],
    },
    # actor-level queue (§7 step 26c): §4.5 reports BOTH queue granularities —
    # the wallet head out-precises the tx head at tight budgets
    {
        "config": "configs/experiment/alert_queue_elliptic_actor.yaml",
        "metrics": ["eval_outputs/elliptic_pp_actor/gnn_rgcn_focal/metrics.json"],
    },
    # procurement second dataset: García, queued on its strongest LOMO fold
    # (Italy) — entity-disjoint market subgraph, precalibrated fold scores
    {
        "config": "configs/experiment/alert_queue_garcia_italy.yaml",
        "metrics": ["eval_outputs/garcia_rodriguez/transfer_lomo_matrix/fold_Italy_s0/run.json"],
    },
]


def load_demo_config(spec: dict) -> dict:
    """The committed queue config for one demo entry."""
    return yaml.safe_load((REPO / spec["config"]).read_text(encoding="utf-8"))


# Phase-2 rigor artifacts (§7 steps 28–29, 32) per dataset: name → path.
# Exists-checked at build time — a machine that has not produced an artifact
# simply serves without it. García's LOMO matrix rides with the procurement
# dataset (García itself has no served queue); the label-efficiency curves
# attach to their TARGET dataset.
RIGOR = {
    "elliptic_pp": {
        "multiseed_gatv2": "eval_outputs/elliptic_pp/gnn_gatv2_focal_multiseed/multiseed.json",
        "multiseed_ensemble": "eval_outputs/elliptic_pp/ensemble_multiseed/ensemble_multiseed.json",
        "sensitivity": "eval_outputs/elliptic_pp/sensitivity/sensitivity.json",
        "label_noise": "eval_outputs/elliptic_pp/label_noise_curve/noise_curve.json",
        "significance": "eval_outputs/elliptic_pp/significance/significance.json",
        "label_efficiency": (
            "eval_outputs/cross_domain/label_efficiency_proc2fin/label_efficiency.json"
        ),
    },
    "mendeley_eu": {
        "multiseed_rgcn": "eval_outputs/mendeley_eu/gnn_rgcn_focal_multiseed/multiseed.json",
        "loco_matrix": "eval_outputs/mendeley_eu/transfer_loco_matrix/matrix.json",
        "sensitivity": "eval_outputs/mendeley_eu/sensitivity/sensitivity.json",
        "label_efficiency": (
            "eval_outputs/cross_domain/label_efficiency_fin2proc/label_efficiency.json"
        ),
    },
    "garcia_rodriguez": {
        "lomo_matrix_garcia": "eval_outputs/garcia_rodriguez/transfer_lomo_matrix/matrix.json",
        "label_efficiency": (
            "eval_outputs/cross_domain/label_efficiency_fin2proc/label_efficiency.json"
        ),
    },
}


def main() -> int:
    serving: dict[str, dict] = {}
    for spec in DEMOS:
        cfg = load_demo_config(spec)
        dataset, out = cfg["dataset"], cfg["output_dir"]
        scores = REPO / cfg["scores_dir"]
        # honour the config's own scores_file (e.g. the calibrated-ensemble parquet)
        if not (scores / cfg.get("scores_file", "scores_test.parquet")).is_file():
            print(f"skip {dataset}: no score run at {cfg['scores_dir']}")
            continue
        summary = build_alert_queue(cfg)
        print(f"{dataset}: {summary['n_alerts']} alerts (config {spec['config']})")

        expl = REPO / "eval_outputs" / dataset / "explanations"
        # the queue's own metrics ride along: the alert-level precision@budget
        # block feeds the dashboard's measured precision readout (§5.3 view 2)
        metrics = [*spec["metrics"], f"{out}/metrics.json"]
        rigor = {
            name: path for name, path in RIGOR.get(dataset, {}).items() if (REPO / path).is_file()
        }
        serving[dataset] = {
            "domain": cfg["domain"],
            "store_root": cfg.get("store_root", "data/interim"),
            "alerts": f"{out}/alerts.parquet",
            "explanations": (f"eval_outputs/{dataset}/explanations" if expl.is_dir() else None),
            "metrics": [m for m in metrics if (REPO / m).is_file()],
            "rigor": rigor,
        }

    if not serving:
        print("no artifacts produced — run the score pipeline first")
        return 1

    # Stress-test section (§7 step 30, §5.3): the OCDS injection study — fake
    # cartels planted into the real unlabeled network. Multi-seed preferred
    # (matches the report's mean±std); single-seed report as fallback; omitted
    # if neither has been run on this machine.
    index: dict[str, dict] = {"datasets": serving}
    ms = "eval_outputs/ocds_georgia/injection_recovery_multiseed/injection_multiseed.json"
    s0 = "eval_outputs/ocds_georgia/injection_recovery/injection_recovery_report.json"
    recovery = ms if (REPO / ms).is_file() else (s0 if (REPO / s0).is_file() else None)
    if recovery is not None:
        index["stress_test"] = {
            "ocds_georgia": {
                "title": "Georgia public contracts — 163,327 firms, no answer key",
                "recovery": recovery,
                "reproduce": (
                    "uv run collusiongraph train -c "
                    "configs/experiment/injection_recovery_ocds_georgia_multiseed.yaml"
                ),
                "note": (
                    "Real government contract network with no labels. We plant fake "
                    "cartels of known shapes and measure how many the detector claws "
                    "back — the only honest way to evaluate where there is no answer key."
                ),
            }
        }

    EVAL.mkdir(parents=True, exist_ok=True)
    (EVAL / "serving.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    extra = " + stress-test study" if "stress_test" in index else ""
    print(f"wrote {EVAL / 'serving.json'} ({len(serving)} datasets{extra})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
