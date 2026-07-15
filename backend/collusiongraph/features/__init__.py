"""Shared structural template (per-graph z-scoring) + domain feature packs (§4.4).

All feature functions take an ``as_of`` timestamp (§9.1b): with it set, no
feature can encode information from after that time; ``as_of=None`` is reserved
for entity-disjoint (LOCO/LOMO) evaluation where time is not the split axis.
"""

from .financial import financial_features, sinusoidal_time_encoding
from .screens import award_screens, bid_screens, co_bid_stats
from .structural import (
    burstiness,
    restrict_as_of,
    structural_features,
    zscore_per_graph,
)

__all__ = [
    "award_screens",
    "bid_screens",
    "burstiness",
    "co_bid_stats",
    "financial_features",
    "restrict_as_of",
    "sinusoidal_time_encoding",
    "structural_features",
    "zscore_per_graph",
]
