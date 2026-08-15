"""GNN core correctness (§7 steps 11–13, §9.1 model sanity suite): losses,
graph materialization, the three models (shapes / overfit-single-batch / seed
determinism), Leiden roll-up, isotonic calibration, alert construction."""

import math

import numpy as np
import polars as pl
import pytest
import torch
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.artifacts import build_alerts
from collusiongraph.models import (
    community_scores,
    isotonic_calibrator,
    leiden_communities,
    make_model,
)
from collusiongraph.schema import GraphStore
from collusiongraph.training import build_graph, confirmed_mask_for, focal_loss, make_loss
from collusiongraph.training.losses import weighted_ce_loss


class TestLosses:
    def test_focal_gamma_zero_is_cross_entropy(self) -> None:
        logits = torch.tensor([0.5, -1.0, 2.0])
        targets = torch.tensor([1, 0, 1])
        ce = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets.float())
        assert torch.isclose(focal_loss(logits, targets, gamma=0.0), ce)

    def test_focal_downweights_easy_examples(self) -> None:
        easy = torch.tensor([4.0])  # confidently correct positive
        hard = torch.tensor([-1.0])  # confidently wrong positive
        target = torch.tensor([1])
        ratio_easy = focal_loss(easy, target, gamma=2.0) / focal_loss(easy, target, gamma=0.0)
        ratio_hard = focal_loss(hard, target, gamma=2.0) / focal_loss(hard, target, gamma=0.0)
        assert ratio_easy < ratio_hard < 1.0

    def test_weighted_ce_upweights_minority(self) -> None:
        logits = torch.zeros(4)
        targets = torch.tensor([1, 0, 0, 0])
        plain = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets.float())
        assert weighted_ce_loss(logits, targets) > plain

    def test_unknown_loss_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown loss"):
            make_loss("hinge")


def ir_fixture() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    nodes = pl.DataFrame({"node_id": ["a", "b", "c", "d"], "time_first_seen": [1, 1, 2, 3]})
    edges = pl.DataFrame(
        {
            "src": ["a", "b", "c"],
            "dst": ["b", "c", "d"],
            "edge_type": ["pays", "pays", "linked_to"],
            "timestamp": [1, 2, 3],
        }
    )
    labels = pl.DataFrame({"node_id": ["a", "b", "c"], "label": ["illicit", "licit", "unknown"]})
    features = pl.DataFrame(
        {"node_id": ["a", "b", "c", "d"], "f0": [1.0, 2.0, None, 4.0], "f1": [0.1] * 4}
    )
    return nodes, edges, labels, features


class TestGraphBuild:
    def test_edges_doubled_with_direction_flags_and_relations(self) -> None:
        nodes, edges, labels, features = ir_fixture()
        data = build_graph(nodes, edges, labels, features)
        assert data.edge_index.shape == (2, 6)
        assert data.edge_direction[:3].sum() == 0 and data.edge_direction[3:].sum() == 3
        # reverse of edge k is edge k+3 with endpoints swapped
        assert torch.equal(data.edge_index[:, 3:], data.edge_index[:, :3].flip(0))
        # relations: linked_to fwd id != pays fwd id; reverse ids offset by n_types
        assert data.num_relations == 4
        assert data.edge_rel[2] != data.edge_rel[0]
        assert data.edge_rel[3] == data.edge_rel[0] + 2

    def test_labels_and_features_align(self) -> None:
        nodes, edges, labels, features = ir_fixture()
        data = build_graph(nodes, edges, labels, features)
        assert data.y.tolist() == [1, 0, -1, -1]  # illicit / licit / unknown / unlabeled
        assert data.x.shape == (4, 2)
        assert data.x[2, 0] == 0.0  # null feature -> 0.0 for message passing

    def test_unidirectional_ablation_arm(self) -> None:  # §7 step 32 (−bidirectional)
        nodes, edges, labels, features = ir_fixture()
        data = build_graph(nodes, edges, labels, features, bidirectional=False)
        # only the original src→dst edges, all direction 0, forward relations only
        assert data.edge_index.shape == (2, 3)
        assert data.edge_direction.sum() == 0
        assert data.num_relations == 2  # pays + linked_to, no reverse ids
        both = build_graph(nodes, edges, labels, features)
        assert torch.equal(data.edge_index, both.edge_index[:, :3])
        assert torch.equal(data.edge_rel, both.edge_rel[:3])

    def test_confirmed_mask_respects_pool_and_prefix(self) -> None:
        nodes, edges, labels, features = ir_fixture()
        data = build_graph(nodes, edges, labels, features)
        mask = confirmed_mask_for(data, {"a", "b", "c", "d"})
        assert mask.tolist() == [True, True, False, False]  # unknowns never in a loss pool
        assert confirmed_mask_for(data, {"b"}).tolist() == [False, True, False, False]


def toy_training_graph(n_per_class: int = 20, seed: int = 0):
    """Two feature-separable classes with intra-class edges — every model must
    drive training loss to ~0 on it (§9.1 overfit-single-batch)."""
    rng = np.random.default_rng(seed)
    n = 2 * n_per_class
    x = np.vstack(
        [
            rng.normal(loc=+1.0, scale=0.3, size=(n_per_class, 4)),
            rng.normal(loc=-1.0, scale=0.3, size=(n_per_class, 4)),
        ]
    ).astype(np.float32)
    y = torch.tensor([1] * n_per_class + [0] * n_per_class)
    src = torch.arange(0, n - 1)
    dst = src + 1
    edge_index = torch.stack([torch.cat([src, dst]), torch.cat([dst, src])])
    direction = torch.cat([torch.zeros(n - 1), torch.ones(n - 1)]).unsqueeze(1)
    rel = torch.cat([torch.zeros(n - 1, dtype=torch.long), torch.ones(n - 1, dtype=torch.long)])
    return torch.from_numpy(x), edge_index, direction, rel, y


