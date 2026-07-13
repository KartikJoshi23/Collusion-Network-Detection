"""
Finaliser node — assembles the final answer, confidence, and evidence payload
before the graph ends.

This is where graceful degradation materialises: if validation failed or was
never clean, we attach a low-confidence badge + raw evidence panel rather than
polishing a potentially-wrong synthesis.
"""

from __future__ import annotations

import logging

from app.graph.state import AgentState, CriticVerdict

logger = logging.getLogger(__name__)


def _pick_authoritative_verdict(state: AgentState) -> tuple[CriticVerdict | None, str]:
    """Pick the deepest verdict available: Arbiter > Cross-Validator > Critic."""
    if state.get("arbiter_verdict"):
        return state["arbiter_verdict"], "arbiter"
    if state.get("cross_validator_verdict"):
        return state["cross_validator_verdict"], "cross_validator"
    if state.get("critic_verdict"):
        return state["critic_verdict"], "critic"
    return None, "none"


def _build_evidence(state: AgentState) -> dict:
    sql_r = state.get("sql_result") or {}
    rag_r = state.get("rag_result") or {}
    return {
        "sql": {
            "query": sql_r.get("sql"),
            "rows_markdown": sql_r.get("rows_markdown"),
            "error": sql_r.get("error"),
        } if sql_r else None,
        "citations": rag_r.get("citations") if rag_r else None,
        "chunks_seen": rag_r.get("chunks_seen") if rag_r else None,
        "hybrid_sub_results": state.get("hybrid_sub_results"),
    }


def finalise_node(state: AgentState) -> dict:
    draft = state.get("draft_answer", "") or "I couldn't produce an answer."
    verdict, source = _pick_authoritative_verdict(state)

    confidence = float(verdict["confidence"]) if verdict else 0.5
    verdict_str = verdict["verdict"] if verdict else "uncertain"

    if verdict_str == "fail" or confidence < 0.5:
        # Graceful degradation — flag low confidence, surface raw evidence.
        low_conf_note = (
            "\n\n---\n\n"
            "**⚠️ Low confidence.** The validation layer could not confirm this answer. "
            "Raw evidence is shown below — please verify before acting on it."
        )
        final_answer = draft + low_conf_note
    elif verdict_str == "uncertain":
        final_answer = draft + (
            "\n\n*(Confidence: moderate. The answer was cross-validated but some ambiguity remains.)*"
        )
    else:
        final_answer = draft

    logger.info("Finalise -> confidence %.2f via %s (%s)", confidence, source, verdict_str)
    trace = state.get("trace", []) + [f"finalise -> {verdict_str} ({confidence:.2f}) via {source}"]

    return {
        "final_answer": final_answer,
        "final_confidence": confidence,
        "evidence": _build_evidence(state),
        "trace": trace,
    }
