"""collusiongraph CLI — {ingest,train,score,explain,eval,serve,demo}.

Config-driven commands mirror the library entry points (one YAML = one
reproducible run). Subcommands whose roadmap week has not arrived print where
their implementation is scheduled and exit non-zero so nothing silently
pretends to work.

* ``ingest --dataset X [--raw-dir D]`` — adapter → IR store (§7 steps 5–6)
* ``train -c cfg.yaml``   — dispatches on config shape: GNN training,
  baselines sweep, ensemble run, or injection-recovery (§7 steps 10–16)
* ``score -c cfg.yaml``   — alert-queue build (§7 step 13)
* ``explain -c cfg.yaml`` — explanation bundles (§7 steps 17–19)
* ``eval -c cfg.yaml``    — the §4.5 harness on precomputed scores/alerts
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

_ROADMAP = {
    "demo": "Week 8 — one-command demo (§7 step 25)",
}

_INGEST_DEFAULTS = {
    "elliptic_pp": ("data/raw/elliptic_pp", "financial", "elliptic_pp_to_ir"),
    "amlworld_hi_small": ("data/raw/amlworld_hi_small", "financial", "amlworld_to_ir"),
    "mendeley_eu": ("data/raw/mendeley_eu", "procurement", "mendeley_to_ir"),
    "garcia_rodriguez": (
        "data/raw/garcia_rodriguez/extracted",
        "procurement",
        "garcia_to_ir",
    ),
}


def select_train_runner(cfg: dict[str, Any]) -> str:
    """Dispatch a training config on its distinguishing shape (pure, testable)."""
    if "baselines" in cfg:
        return "baselines"
    if "motifs" in cfg:
        return "injection_recovery"
    if "supervised_scores_dir" in cfg and "model" not in cfg:
        return "ensemble"
    return "gnn"


def _cmd_ingest(args: argparse.Namespace) -> int:
    import importlib

    from collusiongraph.schema import GraphStore

    raw_default, module, fn_name = _INGEST_DEFAULTS[args.dataset]
    adapters = importlib.import_module(f"collusiongraph.adapters.{module}")
    stats = getattr(adapters, fn_name)(args.raw_dir or raw_default, GraphStore(args.store_root))
    print(json.dumps({k: v for k, v in stats.items() if k != "feature_names"}, indent=2))
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    from collusiongraph.eval import load_config
    from collusiongraph.training import (
        run_baselines,
        run_ensemble,
        run_injection_recovery,
        train_gnn,
    )

    runners = {
        "baselines": run_baselines,
        "injection_recovery": run_injection_recovery,
        "ensemble": run_ensemble,
        "gnn": train_gnn,
    }
    cfg = load_config(args.config)
    kind = select_train_runner(cfg)
    result = runners[kind](cfg)
    print(f"[{kind}] run complete")
    print(json.dumps(result, indent=2, default=str)[:2000])
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    from collusiongraph.training import build_alert_queue

    summary = build_alert_queue(args.config)
    print(json.dumps(summary, indent=2))
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    from collusiongraph.explain import run_explanations

    summary = run_explanations(args.config)
    print(json.dumps({k: v for k, v in summary.items() if k != "bundles"}, indent=2))
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from collusiongraph.eval import run_eval

    metrics = run_eval(args.config)
    out_dir = metrics["config"].get("output_dir", f"eval_outputs/{metrics['dataset']}")
    print(f"metrics written to {out_dir}/metrics.json")
    print(json.dumps(metrics.get("alert_level", {}).get("queue", {}), indent=2))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn
    from api.app import create_app

    uvicorn.run(create_app(args.serving), host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="collusiongraph", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="adapter → IR store")
    ingest.add_argument("--dataset", required=True, choices=sorted(_INGEST_DEFAULTS))
    ingest.add_argument("--raw-dir", default=None)
    ingest.add_argument("--store-root", default="data/interim")
    ingest.set_defaults(func=_cmd_ingest)

    for name, helptext, func in [
        ("train", "config-driven training run (GNN/baselines/ensemble/injection)", _cmd_train),
        ("score", "build an alert queue from a scores run", _cmd_score),
        ("explain", "write explanation bundles for a queue", _cmd_explain),
        ("eval", "config-driven evaluation run (§4.5 harness)", _cmd_eval),
    ]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--config", "-c", required=True, help="experiment YAML")
        p.set_defaults(func=func)

    serve = sub.add_parser("serve", help="serve precomputed artifacts (read-only API, §3.2)")
    serve.add_argument("--serving", default="eval_outputs/serving.json", help="serving index")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_cmd_serve)

    for name, scheduled in _ROADMAP.items():
        sub.add_parser(name, help=f"[not yet implemented] {scheduled}")

    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    print(
        f"'{args.command}' is not implemented yet — scheduled for {_ROADMAP[args.command]}.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
