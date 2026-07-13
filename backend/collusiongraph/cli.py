"""collusiongraph CLI — {ingest,train,score,explain,eval,serve,demo}.

Week-1 scaffold: subcommands are registered but land with their roadmap
week (implementation-plan.md §7). Each prints where its implementation
is scheduled and exits non-zero so nothing silently pretends to work.
"""

from __future__ import annotations

import argparse
import sys

_ROADMAP = {
    "ingest": "Week 2 — adapters → CollusionGraph IR (§7 steps 4–7)",
    "train": "Week 4 — supervised GNN core (§7 steps 11–13)",
    "score": "Week 5 — ensemble + alert queue (§7 steps 14–16)",
    "explain": "Week 6 — explanation bundles (§7 steps 17–19)",
    "eval": "Week 3 — evaluation harness (§7 step 9)",
    "serve": "Week 7 — FastAPI artifact serving (§7 step 22)",
    "demo": "Week 8 — one-command demo (§7 step 25)",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="collusiongraph",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, scheduled in _ROADMAP.items():
        sub.add_parser(name, help=f"[not yet implemented] {scheduled}")

    args = parser.parse_args(argv)
    print(
        f"'{args.command}' is not implemented yet — scheduled for " f"{_ROADMAP[args.command]}.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
