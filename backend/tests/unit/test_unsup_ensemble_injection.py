"""Week-5 correctness (§7 steps 14–16, §9.1): unsupervised detectors on
planted anomalies, rank-fusion invariants, and structural assertions on every
motif generator — the injector and (future) matcher cross-validate each other,
so the generators' geometry must be exactly right."""

from itertools import pairwise

import numpy as np
import polars as pl
import pytest
from collusiongraph.injection import inject, recovery_at_budget
from collusiongraph.injection.generators.financial import GENERATORS as FIN
from collusiongraph.injection.generators.procurement import GENERATORS as PROC
from collusiongraph.models import (
    rank_fusion,
    rank_percentiles,
    structural_floor,
    unsupervised_scores,
)
from collusiongraph.schema import GraphStore


def anomaly_fixture() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """A quiet chain of 30 nodes; node a7 is a strong attribute outlier."""
    rng = np.random.default_rng(0)
    ids = [f"a{i}" for i in range(30)]
    nodes = pl.DataFrame({"node_id": ids, "time_first_seen": [1] * 30})
    edges = pl.DataFrame(
        {
            "src": ids[:-1],
            "dst": ids[1:],
            "edge_type": ["pays"] * 29,
            "timestamp": [1] * 29,
        }
    )
    x = rng.normal(size=(30, 4))
    x[7] += 8.0
    features = pl.DataFrame({"node_id": ids}).with_columns(
        [pl.Series(f"f{j}", x[:, j]) for j in range(4)]
    )
    return nodes, edges, features


class TestUnsupervisedArm:
    @pytest.mark.parametrize("method", ["dominant", "gae"])
    def test_planted_attribute_outlier_is_top_ranked(self, method: str) -> None:
        nodes, edges, features = anomaly_fixture()
        scores = unsupervised_scores(
            nodes, edges, features, method=method, hid_dim=8, epochs=40, seed=0
        )
        assert scores.sort("score", descending=True)["node_id"][0] == "a7"

    def test_deterministic_under_seed(self) -> None:
        nodes, edges, features = anomaly_fixture()
        a = unsupervised_scores(nodes, edges, features, method="gae", epochs=10, seed=5)
        b = unsupervised_scores(nodes, edges, features, method="gae", epochs=10, seed=5)
        assert a.equals(b)

    def test_unknown_method_rejected(self) -> None:
        nodes, edges, features = anomaly_fixture()
        with pytest.raises(ValueError, match="unknown method"):
            unsupervised_scores(nodes, edges, features, method="isolation_forest")

    def test_structural_floor_ranks_the_hub_first(self) -> None:
        ids = [f"n{i}" for i in range(10)]
        nodes = pl.DataFrame({"node_id": ids, "time_first_seen": [1] * 10})
        edges = pl.DataFrame(
            {
                "src": ["n0"] * 9,
                "dst": ids[1:],
                "edge_type": ["pays"] * 9,
                "timestamp": list(range(1, 10)),
                "directed": [True] * 9,
            }
        )
        floor = structural_floor(nodes, edges)
        assert floor.sort("score", descending=True)["node_id"][0] == "n0"


