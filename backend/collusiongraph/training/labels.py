"""Training-label policies (audit F1): what a supervisor could have known.

``resolve_train_labels`` returns the label frame every TRAINING-side consumer
(loss pools, rule thresholds, calibration fits) must use. The default policy
returns the stored labels — correct where labels are intrinsic to the node at
its own timestamp (Elliptic transaction classes). ``mendeley_as_of`` derives
firm labels from award-level ground truth at ``train_end``, because the stored
Mendeley labels roll up a firm's ENTIRE history and would leak future cartel
activity into train-period targets.

Test-side EVALUATION always uses the stored full-knowledge labels — ground
truth is assessed after the fact; training targets must not be. The same
future-rollup caveat applies to AMLworld node labels (edge-level laundering
rolled up over all time) — a policy for it lands with the AMLworld runs.
"""

from __future__ import annotations

import polars as pl

from collusiongraph.adapters.procurement import mendeley_firm_labels_as_of

POLICIES = ("static", "mendeley_as_of")


def resolve_train_labels(
    policy: str,
    labels: pl.DataFrame,
    edges: pl.DataFrame,
    as_of: int,
) -> pl.DataFrame:
    if policy == "static":
        return labels
    if policy == "mendeley_as_of":
        return mendeley_firm_labels_as_of(edges, as_of)
    raise ValueError(f"unknown train_label_policy {policy!r} (expected one of {POLICIES})")
