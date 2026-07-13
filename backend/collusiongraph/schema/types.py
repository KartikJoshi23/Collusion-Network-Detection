"""Closed vocabularies of the CollusionGraph IR (implementation-plan.md §4.2, §4.4).

These enums are the only node/edge/label/motif vocabularies in the system;
adapters map raw datasets onto them and everything downstream is domain-agnostic.
"""

from enum import StrEnum


class Domain(StrEnum):
    FINANCIAL = "financial"
    PROCUREMENT = "procurement"


class NodeType(StrEnum):
    # financial (§4.2: Elliptic++ is a tx–tx graph; AMLworld is an account graph)
    ACCOUNT = "account"
    ADDRESS = "address"
    TRANSACTION = "transaction"
    # procurement
    FIRM = "firm"
    TENDER = "tender"
    BID = "bid"
    LOT = "lot"
    BUYER = "buyer"


class EdgeType(StrEnum):
    # financial
    PAYS = "pays"  # directed, timestamped, amount-attributed money flow
    # both domains (entity linkage where available)
    LINKED_TO = "linked_to"  # shared owners / agents / addresses
    # procurement — core tier (award-derived, always available; §4.2 rule 1)
    AWARDED = "awarded"  # tender -> firm
    BUYS_FROM = "buys_from"  # buyer -> tender
    # procurement — enrichment tier (where bid data exists)
    BIDS_ON = "bids_on"  # firm (or anonymous bid) -> tender, price-attributed
    CO_BID = "co_bid"  # firm -- firm projection of shared tenders


class Label(StrEnum):
    ILLICIT = "illicit"
    LICIT = "licit"
    UNKNOWN = "unknown"


class MotifType(StrEnum):
    """§4.4 explanation-bundle motif vocabulary (all five motif-table rows)."""

    CYCLE = "cycle"
    FAN_IN = "fan_in"
    FAN_OUT = "fan_out"
    COMMON_CONTROL = "common_control"
    PASS_THROUGH = "pass_through"
    ROTATION = "rotation"
    COVER_BID = "cover_bid"
    PARTITION = "partition"
    CLIQUE = "clique"