class TestCalibratedFusion:
    def _val_setup(self):
        """Member 'strong' separates val classes; member 'noise' is random —
        after isotonic calibration on val, noise flattens to ~constant and
        must not outvote strong on test."""
        rng = np.random.default_rng(0)
        n = 200
        ids = [f"v{i}" for i in range(n)]
        y = np.array([1] * 50 + [0] * 150, dtype=np.int8)
        strong_val = pl.DataFrame({"node_id": ids, "score": y * 0.8 + rng.uniform(0, 0.2, size=n)})
        noise_val = pl.DataFrame({"node_id": ids, "score": rng.uniform(size=n)})
        val_labels = pl.DataFrame({"node_id": ids, "y": y})
        return strong_val, noise_val, val_labels

    def test_noise_member_cannot_outvote_calibrated_strong_member(self) -> None:
        from collusiongraph.models.ensemble import calibrated_fusion

        strong_val, noise_val, val_labels = self._val_setup()
        test_ids = ["bad", "ok1", "ok2", "ok3"]
        strong_test = pl.DataFrame({"node_id": test_ids, "score": [0.95, 0.10, 0.15, 0.05]})
        # noise ranks the strong member's worst node first
        noise_test = pl.DataFrame({"node_id": test_ids, "score": [0.1, 0.2, 0.3, 0.9]})
        fused = calibrated_fusion(
            {"strong": strong_test, "noise": noise_test},
            {"strong": strong_val, "noise": noise_val},
            val_labels,
        )
        assert fused["node_id"][0] == "bad"

    def test_missing_validation_scores_rejected(self) -> None:
        from collusiongraph.models.ensemble import calibrated_fusion

        _strong_val, _, val_labels = self._val_setup()
        test = pl.DataFrame({"node_id": ["a"], "score": [0.5]})
        with pytest.raises(ValueError, match="lack validation scores"):
            calibrated_fusion({"m": test}, {}, val_labels)

    def test_calibrated_scores_are_probabilities(self) -> None:
        from collusiongraph.models.ensemble import calibrated_fusion

        strong_val, _noise_val, val_labels = self._val_setup()
        test = pl.DataFrame(
            {"node_id": [f"t{i}" for i in range(5)], "score": [9.0, 5.0, 1.0, -3.0, 0.0]}
        )
        fused = calibrated_fusion({"m": test}, {"m": strong_val}, val_labels)
        assert fused["score"].is_between(0.0, 1.0).all()


class TestRankFusion:
    def test_fusion_hand_computed(self) -> None:
        a = pl.DataFrame({"node_id": ["x", "y", "z"], "score": [3.0, 2.0, 1.0]})
        b = pl.DataFrame({"node_id": ["x", "y", "z"], "score": [10.0, 30.0, 20.0]})
        fused = rank_fusion({"a": a, "b": b}).sort("node_id")
        by_id = dict(fused.iter_rows())
        # rank pcts: a -> x 1.0, y 2/3, z 1/3 ; b -> y 1.0, z 2/3, x 1/3
        assert by_id["x"] == pytest.approx((1.0 + 1 / 3) / 2)
        assert by_id["y"] == pytest.approx((2 / 3 + 1.0) / 2)
        assert by_id["z"] == pytest.approx((1 / 3 + 2 / 3) / 2)

    def test_fusion_invariant_to_monotone_member_transforms(self) -> None:
        """Isotonic calibration is monotone — fusing calibrated scores must
        equal fusing raw scores (§4.4: calibration is for meaning, not order)."""
        rng = np.random.default_rng(1)
        raw = pl.DataFrame({"node_id": [f"n{i}" for i in range(20)], "score": rng.uniform(size=20)})
        squashed = raw.with_columns((pl.col("score") ** 3 * 5 + 1).alias("score"))
        other = pl.DataFrame(
            {"node_id": [f"n{i}" for i in range(20)], "score": rng.uniform(size=20)}
        )
        assert rank_fusion({"m": raw, "o": other}).equals(rank_fusion({"m": squashed, "o": other}))

    def test_missing_member_scores_fuse_over_available(self) -> None:
        a = pl.DataFrame({"node_id": ["x", "y"], "score": [2.0, 1.0]})
        b = pl.DataFrame({"node_id": ["x"], "score": [1.0]})  # never saw y
        fused = dict(rank_fusion({"a": a, "b": b}).iter_rows())
        assert fused["y"] == pytest.approx(0.5)  # a's pct only, not dragged down
        assert fused["x"] == pytest.approx(1.0)

    def test_weights_and_unknown_member_rejection(self) -> None:
        a = pl.DataFrame({"node_id": ["x", "y"], "score": [2.0, 1.0]})
        b = pl.DataFrame({"node_id": ["x", "y"], "score": [1.0, 2.0]})
        fused = dict(rank_fusion({"a": a, "b": b}, weights={"a": 3.0}).iter_rows())
        assert fused["x"] == pytest.approx((3.0 * 1.0 + 0.5) / 4.0)
        with pytest.raises(ValueError, match="unknown members"):
            rank_fusion({"a": a}, weights={"nope": 1.0})

    def test_rank_percentiles_ties_averaged(self) -> None:
        scores = pl.DataFrame({"node_id": ["x", "y", "z"], "score": [1.0, 1.0, 2.0]})
        pcts = dict(rank_percentiles(scores).iter_rows())
        assert pcts["x"] == pcts["y"] == pytest.approx(1.5 / 3)
        assert pcts["z"] == pytest.approx(1.0)