@pytest.mark.parametrize("name", ["graphsage", "gatv2", "rgcn"])
class TestModelSanity:
    def _make(self, name: str):
        kwargs = {"hidden_dim": 16, "num_layers": 2, "dropout": 0.0}
        if name == "gatv2":
            kwargs["heads"] = 2
        return make_model(name, in_dim=4, num_relations=2, **kwargs)

    def test_output_shape_and_dtype(self, name: str) -> None:
        torch.manual_seed(0)
        x, ei, direction, rel, _ = toy_training_graph()
        logits = self._make(name)(x=x, edge_index=ei, edge_direction=direction, edge_rel=rel)
        assert logits.shape == (x.shape[0],)
        assert logits.dtype == torch.float32

    def test_overfits_single_batch(self, name: str) -> None:
        torch.manual_seed(0)
        x, ei, direction, rel, y = toy_training_graph()
        model = self._make(name)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.05)
        loss = torch.tensor(float("inf"))
        for _ in range(150):
            optimizer.zero_grad()
            logits = model(x=x, edge_index=ei, edge_direction=direction, edge_rel=rel)
            loss = focal_loss(logits, y, gamma=0.0)
            loss.backward()
            optimizer.step()
        assert loss.item() < 0.05, f"{name} failed to overfit: loss={loss.item():.3f}"

    def test_seed_determinism(self, name: str) -> None:
        x, ei, direction, rel, _ = toy_training_graph()

        def run() -> torch.Tensor:
            torch.manual_seed(7)
            model = self._make(name)
            model.eval()
            with torch.no_grad():
                return model(x=x, edge_index=ei, edge_direction=direction, edge_rel=rel)

        assert torch.equal(run(), run())


class TestGATv2Attention:
    def test_last_layer_attention_is_captured(self) -> None:
        torch.manual_seed(0)
        x, ei, direction, rel, _ = toy_training_graph()
        model = make_model("gatv2", in_dim=4, hidden_dim=8, heads=2, dropout=0.0)
        model(x=x, edge_index=ei, edge_direction=direction, edge_rel=rel)
        assert model.last_attention is not None
        _, att = model.last_attention
        assert att.shape[1] == 2  # one coefficient per head


def two_clique_graph() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Two 4-cliques joined by a single bridge edge — Leiden must find both."""
    ids = [f"n{i}" for i in range(8)]
    nodes = pl.DataFrame({"node_id": ids, "time_first_seen": [1] * 8})
    pairs = [(a, b) for grp in (ids[:4], ids[4:]) for a in grp for b in grp if a < b]
    pairs.append(("n0", "n4"))
    edges = pl.DataFrame(
        {
            "src": [p[0] for p in pairs],
            "dst": [p[1] for p in pairs],
            "edge_type": ["pays"] * len(pairs),
            "timestamp": [1] * len(pairs),
        }
    )
    return nodes, edges


class TestRollup:
    def test_leiden_finds_planted_cliques_deterministically(self) -> None:
        nodes, edges = two_clique_graph()
        communities = leiden_communities(nodes, edges, seed=0)
        member_sets = {frozenset(m) for m in communities["member_node_ids"].to_list()}
        assert member_sets == {
            frozenset({"n0", "n1", "n2", "n3"}),
            frozenset({"n4", "n5", "n6", "n7"}),
        }
        assert communities.equals(leiden_communities(nodes, edges, seed=0))

    def test_community_score_hand_computed(self) -> None:
        communities = pl.DataFrame(
            {
                "community_id": ["k"],
                "member_node_ids": [["a", "b", "c", "d"]],
                "method": ["fixture"],
            }
        )
        scores = pl.DataFrame({"node_id": ["a", "b", "c", "d"], "score": [0.9, 0.5, 0.3, 0.1]})
        out = community_scores(communities, scores, top_p=0.5)
        # top ceil(0.5*4)=2 mean = 0.7; max = 0.9 -> (0.9+0.7)/2
        assert out["score"][0] == pytest.approx(0.8)

    def test_isotonic_calibration_preserves_ordering(self) -> None:
        """§9.1 calibration monotonicity: higher raw score -> calibrated score
        never lower."""
        rng = np.random.default_rng(0)
        raw = rng.uniform(size=200)
        y = (rng.uniform(size=200) < raw).astype(int)  # noisy but monotone truth
        calibrator = isotonic_calibrator(raw, y)
        grid = np.linspace(0, 1, 50)
        out = calibrator.predict(grid)
        assert (np.diff(out) >= -1e-12).all()
        assert out.min() >= 0.0 and out.max() <= 1.0


class TestBuildAlerts:
    def test_alerts_conform_and_carry_the_caveat(self, tmp_path) -> None:
        nodes, _ = two_clique_graph()
        scored = pl.DataFrame(
            {
                "community_id": ["leiden:0", "leiden:1"],
                "member_node_ids": [["n0", "n1"], ["n4", "n5", "n6"]],
                "method": ["leiden"] * 2,
                "score": [0.4, 0.9],
            }
        )
        alerts = build_alerts(scored, nodes, "toy", "financial", "run0")
        assert alerts["rank"].to_list() == [1, 2]
        assert alerts["risk_score"].to_list() == [0.9, 0.4]  # rank 1 = highest score
        assert alerts["n_members"].to_list() == [3, 2]
        assert (alerts["caveats"] == SCREENING_CAVEAT).all()
        # schema gate: a malformed frame would raise inside GraphStore.write
        store = GraphStore(tmp_path)
        store.write("toy", "alerts", alerts)
        assert not math.isnan(store.read("toy", "alerts")["risk_score"][0])
