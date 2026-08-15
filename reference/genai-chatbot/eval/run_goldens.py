"""
Golden-set evaluation harness.

Runs every golden + paraphrase through the full LangGraph pipeline (in-process —
no HTTP round-trip) and scores the result.

Pass criterion per golden:
  - For `ambiguous` category: the pipeline MUST trigger a clarification interrupt
    before any final answer. If it produces a final answer directly, that's a fail.
  - For sql categories: expected table names must appear in the executed SQL,
    and any `expected_key_values.answer_contains` substrings must appear
    in the final answer.
  - For rag categories: expected source files must be cited, and any
    `expected_key_values.answer_contains` substrings must appear.
  - For hybrid: both of the above.

Run with:   make eval        (inside backend container)
Or locally: pytest eval/run_goldens.py -v

The report card is written to `eval/last_report.json` for programmatic inspection
and printed to stdout.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

GOLDENS_PATH = Path(__file__).parent / "goldens.json"
REPORT_PATH = Path(__file__).parent / "last_report.json"

logger = logging.getLogger(__name__)


def _load_goldens() -> list[dict]:
    with open(GOLDENS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_query(question: str) -> dict[str, Any]:
    """Invoke the graph once and return {interrupted, state} for scoring."""
    from app.graph.orchestrator import get_graph
    from app.graph.state import make_initial_state

    graph = get_graph()
    thread_id = f"eval-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    initial = make_initial_state(thread_id, question)

    t0 = time.monotonic()
    final_state = graph.invoke(initial, config=config)
    elapsed = time.monotonic() - t0

    snap = graph.get_state(config)
    interrupted = bool(snap.tasks and any(getattr(t, "interrupts", None) for t in snap.tasks))
    interrupt_value = None
    if interrupted:
        for task in snap.tasks:
            for iv in getattr(task, "interrupts", []) or []:
                interrupt_value = getattr(iv, "value", None)
                break
            if interrupt_value is not None:
                break

    return {
        "interrupted": interrupted,
        "interrupt_value": interrupt_value,
        "state": final_state,
        "elapsed_s": elapsed,
    }


def _score(golden: dict, result: dict[str, Any]) -> tuple[bool, str]:
    category = golden.get("category", "")
    interrupted = result["interrupted"]
    state = result["state"] or {}
    final = str(state.get("final_answer", "")).lower()
    evidence = state.get("evidence") or {}

    if category == "ambiguous":
        if interrupted:
            return True, "clarification triggered as expected"
        return False, "expected clarification; got final answer"

    if interrupted:
        return False, "unexpected clarification trigger"

    # Substring checks in the answer
    kv = golden.get("expected_key_values") or {}
    ac = kv.get("answer_contains")
    if ac:
        needles = ac if isinstance(ac, list) else [ac]
        for n in needles:
            if str(n).lower() not in final:
                return False, f"answer missing expected substring {n!r}"

    # Source checks
    expected_sources = golden.get("expected_sources") or []
    sql_info = (evidence.get("sql") or {}) if isinstance(evidence.get("sql"), dict) else {}
    sql_query = str(sql_info.get("query") or "").lower()

    citations = evidence.get("citations") or []
    cited_docs: set[str] = set()
    for c in citations:
        cid = c.get("chunk_id") if isinstance(c, dict) else None
        if cid:
            cited_docs.add(cid.split("::")[0])

    for src in expected_sources:
        if src.lower().endswith(".pdf"):
            if src not in cited_docs:
                return False, f"expected citation to {src}; cited: {sorted(cited_docs) or 'none'}"
        else:
            if src not in sql_query:
                return False, f"expected table {src} in SQL; got: {sql_query[:120]}"

    # Simple row_count sanity (when it's positive)
    if golden.get("expected_row_count") and golden["expected_row_count"] > 0:
        # rows_markdown lines starting with '|' roughly = row_count + header + separator
        rows_md = str(sql_info.get("rows_markdown") or "")
        row_lines = [ln for ln in rows_md.splitlines() if ln.startswith("|")]
        approx = max(0, len(row_lines) - 2)  # subtract header + separator
        if approx < golden["expected_row_count"]:
            # Don't fail hard — could be legitimately fewer rows — just note it.
            return True, f"ok (rows: ~{approx} vs expected {golden['expected_row_count']})"

    return True, "ok"


@pytest.fixture(scope="session")
def goldens() -> list[dict]:
    return _load_goldens()


@pytest.mark.parametrize("golden", _load_goldens(), ids=lambda g: g["id"])
def test_golden(golden: dict) -> None:
    result = _run_query(golden["question"])
    ok, reason = _score(golden, result)
    _append_report(
        {
            "id": golden["id"],
            "category": golden["category"],
            "question": golden["question"],
            "ok": ok,
            "reason": reason,
            "elapsed_s": round(result["elapsed_s"], 2),
        }
    )
    assert ok, reason


def _append_report(row: dict[str, Any]) -> None:
    try:
        existing: list[dict] = []
        if REPORT_PATH.exists():
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(row)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not append to report: %s", e)


def print_summary() -> None:
    if not REPORT_PATH.exists():
        print("No report yet.")
        return
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        rows = json.load(f)
    total = len(rows)
    passed = sum(1 for r in rows if r["ok"])
    cats: Counter = Counter()
    cat_pass: Counter = Counter()
    for r in rows:
        cats[r["category"]] += 1
        if r["ok"]:
            cat_pass[r["category"]] += 1
    print(f"\nGolden eval: {passed}/{total} passed ({100.0*passed/total:.1f}%)")
    for cat in sorted(cats.keys()):
        print(f"  {cat:<22} {cat_pass[cat]}/{cats[cat]}")


if __name__ == "__main__":
    # Allow "python -m eval.run_goldens" for ad-hoc runs outside pytest.
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()
    rc = pytest.main([__file__, "-v"])
    print_summary()
    sys.exit(rc)
