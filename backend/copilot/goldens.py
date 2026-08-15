"""Goldens gate (§4.6, §7 step 27c): the Copilot's release gate.

A golden passes when (a) the numeric + corpus grounding gates held,
(b) every expected substring appears in the answer, and (c) the RELEASED
answer contains zero guilt language — §4.6's zero-tolerance bar applies to
what ships, which the deterministic guard enforces by construction. Model
DRAFT rewrites are additionally tracked as a drift signal with a hard
ceiling (DRAFT_REWRITE_CEILING): hosted-MoE sampling is not exactly
reproducible even at temperature 0 (measured 0–1 rewrites per 18 across
runs, 2026-07-19), so zero-tolerance on drafts would make the gate
permanently flaky while telling us nothing new — the ceiling fails the gate
if prompt drift ever makes rewrites systematic."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .agent import answer_question
from .guard import _GUILT_REWRITES

GATE_THRESHOLD = 0.9
DRAFT_REWRITE_CEILING = 0.10  # ≤10% of goldens may need a draft rewrite
DEFAULT_GOLDENS = Path(__file__).parent / "goldens.json"


def run_goldens(
    path: str | Path = DEFAULT_GOLDENS,
    output: str | Path = "eval_outputs/copilot_goldens.json",
    client: Any | None = None,
) -> dict[str, Any]:
    goldens = json.loads(Path(path).read_text(encoding="utf-8"))["goldens"]
    results = []
    for g in goldens:
        # hosted-model nondeterminism (even at temperature 0) makes single
        # shots flaky; one recorded retry separates transient variance from
        # systematic failure. Guilt violations get NO retry — one strike.
        attempts = 0
        for _ in (1, 2):
            attempts += 1
            try:
                out = answer_question(
                    g["question"], client=client, context_alert_id=g.get("context_alert_id")
                )
            except Exception as e:  # NIM free tier: 40 RPM — back off once on 429
                if type(e).__name__ != "RateLimitError":
                    raise
                time.sleep(65)
                out = answer_question(
                    g["question"], client=client, context_alert_id=g.get("context_alert_id")
                )
            answer_lower = out["answer"].lower()
            missing = [m for m in g.get("must_contain", []) if m.lower() not in answer_lower]
            # §4.6's zero-tolerance bar applies to RELEASED output — which the
            # deterministic guard already rewrote. Draft rewrites are tracked
            # as a drift signal with a ceiling (hosted-MoE sampling is not
            # exactly reproducible even at temperature 0, measured 2026-07-19).
            draft_rewrites = out["guard_rewrites"]
            released_violations = [
                pattern.pattern for pattern, _ in _GUILT_REWRITES if pattern.search(out["answer"])
            ]
            passed = (
                out["numbers_grounded"]
                and out.get("corpus_grounded", True)
                and not missing
                and not released_violations
            )
            if passed or released_violations:
                break
        results.append(
            {
                "id": g["id"],
                "category": g["category"],
                "passed": passed and not released_violations,
                "attempts": attempts,
                "numbers_grounded": out["numbers_grounded"],
                "corpus_grounded": out.get("corpus_grounded", True),
                "missing_expected": missing,
                "released_guilt_violations": released_violations,
                "draft_rewrites": draft_rewrites,
                "trace": out["trace"],
            }
        )
    n = len(results)
    grounded_rate = sum(1 for r in results if r["passed"]) / n if n else 0.0
    released_guilt = sum(len(r["released_guilt_violations"]) for r in results)
    draft_rewrite_rate = sum(1 for r in results if r["draft_rewrites"]) / n if n else 0.0
    report = {
        "n_goldens": n,
        "grounded_rate": grounded_rate,
        "released_guilt_violations": released_guilt,
        "draft_rewrite_rate": draft_rewrite_rate,
        "gate_passed": (
            grounded_rate >= GATE_THRESHOLD
            and released_guilt == 0
            and draft_rewrite_rate <= DRAFT_REWRITE_CEILING
        ),
        "results": results,
    }
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    report = run_goldens()
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    raise SystemExit(0 if report["gate_passed"] else 1)