RNG = np.random.default_rng(0)
WINDOW = (10, 20)


class TestFinancialGenerators:
    def test_cycle_is_closed_and_windowed(self) -> None:
        _, edges, members = FIN["cycle"]("t", RNG, *WINDOW, k=5)
        assert edges.height == 5
        assert set(edges["src"]) == set(edges["dst"]) == set(members)
        assert edges["timestamp"].is_between(*WINDOW).all()

    def test_fan_in_is_subthreshold_convergence(self) -> None:
        _, edges, _ = FIN["fan_in"]("t", RNG, *WINDOW, m=8)
        assert edges["dst"].n_unique() == 1  # one target
        assert edges.height == 8
        assert (edges["amount"] < 10_000).all()  # structured deposits

    def test_fan_out_disperses_one_source(self) -> None:
        _, edges, _ = FIN["fan_out"]("t", RNG, *WINDOW, m=6)
        assert edges["src"].n_unique() == 1
        assert edges["dst"].n_unique() == 6

    def test_common_control_clique_complete(self) -> None:
        _, edges, _ = FIN["common_control"]("t", RNG, *WINDOW, k=4)
        linked = edges.filter(pl.col("edge_type") == "linked_to")
        assert linked.height == 6  # C(4,2)
        assert not linked["directed"].any()

    def test_pass_through_has_near_zero_retention_and_short_holds(self) -> None:
        _, edges, _ = FIN["pass_through"]("t", RNG, *WINDOW, k=5)
        amounts = edges.sort("timestamp")["amount"].to_list()
        assert all(b <= a for a, b in pairwise(amounts))
        assert amounts[-1] / amounts[0] > 0.9  # near-zero retention overall
        gaps = edges.sort("timestamp")["timestamp"].diff().drop_nulls()
        assert (gaps == 1).all()  # a hop per tick


