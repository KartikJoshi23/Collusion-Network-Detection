"""Alert unit, hit rule, and NMS deduplication (§4.5) — without these,
subgraph-level Precision@k is ill-defined.

* **Alert unit:** a community/subgraph alert (§3.2 schema), never a bare node.
* **Hit rule (primary):** an alert is a true positive iff it contains ≥1
  confirmed illicit member. Stricter fractional rules (≥10%, ≥25% of members
  confirmed) are the Phase-2 sensitivity analysis — supported via
  ``min_fraction`` so the harness needs no rewrite then.
* **Deduplication:** greedy non-maximum suppression, rank-ascending; an alert
  is suppressed when its member-set Jaccard overlap with an already-accepted
  alert exceeds the threshold (default 0.5, itself ablated later).
* **Size cap:** alerts with more than ``max_members`` members (default 100)
  are excluded up front so a single mega-community cannot absorb the budget.

Only confirmed labels count: ``unknown`` members are neither hits nor misses
(§4.3 D1 unknown-label policy).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from collusiongraph.schema import Label

DEFAULT_JACCARD_THRESHOLD = 0.5
DEFAULT_MAX_MEMBERS = 100


@dataclass(frozen=True)
class DedupResult:
    """Alerts annotated with ``kept``/``overlap_group``; suppressed rows stay
    inspectable (they carry the group of the alert that suppressed them)."""

    alerts: pl.DataFrame
    report: dict = field(default_factory=dict)

    @property
    def kept(self) -> pl.DataFrame:
        return self.alerts.filter(pl.col("kept")).drop("kept")


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def nms_dedup(
    alerts: pl.DataFrame,
    jaccard_threshold: float = DEFAULT_JACCARD_THRESHOLD,
    max_members: int = DEFAULT_MAX_MEMBERS,
) -> DedupResult:
    """Greedy NMS over the ranked alert queue (§4.5).

    Rank-ascending (rank 1 first); suppress any alert whose member-set Jaccard
    overlap with an accepted alert is **strictly greater** than the threshold.
    """
    n_oversized = alerts.filter(pl.col("n_members") > max_members).height
    eligible = alerts.filter(pl.col("n_members") <= max_members).sort("rank")

    member_sets = [set(m) for m in eligible["member_node_ids"].to_list()]
    kept_flags: list[bool] = []
    groups: list[int] = []
    accepted: list[tuple[int, set[str]]] = []  # (group id, member set)
    for members in member_sets:
        suppressor = next(
            (g for g, acc in accepted if jaccard(members, acc) > jaccard_threshold), None
        )
        if suppressor is None:
            group = len(accepted)
            accepted.append((group, members))
            kept_flags.append(True)
            groups.append(group)
        else:
            kept_flags.append(False)
            groups.append(suppressor)

    annotated = eligible.with_columns(
        pl.Series("kept", kept_flags, dtype=pl.Boolean),
        pl.Series("overlap_group", groups, dtype=pl.Int32),
    )
    return DedupResult(
        alerts=annotated,
        report={
            "jaccard_threshold": jaccard_threshold,
            "max_members": max_members,
            "n_input": alerts.height,
            "n_oversized_excluded": n_oversized,
            "n_kept": sum(kept_flags),
            "n_suppressed": len(kept_flags) - sum(kept_flags),
        },
    )


def apply_hit_rule(
    alerts: pl.DataFrame,
    labels: pl.DataFrame,
    min_confirmed: int = 1,
    min_fraction: float | None = None,
) -> pl.DataFrame:
    """Label each alert under the §4.5 hit rule.

    Adds ``n_illicit_members``, ``n_confirmed_members`` (illicit + licit — the
    denominator for fractional rules; unknowns are neither), and ``is_hit``.
    ``min_fraction`` (e.g. 0.25) switches to the stricter Phase-2 rule:
    illicit share of *confirmed* members must reach the fraction (and at least
    ``min_confirmed`` illicit members must exist).
    """
    per_alert = (
        alerts.select("alert_id", "member_node_ids")
        .explode("member_node_ids", empty_as_null=False)
        .rename({"member_node_ids": "node_id"})
        .join(labels.select("node_id", "label"), on="node_id", how="left")
        .group_by("alert_id")
        .agg(
            (pl.col("label") == Label.ILLICIT.value).sum().alias("n_illicit_members"),
            pl.col("label")
            .is_in([Label.ILLICIT.value, Label.LICIT.value])
            .sum()
            .alias("n_confirmed_members"),
        )
    )
    hit = pl.col("n_illicit_members") >= min_confirmed
    if min_fraction is not None:
        hit = hit & (
            pl.col("n_illicit_members")
            >= (pl.col("n_confirmed_members").cast(pl.Float64) * min_fraction)
        )
    return alerts.join(per_alert, on="alert_id", how="left").with_columns(
        pl.col("n_illicit_members").fill_null(0),
        pl.col("n_confirmed_members").fill_null(0),
        hit.fill_null(False).alias("is_hit"),
    )
