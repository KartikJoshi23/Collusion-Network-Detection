"""collusiongraph CLI — {ingest,train,score,explain,eval,serve,demo}.

Subcommands land with their roadmap week (implementation-plan.md §7);
unimplemented ones print where their implementation is scheduled and exit
non-zero so nothing silently pretends to work.

Implemented so far:
* ``eval`` (Week 3, §7 step 9) — config-driven evaluation run: one YAML in,
  ``metrics.json`` out (the §4.5 harness is the only source of paper numbers).
"""

from __future__ import annotations

import argparse
import json
import sys

_ROADMAP = {
    "ingest": "Week 2 — adapters → CollusionGraph IR (§7 steps 4–7)",
    "train": "Week 4 — supervised GNN core (§7 steps 11–13)",
    "score": "Week 5 — ensemble + alert queue (§7 steps 14–16)",
    "explain": "Week 6 — explanation bundles (§7 steps 17–19)",
    "serve": "Week 7 — FastAPI artifact serving (§7 step 22)",
    "demo": "Week 8 — one-command demo (§7 step 25)",
}


def _cmd_eval(args: argparse.Namespace) -> int:
    from collusiongraph.eval import run_eval

    metrics = run_eval(args.config)
    out_dir = metrics["config"].get("output_dir", f"eval_outputs/{metrics['dataset']}")
    print(f"metrics written to {out_dir}/metrics.json")
    print(json.dumps(metrics["alert_level"]["queue"], indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="collusiongraph", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    eval_parser = sub.add_parser("eval", help="config-driven evaluation run (§4.5 harness)")
    eval_parser.add_argument("--config", "-c", required=True, help="experiment YAML")
    eval_parser.set_defaults(func=_cmd_eval)

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