class TestProcurementGenerators:
    def test_rotation_rotates_every_firm(self) -> None:
        _, edges, _ = PROC["rotation"]("t", RNG, *WINDOW, n_firms=4)
        awarded = edges.filter(pl.col("edge_type") == "awarded")
        assert awarded["dst"].n_unique() == 4  # everyone gets a turn
        assert awarded.group_by("dst").len()["len"].to_list() == [2, 2, 2, 2]

    def test_cover_bids_sit_tightly_above_the_winner(self) -> None:
        _, edges, _ = PROC["cover_bid"]("t", RNG, *WINDOW, k_covers=4)
        bids = edges.filter(pl.col("edge_type") == "bids_on").sort("amount")
        w = bids["amount"][0]
        covers = bids["amount"][1:]
        assert ((covers > w) & (covers <= w * 1.05)).all()
        winner = edges.filter(pl.col("edge_type") == "awarded")["dst"][0]
        assert bids["src"][0] == winner  # lowest bid wins

    def test_partition_never_crosses_the_line(self) -> None:
        _, edges, _ = PROC["partition"]("t", RNG, *WINDOW, n_per_side=2)
        buys = edges.filter(pl.col("edge_type") == "buys_from").rename({"src": "buyer"})
        awards = edges.filter(pl.col("edge_type") == "awarded").rename({"dst": "firm"})
        joined = awards.join(buys, left_on="src", right_on="dst")
        pairs = joined.select("buyer", "firm").unique()
        # each firm serves exactly one buyer: perfect market allocation
        assert pairs.group_by("firm").len()["len"].max() == 1

    def test_common_control_links_rival_winners(self) -> None:
        _, edges, _ = PROC["common_control"]("t", RNG, *WINDOW, k=3)
        assert edges.filter(pl.col("edge_type") == "linked_to").height == 3  # C(3,2)
        assert edges.filter(pl.col("edge_type") == "awarded")["dst"].n_unique() == 3

    def test_coordinated_cluster_prices_are_clustered(self) -> None:
        _, edges, _ = PROC["coordinated_cluster"]("t", RNG, *WINDOW, k=4)
        bids = edges.filter(pl.col("edge_type") == "bids_on")
        per_tender_cv = bids.group_by("dst").agg(
            (pl.col("amount").std() / pl.col("amount").mean()).alias("cv")
        )["cv"]
        assert (per_tender_cv < 0.05).all()


