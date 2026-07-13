"""CollusionGraph — explainable, imbalance-robust graph collusion detection.

A risk-screening and triage instrument that ranks cases for human
investigation. It is not an accusation engine and produces no
determination of guilt (implementation-plan.md §1.5).
"""

__version__ = "0.1.0"

# Fixed caveat attached to every alert and every API response (§3.2, R11).
SCREENING_CAVEAT = "screening signal only — no determination of guilt"
