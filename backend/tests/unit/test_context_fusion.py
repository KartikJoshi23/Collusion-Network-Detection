"""Context-fusion encoder tests (Appendix A13, §4.4).

The gated encoder is an *ablatable option*: these tests pin its mechanics
(family slicing, gate range, per-node gate variation, backbone delegation)
and prove the trainer wires spans correctly end to end on a tiny store —
model quality is the B-CF ablation's job, not a unit test's.
"""

import numpy as np
import polars as pl
import pytest
import torch
from collusiongraph.models.gnn import ContextFusionEncoder, FusedModel, make_model
from collusiongraph.schema import GraphStore
from collusiongraph.training import train_gnn

RNG = np.random.default_rng(7)


class TestEncoder:
    def test_output_shape_and_gate_range(self) -> None:
        enc = ContextFusionEncoder([5, 3], out_dim=8)
        out = enc(torch.randn(10, 8))
        assert out.shape == (10, 8)
        assert enc.last_gates is not None
        assert enc.last_gates.shape == (10, 2)
        assert ((enc.last_gates > 0) & (enc.last_gates < 1)).all()

    def test_gates_vary_per_node(self) -> None:
        enc = ContextFusionEncoder([4, 4], out_dim=8)
        enc(torch.randn(64, 8))
        assert enc.last_gates is not None
        assert enc.last_gates.std(dim=0).sum() > 0  # not a constant gate

    def test_each_family_reaches_the_output(self) -> None:
        torch.manual_seed(0)
        enc = ContextFusionEncoder([4, 4], out_dim=8)
        x = torch.randn(16, 8)
        base = enc(x)
        for start, end in ((0, 4), (4, 8)):
            perturbed = x.clone()
            perturbed[:, start:end] += 1.0
            assert not torch.allclose(enc(perturbed), base)

    def test_width_mismatch_rejected(self) -> None:
        enc = ContextFusionEncoder([4, 4], out_dim=8)
        with pytest.raises(ValueError, match="do not cover"):
            enc(torch.randn(5, 9))

    def test_single_family_rejected(self) -> None:
        with pytest.raises(ValueError, match=">= 2 feature families"):
            ContextFusionEncoder([7], out_dim=8)


class TestMakeModel:
    def test_gated_wraps_and_concat_does_not(self) -> None:
        gated = make_model("gatv2", in_dim=10, fusion="gated", fusion_spans=[6, 4])
        plain = make_model("gatv2", in_dim=10)
        assert isinstance(gated, FusedModel)
        assert not isinstance(plain, FusedModel)

    def test_spans_must_sum_to_in_dim(self) -> None:
        with pytest.raises(ValueError, match="must sum to in_dim"):
            make_model("graphsage", in_dim=10, fusion="gated", fusion_spans=[6, 5])
        with pytest.raises(ValueError, match="requires fusion_spans"):
            make_model("graphsage", in_dim=10, fusion="gated")
        with pytest.raises(ValueError, match="unknown fusion"):
            make_model("graphsage", in_dim=10, fusion="magic")

    def test_fused_forward_and_attention_delegation(self) -> None:
        model = make_model(
            "gatv2", in_dim=10, fusion="gated", fusion_spans=[6, 4], fusion_dim=12, hidden_dim=8
        )
        x = torch.randn(6, 10)
        edge_index = torch.tensor([[0, 1, 2, 1, 2, 3], [1, 2, 3, 0, 1, 2]])
        direction = torch.tensor([[0.0], [0.0], [0.0], [1.0], [1.0], [1.0]])
        logits = model(x=x, edge_index=edge_index, edge_direction=direction)
        assert logits.shape == (6,)
        assert model.last_attention is not None  # explainer corroboration intact


def tiny_store(tmp_path) -> GraphStore:
    """12 nodes / 2 eras, separable raw features, chain edges — enough for a
    2-epoch wiring run with features [raw, structural]."""
    store = GraphStore(tmp_path / "interim")
    rows, edges = [], []
    # i=0 illicit at t=1 (loss pool), i=2 illicit at t=3 (val pool), i=4 at t=2:
    # both temporal pools carry both classes.
    bad_ids = {0, 2, 4, 8}
    for i in range(12):
        bad = i in bad_ids
        rows.append(
            {
                "node_id": f"acct:n{i}",
                "node_type": "account",
                "domain": "financial",
                "time_first_seen": 1 + (i % 3) if i < 8 else 5,
                "raw_features": RNG.normal(1.0 if bad else -1.0, 0.2, 3)
                .astype(np.float32)
                .tolist(),
                "raw_attrs": None,
            }
        )
    for i in range(11):
        edges.append(
            {
                "src": f"acct:n{i}",
                "dst": f"acct:n{i + 1}",
                "edge_type": "pays",
                "timestamp": 1 + (i % 3) if i < 7 else 5,
                "amount": 10.0,
                "directed": True,
                "raw_attrs": None,
            }
        )
    labels = [
        {
            "node_id": r["node_id"],
            "label": "illicit" if int(r["node_id"][6:]) in bad_ids else "licit",
            "label_source": "toy",
            "confidence": 1.0,
        }
        for r in rows
    ]
    store.write("toycf", "nodes", pl.DataFrame(rows))
    store.write("toycf", "edges", pl.DataFrame(edges))
    store.write("toycf", "labels", pl.DataFrame(labels))
    store.write_meta("toycf", {"dataset": "toycf", "time_unit": "step", "n_features": 3})
    return store


class TestTrainerWiring:
    def test_multi_family_gated_run_end_to_end(self, tmp_path) -> None:
        store = tiny_store(tmp_path)
        record = train_gnn(
            {
                "dataset": "toycf",
                "store_root": str(store.root),
                "output_dir": str(tmp_path / "run"),
                "seed": 0,
                "features": ["raw", "structural"],
                "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
                "model": {
                    "name": "graphsage",
                    "fusion": "gated",
                    "fusion_dim": 8,
                    "hidden_dim": 8,
                    "dropout": 0.0,
                },
                "epochs": 3,
                "patience": 3,
                "budgets": [2],
            }
        )
        assert record["model"]["fusion"] == "gated"
        assert record["features"] == ["raw", "structural"]
        assert len(record["model"]["fusion_spans"]) == 2
        assert record["model"]["fusion_spans"][0] == 3  # raw family width

    def test_family_column_collision_rejected(self, tmp_path) -> None:
        store = tiny_store(tmp_path)
        with pytest.raises(ValueError, match="re-declares columns"):
            train_gnn(
                {
                    "dataset": "toycf",
                    "store_root": str(store.root),
                    "output_dir": str(tmp_path / "run2"),
                    "features": ["structural", "structural"],
                    "split": {"loss_end": 2, "train_end": 3, "test_start": 5},
                    "model": {"name": "graphsage", "hidden_dim": 8},
                    "epochs": 2,
                    "patience": 2,
                    "budgets": [2],
                }
            )