class TestInjector:
    def background(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        ids = [f"bg{i}" for i in range(20)]
        nodes = pl.DataFrame(
            {
                "node_id": ids,
                "node_type": ["account"] * 20,
                "domain": ["financial"] * 20,
                "time_first_seen": [10] * 20,
                "raw_features": pl.Series([None] * 20, dtype=pl.List(pl.Float32)),
                "raw_attrs": pl.Series([None] * 20, dtype=pl.Utf8),
            }
        )
        edges = pl.DataFrame(
            {
                "src": ids[:-1],
                "dst": ids[1:],
                "edge_type": ["pays"] * 19,
                "timestamp": [12] * 19,
                "amount": [100.0] * 19,
                "directed": [True] * 19,
                "raw_attrs": pl.Series([None] * 19, dtype=pl.Utf8),
            }
        )
        return nodes, edges

    def test_background_preserved_and_ground_truth_complete(self, tmp_path) -> None:
        nodes, edges = self.background()
        result = inject(
            nodes, edges, "financial", {"cycle": 2, "fan_in": 1}, window=(10, 20), seed=0
        )
        assert result.ground_truth.height == 3
        assert result.nodes.head(20).equals(nodes)  # background rows untouched
        injected_ids = set(
            result.ground_truth["member_node_ids"].explode(empty_as_null=False).to_list()
        )
        assert injected_ids <= set(result.nodes["node_id"].to_list())
        # augmented frames still pass the IR schema gate
        store = GraphStore(tmp_path)
        store.write("aug", "nodes", result.nodes)
        store.write("aug", "edges", result.edges)

    def test_unlabeled_injection_recovery_end_to_end(self, tmp_path) -> None:
        """§7 step 30: the unlabeled regime (OCDS shape) runs without labels or
        a supervised member — structural-template features, rank-only fusion,
        and the report names the regime (fusion_mode: rank_unlabeled)."""
        from collusiongraph.training import run_injection_recovery

        rng = np.random.default_rng(0)
        firms = [f"firm:bg:{i}" for i in range(12)]
        tenders = [f"tender:bg:{i}" for i in range(18)]
        nodes = pl.DataFrame(
            {
                "node_id": firms + tenders,
                "node_type": ["firm"] * 12 + ["tender"] * 18,
                "domain": ["procurement"] * 30,
                "time_first_seen": [2020] * 30,
                "raw_features": pl.Series([None] * 30, dtype=pl.List(pl.Float32)),
                "raw_attrs": pl.Series([None] * 30, dtype=pl.Utf8),
            }
        )
        edges = pl.DataFrame(
            {
                "src": [firms[int(rng.integers(12))] for _ in range(40)],
                "dst": [tenders[int(rng.integers(18))] for _ in range(40)],
                "edge_type": ["bids_on"] * 40,
                "timestamp": [int(rng.integers(2020, 2025)) for _ in range(40)],
                "amount": [float(rng.uniform(1e3, 1e5)) for _ in range(40)],
                "directed": [True] * 40,
                "raw_attrs": pl.Series([None] * 40, dtype=pl.Utf8),
            }
        )
        labels = pl.DataFrame(
            {
                "node_id": firms + tenders,
                "label": ["unknown"] * 30,
                "label_source": ["ocds_unlabeled"] * 30,
                "confidence": pl.Series([1.0] * 30, dtype=pl.Float32),
            }
        )
        store = GraphStore(tmp_path)
        store.write("toy_ocds", "nodes", nodes)
        store.write("toy_ocds", "edges", edges)
        store.write("toy_ocds", "labels", labels)
        store.write_meta("toy_ocds", {"dataset": "toy_ocds"})  # no n_features key

        report = run_injection_recovery(
            {
                "dataset": "toy_ocds",
                "domain": "procurement",
                "store_root": str(tmp_path),
                "output_dir": str(tmp_path / "out"),
                "seed": 0,
                "split": {"test_start": 2020, "window_end": 2024},
                "motifs": {"cover_bid": 1},
                "n_bridge_edges": 1,
                "unsupervised": {
                    "edge_type": "bids_on",
                    "features": "structural",
                    "hid_dim": 8,
                    "epochs": 5,
                },
                "budgets": [10],
            }
        )
        assert report["fusion_mode"] == "rank_unlabeled"
        assert set(report["recovery"]) == {"dominant", "gae", "floor", "ensemble_rank"}
        rec = report["recovery"]["ensemble_rank"][0]
        assert rec["motif_type"] == "cover_bid"
        assert 0.0 <= rec["recall@10"] <= 1.0

    def test_unknown_unsupervised_feature_kind_rejected(self, tmp_path) -> None:
        from collusiongraph.training.ensemble_run import _member_scores

        nodes = pl.DataFrame({"node_id": ["a", "b"], "raw_features": [None, None]})
        edges = pl.DataFrame(
            {"src": ["a"], "dst": ["b"], "edge_type": ["bids_on"], "timestamp": [1]}
        )
        with pytest.raises(ValueError, match=r"unknown unsupervised\.features"):
            unsup = {"edge_type": "bids_on", "features": "pca"}
            _member_scores(nodes, edges, 0, {"unsupervised": unsup})

    def test_multi_family_injection_ids_are_disjoint(self) -> None:
        """Regression (2026-07-20): procurement families reused market strings,
        so rotation/common_control/coordinated_cluster instances with the same
        tag overwrote each other's members. All ids must be unique across the
        whole multi-family injection."""
        ids = [f"tender:bg:{i}" for i in range(5)]
        nodes = pl.DataFrame(
            {
                "node_id": ids,
                "node_type": ["tender"] * 5,
                "domain": ["procurement"] * 5,
                "time_first_seen": [10] * 5,
                "raw_features": pl.Series([None] * 5, dtype=pl.List(pl.Float32)),
                "raw_attrs": pl.Series([None] * 5, dtype=pl.Utf8),
            }
        )
        edges = pl.DataFrame(
            {
                "src": ids[:-1],
                "dst": ids[1:],
                "edge_type": ["bids_on"] * 4,
                "timestamp": [10] * 4,
                "amount": pl.Series([None] * 4, dtype=pl.Float64),
                "directed": [True] * 4,
                "raw_attrs": pl.Series([None] * 4, dtype=pl.Utf8),
            }
        )
        result = inject(
            nodes,
            edges,
            "procurement",
            {m: 2 for m in PROC},
            window=(10, 20),
            seed=0,
        )
        injected = result.nodes["node_id"].to_list()[5:]
        assert len(injected) == len(set(injected))
        members = result.ground_truth["member_node_ids"].explode(empty_as_null=False)
        per_instance = result.ground_truth.select(pl.col("member_node_ids").list.len().alias("n"))[
            "n"
        ].sum()
        assert members.n_unique() == per_instance  # no member shared across instances

    def test_colliding_generator_ids_are_refused(self, monkeypatch) -> None:
        """The injector guard: a generator emitting an id that already exists
        must raise, never silently corrupt ground truth."""
        import collusiongraph.injection.injector as injector_mod

        def clashing(tag, rng, t0, t1):
            ids = ["firm:clash:F0"]
            nodes = pl.DataFrame(
                {
                    "node_id": ids,
                    "node_type": ["firm"],
                    "domain": ["procurement"],
                    "time_first_seen": [t0],
                }
            )
            edges = pl.DataFrame(
                {
                    "src": ids,
                    "dst": ids,
                    "edge_type": ["bids_on"],
                    "timestamp": [t0],
                    "directed": [True],
                }
            )
            return nodes, edges, ids

        monkeypatch.setitem(injector_mod.GENERATORS, "procurement", {"clasher": clashing})
        nodes = pl.DataFrame(
            {
                "node_id": ["tender:bg:0"],
                "node_type": ["tender"],
                "domain": ["procurement"],
                "time_first_seen": [10],
            }
        )
        edges = pl.DataFrame(
            {
                "src": ["tender:bg:0"],
                "dst": ["tender:bg:0"],
                "edge_type": ["bids_on"],
                "timestamp": [10],
                "directed": [True],
            }
        )
        with pytest.raises(ValueError, match="already exist"):
            inject(nodes, edges, "procurement", {"clasher": 2}, window=(10, 20), seed=0)

    def test_deterministic_under_seed(self) -> None:
        nodes, edges = self.background()
        a = inject(nodes, edges, "financial", {"fan_out": 2}, window=(10, 20), seed=3)
        b = inject(nodes, edges, "financial", {"fan_out": 2}, window=(10, 20), seed=3)
        assert a.nodes.equals(b.nodes) and a.edges.equals(b.edges)

    def test_unknown_motif_and_domain_rejected(self) -> None:
        nodes, edges = self.background()
        with pytest.raises(ValueError, match="unknown motifs"):
            inject(nodes, edges, "financial", {"rotation": 1}, window=(10, 20))
        with pytest.raises(ValueError, match="unknown domain"):
            inject(nodes, edges, "energy", {"cycle": 1}, window=(10, 20))

    def test_recovery_at_budget_hand_computed(self) -> None:
        gt = pl.DataFrame(
            {
                "instance_id": ["fan_in:0"],
                "motif_type": ["fan_in"],
                "member_node_ids": [["m1", "m2", "m3", "m4"]],
                "n_edges": [3],
            }
        )
        scores = pl.DataFrame(
            {
                "node_id": ["m1", "bg1", "m2", "bg2", "m3", "m4"],
                "score": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
            }
        )
        rec = recovery_at_budget(scores, gt, budgets=[2, 6])
        assert rec["recall@2"][0] == pytest.approx(1 / 4)
        assert rec["recall@6"][0] == pytest.approx(1.0)

    def test_floor_recovers_planted_fan_in_on_quiet_background(self) -> None:
        """§9.1 injection-recovery: on a quiet chain background the structural
        floor must put the fan-in hub inside a tight budget."""
        nodes, edges = self.background()
        result = inject(
            nodes, edges, "financial", {"fan_in": 1}, window=(10, 20), seed=1, n_bridge_edges=0
        )
        floor = structural_floor(result.nodes, result.edges)
        target = next(n for n in result.ground_truth["member_node_ids"][0] if "target" in n)
        top3 = floor.sort("score", descending=True).head(3)["node_id"].to_list()
        assert target in top3
