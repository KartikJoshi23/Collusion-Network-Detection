"""
LangGraph orchestrator — the state machine that wires all 10 agents together.

Graph shape:

    START
      │
      ▼
    router
      │
      ▼
    intent_classifier
      │
      ▼
   [clarify?] ──yes──▶ clarification ──▶ intent_classifier (re-enter)
      │no
      ▼
   [route]
   /  |  \\
  sql rag hybrid
   |  |   │
   |  |   planner ──▶ hybrid_executor ──▶ synthesiser
   |  |                                      │
   sql_agent   rag_agent                     │
       \\          |                          │
        \\─────────┴──────────────┬───────────┘
                                 ▼
                          [complex?] ──yes──▶ readback
                                 │no           │approved
                                 │◀────────────┘
                                 ▼
                              critic
                                 │
                           [borderline?] ──yes──▶ cross_validator
                                 │no                     │
                                 │            [disagree?]──yes──▶ arbiter
                                 │                     │no         │
                                 └─────────────────────┴───────────┘
                                                       ▼
                                                  finalise ──▶ END
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.agents.arbiter import arbiter_node, should_arbitrate
from app.graph.agents.clarification import clarification_node, needs_clarification
from app.graph.agents.completeness_checker import (
    completeness_node,
    completeness_reground_node,
    should_check_completeness,
)
from app.graph.agents.critic import critic_node
from app.graph.agents.cross_validator import cross_validator_node, should_cross_validate
from app.graph.agents.finaliser import finalise_node
from app.graph.agents.hybrid_executor import hybrid_execute_node
from app.graph.agents.intent_classifier import intent_classifier_node
from app.graph.agents.planner import planner_node
from app.graph.agents.rag_agent import rag_agent_node
from app.graph.agents.readback import is_complex_query, readback_node
from app.graph.agents.router import router_node
from app.graph.agents.sql_agent import sql_agent_node
from app.graph.agents.synthesiser import synthesiser_node
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


# ---- Conditional edge functions ----------------------------------------------

def _after_intent(state: AgentState) -> str:
    if needs_clarification(state):
        return "clarification"
    return "readback_gate"


def _after_clarification(state: AgentState) -> str:
    # Loop back through intent classifier so the enriched query gets re-scored.
    return "intent_classifier"


def _after_readback_gate(state: AgentState) -> str:
    route = state.get("route") or "sql"
    if is_complex_query(state):
        return "readback"
    if route == "hybrid":
        return "planner"
    if route == "rag":
        return "rag_agent"
    return "sql_agent"


def _after_readback(state: AgentState) -> str:
    if not state.get("readback_approved", True):
        # User adjusted — re-enter intent classifier with enriched query.
        return "intent_classifier"
    route = state.get("route") or "sql"
    if route == "hybrid":
        return "planner"
    if route == "rag":
        return "rag_agent"
    return "sql_agent"


def _after_critic(state: AgentState) -> str:
    if should_cross_validate(state):
        return "cross_validator"
    return "completeness_gate"


def _after_cross_validator(state: AgentState) -> str:
    if should_arbitrate(state):
        return "arbiter"
    return "completeness_gate"


def _after_arbiter(state: AgentState) -> str:
    return "completeness_gate"


def _completeness_gate_node(state: AgentState) -> dict:
    """No-op decision node — used as the edge hub for post-validation routing."""
    return {}


def _after_completeness_gate(state: AgentState) -> str:
    if should_check_completeness(state):
        return "completeness_checker"
    return "finaliser"


def _after_completeness(state: AgentState) -> str:
    v = state.get("completeness_verdict") or {}
    if v.get("verdict") == "retry" and state.get("completeness_retry_used", 0) < 1:
        return "completeness_reground"
    return "finaliser"


# The readback_gate is a trivial pass-through used as a decision point; we
# model it as a no-op node so LangGraph has something to hang conditional
# edges off of.
def _readback_gate_node(state: AgentState) -> dict:
    return {}


# ---- Graph builder -----------------------------------------------------------

def _build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("intent_classifier", intent_classifier_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("readback_gate", _readback_gate_node)
    graph.add_node("readback", readback_node)
    graph.add_node("planner", planner_node)
    graph.add_node("sql_agent", sql_agent_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("hybrid_executor", hybrid_execute_node)
    graph.add_node("synthesiser", synthesiser_node)
    graph.add_node("critic", critic_node)
    graph.add_node("cross_validator", cross_validator_node)
    graph.add_node("arbiter", arbiter_node)
    graph.add_node("completeness_gate", _completeness_gate_node)
    graph.add_node("completeness_checker", completeness_node)
    graph.add_node("completeness_reground", completeness_reground_node)
    graph.add_node("finaliser", finalise_node)

    graph.add_edge(START, "router")
    graph.add_edge("router", "intent_classifier")

    graph.add_conditional_edges(
        "intent_classifier",
        _after_intent,
        {"clarification": "clarification", "readback_gate": "readback_gate"},
    )
    graph.add_conditional_edges(
        "clarification",
        _after_clarification,
        {"intent_classifier": "intent_classifier"},
    )
    graph.add_conditional_edges(
        "readback_gate",
        _after_readback_gate,
        {
            "readback": "readback",
            "planner": "planner",
            "rag_agent": "rag_agent",
            "sql_agent": "sql_agent",
        },
    )
    graph.add_conditional_edges(
        "readback",
        _after_readback,
        {
            "intent_classifier": "intent_classifier",
            "planner": "planner",
            "rag_agent": "rag_agent",
            "sql_agent": "sql_agent",
        },
    )

    # Hybrid execution chain.
    graph.add_edge("planner", "hybrid_executor")
    graph.add_edge("hybrid_executor", "synthesiser")
    graph.add_edge("synthesiser", "critic")

    # SQL / RAG direct -> critic.
    graph.add_edge("sql_agent", "critic")
    graph.add_edge("rag_agent", "critic")

    # Critic branching.
    graph.add_conditional_edges(
        "critic",
        _after_critic,
        {"cross_validator": "cross_validator", "completeness_gate": "completeness_gate"},
    )
    graph.add_conditional_edges(
        "cross_validator",
        _after_cross_validator,
        {"arbiter": "arbiter", "completeness_gate": "completeness_gate"},
    )
    graph.add_edge("arbiter", "completeness_gate")

    # Completeness gate: final recall check before finalising.
    graph.add_conditional_edges(
        "completeness_gate",
        _after_completeness_gate,
        {"completeness_checker": "completeness_checker", "finaliser": "finaliser"},
    )
    graph.add_conditional_edges(
        "completeness_checker",
        _after_completeness,
        {"completeness_reground": "completeness_reground", "finaliser": "finaliser"},
    )
    graph.add_edge("completeness_reground", "finaliser")

    graph.add_edge("finaliser", END)

    checkpointer = MemorySaver()  # will upgrade to Redis in Phase 8
    return graph.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_graph():
    return _build_graph()
