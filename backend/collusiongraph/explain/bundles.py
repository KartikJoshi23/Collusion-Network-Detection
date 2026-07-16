"""Explanation bundles (§4.4 schema, §7 step 19): one validated JSON per alert.

An unexplained flag is a non-deliverable (P1.4). Every bundle labels which
evidence came from which source (learned explainer / structural matcher /
screens — §4.4 scope honesty), adapts evidence fields to the dataset's
declared coverage (D1: Elliptic has no amounts → structural + temporal
evidence leads), and carries the immutable screening-only caveat. The §9.1
invariants are enforced at construction: non-empty minimal subgraph ⊆ input
graph, red flags resolve to curated indicators, caveat unconstructable
weakened.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl
import torch
from pydantic import BaseModel, Field, field_validator

from collusiongraph import SCREENING_CAVEAT
from collusiongraph.eval import load_config
from collusiongraph.explain.explainer_runner import attention_summaries, explain_nodes
from collusiongraph.explain.motif_matcher import match_motifs
from collusiongraph.explain.redflags import map_red_flags
from collusiongraph.models.gnn import make_model
from collusiongraph.schema import GraphStore
from collusiongraph.training.baseline_run import raw_feature_frame
from collusiongraph.training.graph_build import build_graph

_TIME = "time_first_seen"


class MinimalSubgraph(BaseModel):
    nodes: list[str] = Field(min_length=1)
    edges: list[tuple[str, str]]


class ExplanationBundle(BaseModel):
    """§4.4 bundle schema — validated, never hand-assembled JSON."""

    alert_id: str
    domain: str
    dataset: str
    rank: int = Field(ge=1)
    risk_score: float
    budget_position: int = Field(ge=1)
    minimal_subgraph: MinimalSubgraph
    attention_summary: dict[str, Any] | None = None
    motif: dict[str, Any] | None = None
    evidence: dict[str, Any]
    evidence_sources: dict[str, list[str]]
    red_flags: list[dict[str, str]]
    fidelity: dict[str, float] | None = None
    # §9.1 sanity: fidelity+ >= fidelity−. Recorded, never silently dropped —
    # an insane explanation ships flagged so the queue is never blocked but
    # the defect is visible (audit F13).
    fidelity_sane: bool | None = None
    caveats: str = SCREENING_CAVEAT

    @field_validator("caveats")
    @classmethod
    def _fixed_caveat(cls, v: str) -> str:
        if v != SCREENING_CAVEAT:
            raise ValueError("the bundle caveat is fixed and must not be altered")
        return v

    @field_validator("red_flags")
    @classmethod
    def _flags_resolve(cls, flags: list[dict[str, str]]) -> list[dict[str, str]]:
        required = {"framework", "indicator_id", "indicator_text", "matched_because"}
        for flag in flags:
            if not required <= set(flag):
                raise ValueError(f"red flag missing fields: {sorted(required - set(flag))}")
        return flags


def build_bundle(
    alert: dict[str, Any],
    domain: str,
    dataset: str,
    member_edges: pl.DataFrame,
    nodes: pl.DataFrame,
    explanation: Any | None,
    budget_position: int,
    attention: dict[str, float] | None = None,
    matcher_params: dict[str, float] | None = None,
) -> ExplanationBundle:
    """Assemble one alert's bundle from matcher + (optional) explainer output."""
    matches = match_motifs(member_edges, domain, **(matcher_params or {}))
    top_match = max(matches, key=lambda m: len(m.member_node_ids), default=None)
    red_flags = map_red_flags(matches, domain)

    members = list(alert["member_node_ids"])
    member_times = nodes.filter(pl.col("node_id").is_in(members))[_TIME].cast(pl.Int64)
    t_min, t_max = member_times.min(), member_times.max()
    evidence: dict[str, Any] = {
        "time_window": [alert.get("time_window_start"), alert.get("time_window_end")],
        "n_members": alert["n_members"],
        "n_member_edges": member_edges.height,
        "member_time_span": [
            t_min if isinstance(t_min, int) else None,
            t_max if isinstance(t_max, int) else None,
        ],
    }
    amounts = member_edges["amount"].drop_nulls().cast(pl.Float64)
    amount_max = amounts.max()
    if isinstance(amount_max, float):  # amount evidence only where amounts exist (D1)
        evidence["amount_total"] = float(amounts.sum())
        evidence["amount_max"] = amount_max

    if explanation is not None:
        subgraph = MinimalSubgraph(
            nodes=explanation.subgraph_node_ids, edges=explanation.subgraph_edges
        )
        fidelity = {
            "fidelity_plus": explanation.fidelity_plus,
            "fidelity_minus": explanation.fidelity_minus,
        }
        fidelity_sane = explanation.fidelity_plus >= explanation.fidelity_minus
        learned = [f"gnn_explainer(top member {explanation.node_id})"]
        if attention is not None:
            learned.append("gatv2_attention(top member incoming messages)")
    else:
        subgraph = MinimalSubgraph(
            nodes=members,
            edges=list(member_edges.select("src", "dst").iter_rows()),
        )
        fidelity = None
        fidelity_sane = None
        learned = []

    return ExplanationBundle(
        alert_id=alert["alert_id"],
        domain=domain,
        dataset=dataset,
        rank=alert["rank"],
        risk_score=alert["risk_score"],
        budget_position=budget_position,
        minimal_subgraph=subgraph,
        attention_summary=attention,
        motif=({"type": top_match.motif_type, "params": top_match.params} if top_match else None),
        evidence=evidence,
        evidence_sources={
            "learned": learned,
            "structural": [m.because() for m in matches],
            "screen": [],
        },
        red_flags=red_flags,
        fidelity=fidelity,
        fidelity_sane=fidelity_sane,
    )


