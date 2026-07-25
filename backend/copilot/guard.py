"""Deterministic guardrails (§4.6): the ported numeric-sanity gate and the
NEW guilt-language guard + caveat finaliser — §1.5 enforced in code.

The RED_FLAG_LEXICON replaces the archive's POLICY_LEXICON; it will drive the
grounding gate once the RAG corpus lands (next slice) and is exported now so
the lexicon is reviewed with this port, not invented later."""

from __future__ import annotations

import re

from collusiongraph import SCREENING_CAVEAT

RED_FLAG_LEXICON: set[str] = {
    "smurfing",
    "structuring",
    "layering",
    "placement",
    "integration",
    "fan-in",
    "fan-out",
    "pass-through",
    "cycle",
    "shell company",
    "beneficial owner",
    "bid rotation",
    "cover bidding",
    "cover bid",
    "market allocation",
    "market partition",
    "common control",
    "winner rotation",
    "complementary bid",
}

# guilt-asserting phrasings → screening-language rewrites (§1.5). Applied
# case-insensitively; the list is deliberately blunt — false positives cost a
# softer sentence, false negatives cost the project's scope boundary.
_GUILT_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.IGNORECASE), r)
    for p, r in [
        (r"\bis guilty of\b", "shows flagged patterns consistent with"),
        (r"\bare guilty of\b", "show flagged patterns consistent with"),
        (r"\bguilty\b", "flagged"),
        (
            r"\bcommitted (fraud|money laundering|collusion|a crime)\b",
            r"shows patterns consistent with \1",
        ),
        (r"\bis (a|the) (criminal|fraudster|launderer)\b", "is a flagged entity"),
        (r"\bare (criminals|fraudsters|launderers)\b", "are flagged entities"),
        (r"\bproves? (that )?\b", "is consistent with "),
        (r"\bbroke the law\b", "shows patterns that warrant review"),
        (r"\bis laundering money\b", "shows patterns consistent with laundering typologies"),
        (r"\bis definitely (fraudulent|colluding|illicit)\b", r"is flagged as potentially \1"),
    ]
]

_NUMBER_RE = re.compile(r"(?<![\w.])\d{2,}(?:,\d{3})*(?:\.\d+)?(?![\w.])")


def grounding_gate(question: str, trace: list[str]) -> tuple[bool, list[str]]:
    """Ported §4.6 gate, re-lexiconed: red-flag/typology terms in the QUESTION
    require a corpus_search call in the trace (citations must be possible).
    Returns (ok, triggering_terms)."""
    q = question.lower()
    terms = sorted(t for t in RED_FLAG_LEXICON if t in q)
    if not terms:
        return True, []
    searched = any(t.startswith("corpus_search(") for t in trace)
    return searched, terms


# A decoder that falls apart emits the same token forever. Measured live
# 2026-07-25: the question "your XGBoost baseline beats the graph neural
# network, does that mean the deep learning part is useless?" produced 168
# seconds of "<unk><unk><unk>…". Releasing that to an investigator is worse
# than releasing nothing, so it is caught before the answer leaves the agent.
_DEGENERATE_PATTERNS = (
    re.compile(r"(?:<unk>\s*){8,}", re.I),
    re.compile(r"(?:<\|[^|>]*\|>\s*){8,}"),
    re.compile(r"(.{1,24}?)\1{15,}", re.S),  # any short chunk repeated 16x+
)

DEGENERATE_FALLBACK = (
    "I could not produce a reliable answer to that question — the model's "
    "response failed a quality check before release, so it was withheld rather "
    "than shown. Please ask again, ideally more specifically."
)


def degenerate_output_gate(answer: str) -> tuple[bool, str | None]:
    """True when the model's own output is broken (token-repetition collapse).

    Returns (is_degenerate, matched_pattern). A degenerate answer must never be
    released: it cannot be grounded, cannot be checked, and reads as a crash.
    """
    probe = answer.strip()
    if not probe:
        return True, "empty answer"
    for pattern in _DEGENERATE_PATTERNS:
        if pattern.search(probe):
            return True, pattern.pattern
    # a wall of one repeated character with almost no variety
    if len(probe) > 200 and len(set(probe)) <= 6:
        return True, "near-zero character variety"
    return False, None


def apply_guilt_guard(answer: str) -> tuple[str, list[str]]:
    """Rewrite guilt-asserting phrasings and append the screening caveat.
    Returns (safe_answer, list of rewrites applied)."""
    rewrites: list[str] = []
    for pattern, replacement in _GUILT_REWRITES:
        if pattern.search(answer):
            rewrites.append(pattern.pattern)
            answer = pattern.sub(replacement, answer)
    if SCREENING_CAVEAT.lower() not in answer.lower():
        answer = f"{answer.rstrip()}\n\n---\n*{SCREENING_CAVEAT}*"
    return answer, rewrites


def numeric_sanity_gate(answer: str, evidence_text: str) -> tuple[bool, list[str]]:
    """Ported §4.6 gate: every multi-digit number the answer claims must
    appear in the tool evidence. Returns (ok, unsupported_numbers)."""
    claimed = set(_NUMBER_RE.findall(answer))
    if not claimed:
        return True, []
    seen = set(_NUMBER_RE.findall(evidence_text))
    seen |= {n.replace(",", "") for n in seen}
    unsupported = sorted(n for n in claimed if n not in seen and n.replace(",", "") not in seen)
    return (len(unsupported) == 0, unsupported)
