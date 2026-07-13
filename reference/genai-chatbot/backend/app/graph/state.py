"""
The single state object flowing through every LangGraph node.

Every node reads what it needs and writes only the fields it produces. LangGraph
merges partial updates via the `operator.or_` semantics (for dicts) or replacement
(for scalars). We use TypedDict (not Pydantic BaseModel) for LangGraph
compatibility — pydantic validators conflict with partial updates.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

Route = Literal["sql", "rag", "hybrid", "clarify"]


class Ambiguity(TypedDict, total=False):
    field: str  # "metric" | "timeframe" | "entity_scope" | "filter"
    issue: str
    severity: float  # 0.0 - 1.0


class Intent(TypedDict, total=False):
    entities: list[str]
    ops: list[str]
    ambiguities: list[Ambiguity]
    clarity_score: float  # 0.0 - 1.0


class ClarificationTurn(TypedDict):
    question: str
    user_answer: str | None


class SubQuestion(TypedDict, total=False):
    question: str
    type: Literal["sql", "rag"]


class SqlResult(TypedDict, total=False):
    sql: str
    rows_markdown: str
    row_count: int
    error: str | None
    iterations: int  # how many retries the SQL agent used


class RagChunkRef(TypedDict, total=False):
    chunk_id: str
    doc_name: str
    section_num: int
    section_title: str
    score: float


class RagResult(TypedDict, total=False):
    answer: str
    citations: list[RagChunkRef]
    chunks_seen: list[RagChunkRef]


class CriticVerdict(TypedDict, total=False):
    confidence: float
    reasons: list[str]
    issues: list[str]
    verdict: Literal["pass", "retry", "uncertain", "fail"]


class AgentState(TypedDict, total=False):
    # --- Inputs ---
    session_id: str
    user_query: str
    conversation_history: list[dict[str, str]]  # [{role, content}]

    # --- Router ---
    route: Route | None

    # --- Intent classifier ---
    intent: Intent | None

    # --- Clarification loop ---
    clarification_rounds: int
    clarification_turns: list[ClarificationTurn]
    pending_clarification: str | None  # question awaiting user answer
    enriched_query: str  # original + clarifications folded in

    # --- Planner (hybrid only) ---
    sub_questions: list[SubQuestion] | None

    # --- Execution results ---
    sql_result: SqlResult | None
    rag_result: RagResult | None
    hybrid_sub_results: list[dict[str, Any]] | None

    # --- Read-back ---
    readback_text: str | None
    readback_approved: bool | None

    # --- Synthesis / final draft ---
    draft_answer: str

    # --- Validation stack ---
    critic_verdict: CriticVerdict | None
    cross_validator_verdict: CriticVerdict | None
    arbiter_verdict: CriticVerdict | None

    # --- Completeness check (post-validation recall gate) ---
    completeness_verdict: dict[str, Any] | None
    completeness_retry_used: int

    # --- Final output ---
    final_answer: str
    final_confidence: float
    evidence: dict[str, Any]  # {sql: ..., chunks: [...]}
    trace: list[str]  # human-readable log of which agents fired


def make_initial_state(session_id: str, user_query: str, history: list[dict[str, str]] | None = None) -> AgentState:
    return AgentState(
        session_id=session_id,
        user_query=user_query,
        conversation_history=history or [],
        route=None,
        intent=None,
        clarification_rounds=0,
        clarification_turns=[],
        pending_clarification=None,
        enriched_query=user_query,
        sub_questions=None,
        sql_result=None,
        rag_result=None,
        hybrid_sub_results=None,
        readback_text=None,
        readback_approved=None,
        draft_answer="",
        critic_verdict=None,
        cross_validator_verdict=None,
        arbiter_verdict=None,
        completeness_verdict=None,
        completeness_retry_used=0,
        final_answer="",
        final_confidence=0.0,
        evidence={},
        trace=[],
    )
