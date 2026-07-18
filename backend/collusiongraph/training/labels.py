"""Training-label policies (audit F1): what a supervisor could have known.

``resolve_train_labels`` returns the label frame every TRAINING-side consumer
(loss pools, rule thresholds, calibration fits) must use. The default policy
returns the stored labels — correct where labels are intrinsic to the node at
its own timestamp (Elliptic transaction classes). ``mendeley_as_of`` derives
firm labels from award-level ground truth at ``train_end``, because the stored
Mendeley labels roll up a firm's ENTIRE history and would leak future cartel
activity into train-period targets. ``history_as_of`` is the general form for
datasets whose adapter writes a ``label_history`` feature pack of per-step
class observations (Elliptic++ actor wallets; AMLworld when it lands): a node
is illicit if any illicit observation exists at or before ``train_end``,
licit if it has known observations and none illicit, absent otherwise.

Test-side EVALUATION always uses the stored full-knowledge labels — ground
truth is assessed after the fact; training targets must not be.
"""

from __future__ import annotations

import polars as pl

from collusiongraph.adapters.procurement import mendeley_firm_labels_as_of
from collusiongraph.schema import GraphStore, Label

POLICIES = ("static", "mendeley_as_of", "history_as_of")


def load_label_history(store: GraphStore, dataset: str, policy: str) -> pl.DataFrame | None:
    """The dataset's ``label_history`` pack when ``policy`` needs it — the one
    place every training-side consumer (trainer, queue calibration) gets it."""
    if policy != "history_as_of":
        return None
    return store.read_features(dataset, "label_history")


def history_labels_as_of(history: pl.DataFrame, as_of: int) -> pl.DataFrame:
    """Per-step observations (node_id, step, label) → as-of label frame."""
    return (
        history.filter(pl.col("step") <= as_of)
        .group_by("node_id")
        .agg(
            pl.when(pl.col("label").eq(Label.ILLICIT.value).any())
            .then(pl.lit(Label.ILLICIT.value))
            .otherwise(pl.lit(Label.LICIT.value))
            .alias("label")
        )
        .select(
            "node_id",
            "label",
            pl.lit("history_as_of").alias("label_source"),
            pl.lit(1.0, dtype=pl.Float32).alias("confidence"),
        )
    )


def resolve_train_labels(
    policy: str,
    labels: pl.DataFrame,
    edges: pl.DataFrame,
    as_of: int,
    history: pl.DataFrame | None = None,
) -> pl.DataFrame:
    if policy == "static":
        return labels
    if policy == "mendeley_as_of":
        return mendeley_firm_labels_as_of(edges, as_of)
    if policy == "history_as_of":
        if history is None:
            raise ValueError("history_as_of requires the dataset's label_history feature pack")
        return history_labels_as_of(history, as_of)
    raise ValueError(f"unknown train_label_policy {policy!r} (expected one of {POLICIES})")