def run_explanations(config: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Config-driven batch writer: top-k alerts → validated bundle JSONs."""
    cfg = load_config(config)
    store = GraphStore(cfg.get("store_root", "data/interim"))
    dataset: str = cfg["dataset"]
    domain: str = cfg["domain"]
    top_k: int = cfg.get("top_k", 50)
    out_dir = Path(cfg["output_dir"])

    nodes = store.read(dataset, "nodes")
    edges = store.read(dataset, "edges")
    alerts = pl.read_parquet(cfg["alerts"]).sort("rank").head(top_k)

    explanations: dict[str, Any] = {}
    attention: dict[str, dict[str, float]] = {}
    top_member_of: dict[str, str] = {}
    if "supervised_model" in cfg:
        explanations, attention, top_member_of = _explain_top_members(
            cfg, store, nodes, edges, alerts
        )

    matcher_params = cfg.get("matcher", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for position, alert in enumerate(alerts.iter_rows(named=True), start=1):
        members = alert["member_node_ids"]
        member_set = pl.Series(members).implode()
        member_edges = edges.filter(
            pl.col("src").is_in(member_set) & pl.col("dst").is_in(member_set)
        )
        top_member = top_member_of.get(alert["alert_id"])
        bundle = build_bundle(
            alert,
            domain,
            dataset,
            member_edges,
            nodes,
            explanations.get(top_member) if top_member else None,
            budget_position=position,
            attention=attention.get(top_member) if top_member else None,
            matcher_params=matcher_params,
        )
        path = out_dir / f"{bundle.alert_id.replace(':', '_')}.json"
        path.write_text(bundle.model_dump_json(indent=2) + "\n", encoding="utf-8")
        written.append(
            {
                "alert_id": bundle.alert_id,
                "motif": bundle.motif["type"] if bundle.motif else None,
                "n_red_flags": len(bundle.red_flags),
                "fidelity": bundle.fidelity,
                "fidelity_sane": bundle.fidelity_sane,
                "attention": bundle.attention_summary is not None,
            }
        )

    summary = {
        "dataset": dataset,
        "n_bundles": len(written),
        "n_with_motif": sum(1 for w in written if w["motif"]),
        "n_with_red_flags": sum(1 for w in written if w["n_red_flags"]),
        "n_with_fidelity": sum(1 for w in written if w["fidelity"]),
        "n_fidelity_insane": sum(1 for w in written if w["fidelity_sane"] is False),
        "n_with_attention": sum(1 for w in written if w["attention"]),
        "bundles": written,
    }
    (out_dir / "explanations_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def _explain_top_members(
    cfg: dict[str, Any],
    store: GraphStore,
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    alerts: pl.DataFrame,
) -> tuple[dict[str, Any], dict[str, dict[str, float]], dict[str, str]]:
    """GNNExplainer over each alert's highest-scored member (§4.4: k ≤ 200
    bounds the per-alert optimization budget). Returns (explanations by node,
    attention summaries by node, top member by alert id)."""
    model_cfg = dict(cfg["supervised_model"])
    checkpoint = model_cfg.pop("checkpoint")
    name = model_cfg.pop("name")
    model_cfg.pop("features", None)  # feature kind comes from the checkpoint's stats
    n_raw = store.read_meta(cfg["dataset"]).get("n_features", 0)

    # the model is explained under the SAME frozen normalization it was
    # trained and scored with (audit F3) — never re-fit on the explained graph
    from collusiongraph.features import apply_zscore, structural_features
    from collusiongraph.training.ensemble_run import load_feature_stats

    feature_kind, stats = load_feature_stats(checkpoint)
    if feature_kind == "raw":
        raw = raw_feature_frame(nodes, n_raw)
    else:
        raw = structural_features(nodes, edges)
    data = build_graph(nodes, edges, store.read(cfg["dataset"], "labels"), apply_zscore(raw, stats))
    model = make_model(
        name, in_dim=data.x.shape[1], num_relations=int(data.num_relations), **model_cfg
    )
    model.load_state_dict(torch.load(checkpoint, weights_only=True))
    model.eval()

    scores = pl.read_parquet(cfg["member_scores"])
    top_member_of: dict[str, str] = {}
    for alert in alerts.iter_rows(named=True):
        member_scores = scores.filter(
            pl.col("node_id").is_in(pl.Series(alert["member_node_ids"]).implode())
        )
        if not member_scores.is_empty():
            top_member_of[alert["alert_id"]] = member_scores.sort("score", descending=True)[
                "node_id"
            ][0]
    targets = sorted(set(top_member_of.values()))
    explanations = explain_nodes(
        model,
        data,
        targets,
        num_hops=cfg.get("num_hops", 2),
        epochs=cfg.get("explainer_epochs", 100),
        top_edges=cfg.get("top_edges", 20),
        seed=cfg.get("seed", 0),
    )
    from collusiongraph.models.gnn import GATv2

    attention = attention_summaries(model, data, targets) if isinstance(model, GATv2) else {}
    return explanations, attention, top_member_of
