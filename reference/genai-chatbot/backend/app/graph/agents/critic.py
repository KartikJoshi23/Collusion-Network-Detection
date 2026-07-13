"""Critic — validates the draft answer against the user's question + evidence.

Flow:
  1. Deterministic gates run first (fast, no LLM):
       - grounding gate: if question contains policy/fuzzy terms, the answer
         MUST cite at least one PDF chunk. Ungrounded policy claims are the
         biggest source of silent-wrong answers in hybrid systems.
       - numeric sanity gate: if the answer claims specific numbers and an SQL
         result exists, at least one of those numbers must appear in the SQL
         rows_markdown. Catches LLMs inventing numbers.
  2. If both gates pass, the LLM does its full plausibility/logic check.
  3. If a gate fails, we short-circuit with verdict=retry and a clear reason
     — the Cross-Validator will pick up the retry and re-derive with the
     missing evidence.
"""

from __future__ import annotations

import json
import logging
import re

from app.graph.agents._utils import parse_json_response
from app.graph.prompts import CRITIC_SYSTEM
from app.graph.state import AgentState, CriticVerdict
from app.llm import get_model_name, get_openai_client

logger = logging.getLogger(__name__)

_VALID_VERDICTS = {"pass", "retry", "uncertain", "fail"}

# Policy / fuzzy terms that require PDF grounding. Any of these appearing in a
# user question means the answer should cite at least one policy/governance PDF.
# Curated by category so it's easy to extend without duplication.
POLICY_LEXICON: set[str] = {
    # Compliance, risk, governance
    "flagged", "overdue", "behind", "critical", "risky", "at risk", "at-risk",
    "vested", "certified", "compliant", "non-compliant",
    "mandatory", "passed", "conditional", "suspended", "approved",
    "exposed", "eligible", "governance", "sla breach",
    # Compensation / HR policy
    "retention bonus", "counter-offer", "esop", "esops", "vesting",
    "ipo", "drhp", "certification", "certifications",
    # Geography / data sovereignty
    "localisation", "localization", "data sovereignty", "data residency",
    "dpdp", "regulated",
    # Finance / budget / reconciliation
    "over budget", "budget", "utilised", "utilized", "utilisation", "utilization",
    "reconciliation", "reconcile", "procurement", "gap",
    "actual", "reported", "allocation",
    "cost centre", "cost center", "capex", "opex",
    # Tiers / segmentation (policy-defined)
    "tier 1", "tier-1", "tier1", "high-value",
}

_PDF_CITATION_RE = re.compile(r"\.pdf(?:::sec\d+)?", re.IGNORECASE)
_NUMBER_RE = re.compile(r"(?<![\w.])\d{2,}(?:,\d{3})*(?:\.\d+)?(?![\w.])")

# Numeric value with at most one decimal comma or period separator, for
# arithmetic-consistency checks (only crude cases are worth verifying).
_MONEY_RE = re.compile(r"₹\s*([\d,]+(?:\.\d+)?)\s*(?:L|lakh|lakhs|Cr|crore|crores)?", re.IGNORECASE)


def _detect_policy_terms(question: str) -> list[str]:
    q = question.lower()
    return sorted({term for term in POLICY_LEXICON if term in q})


def _grounding_gate(state: AgentState, draft: str) -> tuple[bool, str]:
    """Returns (passed, reason)."""
    question = state.get("user_query", "")
    terms = _detect_policy_terms(question)
    if not terms:
        return True, ""
    if _PDF_CITATION_RE.search(draft):
        return True, ""
    return False, (
        f"Question uses policy/fuzzy terms {terms} but the answer cites no PDF. "
        "Fetch the relevant policy clauses (via hybrid_search) and cite them."
    )


def _numeric_sanity_gate(state: AgentState, draft: str) -> tuple[bool, str]:
    """If the answer mentions specific numbers, at least one should appear in the SQL result."""
    sql_result = state.get("sql_result") or {}
    rows_md = sql_result.get("rows_markdown") or ""

    # Also fall back to hybrid sub-results
    if not rows_md:
        for sub in state.get("hybrid_sub_results") or []:
            sr = (sub or {}).get("sql_result") or {}
            if sr.get("rows_markdown"):
                rows_md += "\n" + sr["rows_markdown"]

    if not rows_md:
        return True, ""

    answer_nums = set(_NUMBER_RE.findall(draft))
    if not answer_nums:
        return True, ""
    rows_nums = set(_NUMBER_RE.findall(rows_md))
    if answer_nums & rows_nums:
        return True, ""
    return False, (
        f"Answer mentions numbers {sorted(answer_nums)[:5]} but NONE of those "
        f"appear in the SQL result. Numbers must be grounded in retrieved rows."
    )


