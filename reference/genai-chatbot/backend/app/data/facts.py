"""
Deterministic fact catalog loader.

The curated `facts.yaml` file is the structured-fact layer: every important
policy or strategic fact from the 10 PDFs is stored here with categories.
At inference, we use the user's question + intent to select categories, and
return every matching fact. This gives the Planner and downstream agents a
recall floor that pure semantic RAG cannot guarantee.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Two sources: hand-curated facts (take precedence on conflicts) and
# auto-extracted facts (regenerated on every ingest).
CURATED_FACTS_PATH = Path(__file__).parent / "facts_curated.yaml"
AUTO_FACTS_PATH = Path(__file__).parent / "facts_auto.yaml"
# Legacy fallback for installs that predate the split.
LEGACY_FACTS_PATH = Path(__file__).parent / "facts.yaml"


@dataclass(frozen=True)
class Fact:
    id: str
    text: str
    source: str
    categories: tuple[str, ...]
    origin: str = "curated"  # "curated" | "auto_pdf" | "auto_schema"

    def as_prompt_line(self) -> str:
        return f"- [{self.id}] {self.text}  (source: {self.source})"


# Keywords that trigger each category. Each category uses OR over its keyword
# set; a question matching any keyword gets every fact in that category.
CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "ipo_readiness": {
        "ipo", "drhp", "listing", "pre-ipo", "public offering", "filing",
        "before the ipo", "before we file", "in the runup", "pre ipo",
    },
    "ipo_milestone": {
        "ipo target", "customer target", "nrr", "retention rate",
        "consecutive quarter", "soc 2", "iso 27001",
    },
    "ipo_timeline": {"drhp", "q3 fy", "september 2026", "ipo timing", "ipo date"},
    "nrr": {"nrr", "net revenue retention", "retention rate"},
    "customer_growth": {"3,500", "3500", "customer target", "logo target", "new logos"},
    "valuation": {"valuation", "pre-money", "pre money", "issue size"},
    "legal": {"legal counsel", "lawyer", "brlm", "book running", "law firm"},
    "breach": {
        "breach", "incident", "inc-2025", "attack", "cyber incident",
        "data exfiltration", "security event", "cybersecurity",
    },
    "breach_absorption": {
        "absorb", "afford", "headroom", "cover the cost", "cover the breach",
        "budget to absorb", "breach cost", "breach bill", "cost us",
    },
    "liquidity": {
        "cash", "fcf", "free cash flow", "liquidity", "reserves", "on hand",
        "afford", "absorb", "debt", "runway",
    },
    "insurance": {"insurance", "cyber cover", "icici lombard", "insured", "policy"},
    "cybersecurity_budget": {
        "cybersecurity", "cyber spend", "cyber budget", "zero trust",
        "security investment", "security budget",
    },
    "regulatory": {
        "regulatory", "cert-in", "dpdp", "data privacy", "data protection",
        "regulatory filing", "regulatory cost", "regulatory bill", "legal bill",
    },
    "data_localization": {
        "localization", "localisation", "data residency", "sovereignty",
        "in-country", "vietnam", "indonesia",
    },
    "cert_in": {"cert-in", "cert in", "filing window", "6 hour", "six hour"},
    "dpdp": {"dpdp", "data protection", "personal data"},
    "compliance": {
        "compliant", "compliance", "flagged", "overdue", "behind", "mandatory",
        "training", "dashboard flag",
    },
    "training": {
        "training", "certification", "module", "infosec", "posh", "abac", "dpdp",
    },
    "threshold": {"threshold", "below 90", "90%", "flag threshold"},
    "certification": {
        "certification", "soc 2", "iso 27001", "aws sap", "cka", "cipp",
        "ml engineer cert",
    },
    "talent": {
        "employee", "engineer", "talent", "retention", "lock in", "lock-in",
        "esop", "salary", "ctc", "bonus", "counter-offer",
    },
    "esop": {"esop", "stock option", "vested", "vesting", "dilution", "fmv"},
    "retention": {
        "retention", "lock in", "lock-in", "counter-offer", "retain", "attrite",
    },
    "compensation": {
        "salary", "ctc", "bonus", "pay", "compensation", "variable pay",
    },
    "governance": {"governance", "board", "committee", "audit"},
    "on_call": {"on-call", "on call", "oncall", "stipend", "primary", "secondary"},
    "incident_response": {
        "incident", "response time", "sev-1", "sev-2", "on-call", "on call",
        "runbook",
    },
    "sla": {"sla", "uptime", "response time", "availability"},
    "vendor_risk": {
        "vendor", "sig-lite", "sig lite", "flagged vendor", "conditional",
        "suspended", "vendor risk",
    },
    "cloud_infrastructure": {
        "aws", "gcp", "snowflake", "cloud vendor", "cloud spend",
    },
    "ai_investment": {
        "ai", "ml", "artificial intelligence", "machine learning", "gpu",
        "a100", "ai/ml", "ai spend", "ai infra",
    },
    "ai_concentration": {
        "ai cluster", "single cluster", "ai concentration", "ai redundancy",
        "regional redundancy", "critical ai",
    },
    "infrastructure": {
        "architecture", "platform", "microservice", "cluster", "kubernetes",
        "deployment",
    },
    "criticality": {"critical", "criticality tier", "sev-1", "criticality"},
    "service_taxonomy": {"domain", "analytics engine", "ai services", "user management"},
    "customer_base": {"customer count", "enterprise customers", "2,847", "43 countries"},
    "customer_retention": {
        "churn", "at risk", "retention", "nrr", "expansion", "renewal",
    },
    "customer_relationship": {
        "tier 1", "tier 2", "tier-1", "account manager", "arr", "customer",
    },
    "geopolitical": {"geopolitical", "vietnam", "indonesia", "apac risk"},
    "apac": {"apac", "asia pacific", "asia-pacific"},
    "geo_expansion": {"singapore", "data centre", "data center", "expansion"},
    "budget": {
        "budget", "utilization", "utilised", "utilised", "headroom", "unspent",
        "overspend", "underspend", "allocation",
    },
    "engineering": {"engineering", "engineering budget", "engineering dept"},
    "capex": {"capex", "capital expenditure", "hardware purchase"},
    "financial_baseline": {
        "revenue", "ebitda", "fcf", "margin", "balance sheet", "cash",
        "financial", "baseline",
    },
    "revenue": {"revenue", "arr", "top-line", "top line"},
    "profitability": {"ebitda", "margin", "profit"},
    "reconciliation": {
        "align", "line up", "reconcile", "match", "gap", "vs",
        "actual vs reported", "discrepancy",
    },
    "finance_query": {
        "category", "subcategory", "transaction", "spend", "expenditure",
    },
    "data_model": {"table", "schema", "column", "row count", "how many"},
    "strategy": {
        "strategy", "roadmap", "plan", "next year", "fy26", "fy27", "scale",
        "scaling",
    },
    "security": {
        "security", "soc 2", "iso 27001", "zero trust", "compliance-grade",
    },
}


def _load_yaml_facts(path: Path, default_origin: str) -> list[Fact]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    facts_raw = data.get("facts", []) or []
    out: list[Fact] = []
    for f in facts_raw:
        origin = str(f.get("origin") or default_origin)
        out.append(Fact(
            id=str(f["id"]),
            text=str(f["text"]),
            source=str(f["source"]),
            categories=tuple(f.get("categories", []) or []),
            origin=origin,
        ))
    return out


@lru_cache(maxsize=1)
def get_all_facts() -> tuple[Fact, ...]:
    """Load curated + auto-extracted facts, dedup by text, curated wins on collision."""
    curated = _load_yaml_facts(CURATED_FACTS_PATH, default_origin="curated")
    auto = _load_yaml_facts(AUTO_FACTS_PATH, default_origin="auto_pdf")

    if not curated and not auto and LEGACY_FACTS_PATH.exists():
        # Backwards-compatibility: load the pre-split file if split files don't exist yet.
        curated = _load_yaml_facts(LEGACY_FACTS_PATH, default_origin="curated")

    # Dedup: curated facts shadow auto facts with identical text.
    seen_texts: set[str] = set()
    merged: list[Fact] = []
    for f in list(curated) + list(auto):
        key = f.text.strip().lower()
        if key in seen_texts:
            continue
        seen_texts.add(key)
        merged.append(f)

    logger.info(
        "FactLoader: %d curated + %d auto = %d unique facts",
        len(curated), len(auto), len(merged),
    )
    return tuple(merged)


# Co-activation: detecting one "parent" category implicitly expands to related
# facets so that facts tagged with the narrower child still get loaded. Without
# this, a question that says "IPO" but not literally "NRR" or "SOC 2" would
# miss the NRR-threshold and certification-milestone facts, which are exactly
# the sharpest IPO-timeline arguments.
_CATEGORY_EXPANSIONS: dict[str, set[str]] = {
    "ipo_readiness":        {"ipo_milestone", "ipo_timeline", "nrr", "customer_growth", "valuation", "certification"},
    "ipo_timeline":         {"ipo_readiness", "ipo_milestone"},
    "breach":               {"breach_absorption", "cybersecurity_budget", "incident_baseline", "insurance"},
    "breach_absorption":    {"insurance", "liquidity", "cybersecurity_budget", "financial_baseline"},
    "ai_investment":        {"ai_concentration", "infrastructure"},
    "ai_concentration":     {"infrastructure", "ai_investment"},
    "regulatory":           {"cert_in", "dpdp", "data_privacy", "legal"},
    "data_localization":    {"geopolitical", "apac"},
    "compliance":           {"training", "threshold"},
    "vendor_risk":          {"compliance", "cloud_infrastructure"},
    "retention":            {"talent", "compensation", "esop"},
    "reconciliation":       {"budget", "financial_baseline"},
    "liquidity":            {"financial_baseline", "revenue"},
    "budget":               {"financial_baseline", "engineering", "capex"},
}


def detect_categories(text: str) -> set[str]:
    """Return the set of categories whose keywords appear in `text`, plus any
    co-activation children."""
    lower = text.lower()
    hits: set[str] = set()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in lower for k in keywords):
            hits.add(category)
    # Expand via co-activation (one pass — not recursive, to keep output stable).
    expanded = set(hits)
    for parent in hits:
        expanded.update(_CATEGORY_EXPANSIONS.get(parent, set()))
    return expanded


_ORIGIN_RANK: dict[str, int] = {
    "curated": 0,
    "auto_schema": 1,
    "auto_pdf": 2,
}


def load_facts_for_text(text: str, max_facts: int = 20) -> list[Fact]:
    """Detect categories from text and return relevant facts.

    Selection order (for ties and overall ranking):
      1. Highest category-overlap first (more matching categories = more relevant).
      2. CURATED facts win ties over auto-extracted ones — hand-picked
         high-value facts like IPO-milestone thresholds never get displaced by
         noisy auto facts.
      3. Stable alphabetical by id.

    Hard cap to keep prompts bounded. Max set to 20 (down from 30) to prevent
    attention dilution across too many competing facts.
    """
    categories = detect_categories(text)
    if not categories:
        return []
    scored: list[tuple[int, int, Fact]] = []
    for fact in get_all_facts():
        overlap = len(set(fact.categories) & categories)
        if overlap:
            origin_rank = _ORIGIN_RANK.get(fact.origin, 9)
            scored.append((-overlap, origin_rank, fact))
    # Tuple sort: overlap desc, origin_rank asc, id asc.
    scored.sort(key=lambda t: (t[0], t[1], t[2].id))
    return [f for _, _, f in scored[:max_facts]]


def format_facts_block(facts: list[Fact]) -> str:
    """Render a list of facts as a Markdown block suitable for a prompt."""
    if not facts:
        return "(no structured facts matched)"
    return "\n".join(f.as_prompt_line() for f in facts)


def format_facts_for_text(text: str, max_facts: int = 25) -> str:
    return format_facts_block(load_facts_for_text(text, max_facts=max_facts))
