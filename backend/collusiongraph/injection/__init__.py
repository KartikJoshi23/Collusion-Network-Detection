"""Synthetic motif injection (§4.4 item 4): all five motif-table rows, both domains."""

from .injector import GENERATORS, InjectionResult, inject, recovery_at_budget

__all__ = ["GENERATORS", "InjectionResult", "inject", "recovery_at_budget"]
