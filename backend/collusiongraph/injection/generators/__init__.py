"""Motif generators, one module per domain (§8 layout, consolidated by domain)."""

from .financial import GENERATORS as FINANCIAL_GENERATORS
from .procurement import GENERATORS as PROCUREMENT_GENERATORS

__all__ = ["FINANCIAL_GENERATORS", "PROCUREMENT_GENERATORS"]
