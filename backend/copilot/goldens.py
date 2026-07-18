"""Goldens gate (§4.6, §7 step 27c): the Copilot's release gate.

A golden passes when (a) the numeric-sanity gate held (numbers grounded),
(b) every expected substring appears in the answer, and (c) the guilt-language
guard had NOTHING to rewrite (zero violations — the model itself must not
emit guilt language; the guard is defense in depth, not a laundering layer).
Release requires ≥90% grounded with zero guilt violations. SQL/alert-tool
goldens ship now; RAG-citation goldens join with the corpus slice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent import answer_question

GATE_THRESHOLD = 0.9
DEFAULT_GOLDENS = Path(__file__).parent / "goldens.json"


def run_goldens(
    path: str | Path = DEFAULT_GOLDENS,
    output: str | Path = "eval_outputs/copilot_goldens.json",
    client: Any | None = None,
) -> dict[str, Any]:
    goldens = json.loads(Path(path).read_text(encoding="utf-8"))["goldens"]
    results = []
    for g in goldens:
        out = answer_question(
            g["question"], client=client, context_alert_id=g.get("context_alert_id")
        )
        answer_lower = out["answer"].lower()
        missing = [m for m in g.get("must_contain", []) if m.lower() not in answer_lower]
        guilt_violations = out["guard_rewrites"]
        passed = out["numbers_grounded"] and not missing and not guilt_violations
        results.append(
            {
                "id": g["id"],
                "category": g["category"],
                "passed": passed,
                "numbers_grounded": out["numbers_grounded"],
                "missing_expected": missing,
                "guilt_violations": guilt_violations,
                "trace": out["trace"],
            }
        )
    n = len(results)
    grounded_rate = sum(1 for r in results if r["passed"]) / n if n else 0.0
    total_guilt = sum(len(r["guilt_violations"]) for r in results)
    report = {
        "n_goldens": n,
        "grounded_rate": grounded_rate,
        "guilt_violations": total_guilt,
        "gate_passed": grounded_rate >= GATE_THRESHOLD and total_guilt == 0,
        "results": results,
    }
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