def _evidence_block(state: AgentState) -> str:
    parts: list[str] = []
    sql_result = state.get("sql_result")
    if sql_result:
        parts.append(
            "SQL executed:\n```sql\n" + (sql_result.get("sql") or "(none)") + "\n```\n"
            "SQL result (truncated):\n" + (sql_result.get("rows_markdown") or "(empty)")
        )
    rag_result = state.get("rag_result")
    if rag_result:
        cits = rag_result.get("citations") or []
        # Hydrate citations with actual chunk text so the Critic can verify the
        # answer against source content — not just the fact that a chunk_id was
        # cited. Without this the Critic can only check syntactic citation, not
        # factual grounding.
        chunk_texts: list[str] = []
        try:
            from app.retrieval.hybrid import get_retriever

            retriever = get_retriever()
            retriever._ensure_loaded()
            payload_by_id = {p["chunk_id"]: p for p in retriever._corpus_payloads}
            for c in cits:
                cid = c.get("chunk_id")
                payload = payload_by_id.get(cid) if cid else None
                if payload:
                    chunk_texts.append(
                        f"### [{cid}] — {payload['doc_name']} §{payload['section_num']} {payload['section_title']}\n\n{payload['raw_text']}"
                    )
        except Exception as e:  # noqa: BLE001
            chunk_texts.append(f"(could not hydrate chunk bodies: {e})")
        if chunk_texts:
            parts.append("Retrieved chunks (full text):\n\n" + "\n\n---\n\n".join(chunk_texts))
        else:
            parts.append(
                "Retrieved chunks (no bodies available, IDs only):\n"
                + "\n".join(f"- [{c.get('chunk_id')}]" for c in cits)
            )

    # Hybrid path: the SQL/RAG results live in hybrid_sub_results, not the
    # top-level sql_result / rag_result slots. Surface each sub-answer with
    # its SQL and/or citations so the Critic can verify.
    hybrid = state.get("hybrid_sub_results") or []
    for i, sub in enumerate(hybrid, 1):
        lines = [f"### Hybrid sub-answer {i} ({sub.get('type', '?')})", f"Q: {sub.get('question', '')}"]
        lines.append(f"A: {sub.get('answer', '')}")
        sqlr = sub.get("sql_result") or {}
        if sqlr.get("sql"):
            lines.append("SQL executed:\n```sql\n" + sqlr["sql"] + "\n```")
        if sqlr.get("rows_markdown"):
            lines.append("Rows:\n" + sqlr["rows_markdown"])
        ragr = sub.get("rag_result") or {}
        if ragr.get("citations"):
            lines.append(
                "Citations: " + ", ".join(f"[{c.get('chunk_id')}]" for c in ragr["citations"])
            )
        parts.append("\n\n".join(lines))

    if not parts:
        return "(no evidence)"
    return "\n\n".join(parts)


def critic_node(state: AgentState) -> dict:
    draft = state.get("draft_answer") or ""

    # ---- Deterministic gates (fast, no LLM) ----
    gate_failures: list[str] = []
    for gate_name, gate_fn in (("grounding", _grounding_gate), ("numeric_sanity", _numeric_sanity_gate)):
        ok, reason = gate_fn(state, draft)
        if not ok:
            gate_failures.append(f"{gate_name}: {reason}")

    if gate_failures:
        logger.info("Critic deterministic gate FAILED: %s", gate_failures)
        verdict: CriticVerdict = {
            "confidence": 0.3,
            "reasons": gate_failures,
            "issues": gate_failures,
            "verdict": "retry",  # type: ignore[typeddict-item]
        }
        trace = state.get("trace", []) + [f"critic -> retry (gate: {gate_failures[0][:50]}...)"]
        return {"critic_verdict": verdict, "trace": trace}

    # ---- LLM plausibility / logic check (runs only when gates pass) ----
    client = get_openai_client()
    model = get_model_name()

    user_block = (
        f"User question: {state['user_query']}\n\n"
        f"Resolved intent:\n```json\n{json.dumps(state.get('intent') or {}, indent=2)}\n```\n\n"
        f"Draft answer:\n{draft or '(empty)'}\n\n"
        f"Evidence:\n{_evidence_block(state)}"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CRITIC_SYSTEM},
            {"role": "user", "content": user_block},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    payload = parse_json_response(resp.choices[0].message.content or "", context="critic")

    verdict_str = str(payload.get("verdict", "")).lower()
    if verdict_str not in _VALID_VERDICTS:
        verdict_str = "uncertain"

    verdict: CriticVerdict = {
        "confidence": float(payload.get("confidence", 0.5)),
        "reasons": payload.get("reasons", []) or [],
        "issues": payload.get("issues", []) or [],
        "verdict": verdict_str,  # type: ignore[typeddict-item]
    }

    logger.info("Critic -> %s (conf %.2f)", verdict["verdict"], verdict["confidence"])
    trace = state.get("trace", []) + [f"critic -> {verdict['verdict']} ({verdict['confidence']:.2f})"]
    return {"critic_verdict": verdict, "trace": trace}
