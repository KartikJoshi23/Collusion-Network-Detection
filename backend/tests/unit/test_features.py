"""Feature-template and domain-pack correctness (§4.2 rule 2, §4.4, §9.1).

Every value asserted here is hand-computed on a fixture small enough to check
on paper — the metric-test discipline of §9.1 applied to features.
"""

import json
import math

import polars as pl
import pytest
from collusiongraph.features import (
    award_screens,
    bid_screens,
    co_bid_stats,
    financial_features,
    precomputed_screens,
    sinusoidal_time_encoding,
    structural_features,
    zscore_per_graph,
)
from collusiongraph.schema import GraphStore


def structural_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    """a-b-c form a triangle (a<->b mutual); c->d dangles; e is isolated."""
    nodes = pl.DataFrame(
        {
            "node_id": ["a", "b", "c", "d", "e"],
            "time_first_seen": [1, 1, 2, 4, 1],
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["a", "b", "a", "b", "c"],
            "dst": ["b", "a", "c", "c", "d"],
            "timestamp": [1, 2, 2, 3, 4],
            "edge_type": ["pays"] * 5,
            "directed": [True] * 5,
        }
    )
    return nodes, edges


class TestStructuralTemplate:
    def test_degrees_count_multi_edges_and_directions(self) -> None:
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges).sort("node_id")
        assert feats["degree_in"].to_list() == [1, 1, 2, 1, 0]
        assert feats["degree_out"].to_list() == [2, 2, 1, 0, 0]
        assert feats["degree_total"].to_list() == [3, 3, 3, 1, 0]

    def test_motif_participation(self) -> None:
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges).sort("node_id")
        assert feats["triangles"].to_list() == [1, 1, 1, 0, 0]
        assert feats["mutual_degree"].to_list() == [1, 1, 0, 0, 0]  # only a<->b

    def test_clustering_and_kcore(self) -> None:
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges).sort("node_id")
        # c's neighbors {a, b, d}: one of three possible links exists
        assert feats["clustering"].to_list() == pytest.approx([1.0, 1.0, 1 / 3, 0.0, 0.0])
        assert feats["kcore"].to_list() == [2, 2, 2, 1, 0]

    def test_community_relative_stats_default_to_components(self) -> None:
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges).sort("node_id")
        assert feats["community_size"].to_list() == [4, 4, 4, 4, 1]
        # component mean degree_total = (3+3+3+1)/4 = 2.5; isolated e pins to 1.0
        assert feats["degree_rel_community"].to_list() == pytest.approx([1.2, 1.2, 1.2, 0.4, 1.0])

    def test_explicit_communities_override_components(self) -> None:
        nodes, edges = structural_fixture()
        communities = pl.DataFrame(
            {
                "community_id": ["k1", "k2"],
                "member_node_ids": [["a", "b"], ["c", "d", "e"]],
                "method": ["fixture", "fixture"],
            }
        )
        feats = structural_features(nodes, edges, communities=communities).sort("node_id")
        assert feats["community_size"].to_list() == [2, 2, 3, 3, 3]

    def test_simultaneous_events_give_null_burstiness_not_nan(self) -> None:
        """All gaps zero -> sigma+mu = 0 -> burstiness undefined (null), never
        0/0 = NaN, which would poison per-graph z-scoring downstream."""
        nodes = pl.DataFrame({"node_id": ["hub", "x", "y"], "time_first_seen": [1, 1, 1]})
        edges = pl.DataFrame(
            {
                "src": ["hub", "hub"],
                "dst": ["x", "y"],
                "timestamp": [5, 5],  # simultaneous
                "edge_type": ["pays"] * 2,
                "directed": [True] * 2,
            }
        )
        feats = structural_features(nodes, edges).sort("node_id")
        hub = feats.filter(pl.col("node_id") == "hub")
        assert hub["burstiness"][0] is None
        assert not feats["burstiness"].is_nan().any()

    def test_burstiness_hand_computed(self) -> None:
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges).sort("node_id")
        # a's events: t=1, 2, 2 -> gaps [1, 0]: mu=.5, sigma=std([1,0])=sqrt(.5)
        sigma, mu = math.sqrt(0.5), 0.5
        assert feats["burstiness"][0] == pytest.approx((sigma - mu) / (sigma + mu))
        assert feats["burstiness"][4] is None  # e: no events

    def test_empty_as_of_graph_keeps_schema(self) -> None:
        """An as-of before anything exists yields an empty frame with intact
        dtypes — downstream joins must not meet a Null-typed node_id."""
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges, as_of=0)
        assert feats.is_empty()
        assert feats.schema["node_id"] == pl.Utf8

    def test_zscore_per_graph(self) -> None:
        df = pl.DataFrame({"node_id": ["a", "b"], "x": [0.0, 10.0], "const": [7.0, 7.0]})
        z = zscore_per_graph(df)
        assert z["x"].to_list() == pytest.approx([-math.sqrt(0.5), math.sqrt(0.5)])
        assert z["const"].to_list() == [0.0, 0.0]  # zero variance -> no information
        assert z["node_id"].to_list() == ["a", "b"]

    def test_zscore_fills_nulls_with_graph_mean(self) -> None:
        df = pl.DataFrame({"node_id": ["a", "b", "c"], "x": [0.0, 10.0, None]})
        assert zscore_per_graph(df)["x"][2] == 0.0
        assert zscore_per_graph(df, fill_null=False)["x"][2] is None


def financial_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    nodes = pl.DataFrame({"node_id": ["x", "y", "z"], "time_first_seen": [10, 10, 13]})
    edges = pl.DataFrame(
        {
            "src": ["x", "x", "y", "y"],
            "dst": ["y", "y", "z", "z"],
            "timestamp": [10, 12, 13, 20],
            "amount": [100.0, 50.0, 150.0, 100.0],
            "edge_type": ["pays"] * 4,
            "directed": [True] * 4,
        }
    )
    return nodes, edges


class TestFinancialPack:
    def test_retention_ratio(self) -> None:
        nodes, edges = financial_fixture()
        feats = financial_features(nodes, edges).sort("node_id")
        # x: pure source -> -1; y: in 150 out 250 -> -0.25; z: pure sink -> +1
        assert feats["retention_ratio"].to_list() == pytest.approx([-1.0, -0.25, 1.0])

    def test_counts_and_velocity(self) -> None:
        nodes, edges = financial_fixture()
        feats = financial_features(nodes, edges).sort("node_id")
        assert feats["in_count"].to_list() == [0, 2, 2]
        assert feats["out_count"].to_list() == [2, 2, 0]
        # y: 4 events over span 20-10 -> 4/11
        assert feats["velocity"][1] == pytest.approx(4 / 11)

    def test_holding_time_asof_matching(self) -> None:
        nodes, edges = financial_fixture()
        feats = financial_features(nodes, edges).sort("node_id")
        # y's outflows at 13 and 20 both match its latest inflow at 12 -> gaps 1, 8
        assert feats["holding_time_median"][1] == pytest.approx(4.5)
        assert feats["holding_time_median"][0] is None  # x never receives

    def test_round_amount_share(self) -> None:
        nodes, edges = financial_fixture()
        feats = financial_features(nodes, edges).sort("node_id")
        # y's inflows: 100 (round), 50 (not) -> 0.5; z's: 150, 100 -> hand check
        assert feats["in_round_amount_share"][1] == pytest.approx(0.5)
        assert feats["in_round_amount_share"][2] == pytest.approx(0.5)

    def test_amountless_dataset_yields_null_not_zero_or_nan(self) -> None:
        """Elliptic++ carries no amounts (§4.3 D1): amount-derived features must
        be null (unknown), never 0.0 or NaN — NaN would poison z-scoring."""
        nodes, edges = financial_fixture()
        no_amounts = edges.with_columns(pl.lit(None, dtype=pl.Float64).alias("amount"))
        feats = financial_features(nodes, no_amounts)
        for col in ("in_amount_sum", "retention_ratio", "in_round_amount_share"):
            assert feats[col].null_count() == feats.height, col
            assert not feats[col].is_nan().any(), col
        # time-derived features survive without amounts
        assert feats["velocity"].null_count() == 0
        assert feats["holding_time_median"][1] is not None

    def test_non_pays_edges_are_ignored(self) -> None:
        nodes, edges = financial_fixture()
        linked = pl.DataFrame(
            {
                "src": ["x"],
                "dst": ["z"],
                "timestamp": [11],
                "amount": [9999.0],
                "edge_type": ["linked_to"],
                "directed": [True],
            }
        )
        with_link = pl.concat([edges, linked])
        assert financial_features(nodes, with_link).equals(financial_features(nodes, edges))

    def test_sinusoidal_encoding_shape_and_range(self) -> None:
        enc = sinusoidal_time_encoding(pl.Series([0, 1, 100]), n_frequencies=3)
        assert enc.shape == (3, 6)
        assert enc.select(pl.all().abs().max()).max_horizontal().max() <= 1.0


def award_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Market M: B1 awards T1,T2,T4->F1 and T3->F2; F3 wins T6 from an unknown
    buyer. Market N: B2 awards T5->G1 (single-winner buyer)."""
    nodes = pl.DataFrame(
        {
            "node_id": [
                "firm:M:F1",
                "firm:M:F2",
                "firm:M:F3",
                "firm:N:G1",
                "buyer:M:B1",
                "buyer:N:B2",
                "tender:M:T1",
                "tender:M:T2",
                "tender:M:T3",
                "tender:M:T4",
                "tender:M:T6",
                "tender:N:T5",
            ],
            "time_first_seen": [2010] * 12,
        }
    )
    awarded = pl.DataFrame(
        {
            "src": [
                "tender:M:T1",
                "tender:M:T2",
                "tender:M:T3",
                "tender:M:T4",
                "tender:M:T6",
                "tender:N:T5",
            ],
            "dst": ["firm:M:F1", "firm:M:F1", "firm:M:F2", "firm:M:F1", "firm:M:F3", "firm:N:G1"],
            "edge_type": ["awarded"] * 6,
            "timestamp": [2010, 2011, 2012, 2013, 2013, 2011],
            "amount": pl.Series([None] * 6, dtype=pl.Float64),
            "directed": [True] * 6,
        }
    )
    buys = pl.DataFrame(
        {
            "src": ["buyer:M:B1"] * 4 + ["buyer:N:B2"],
            "dst": ["tender:M:T1", "tender:M:T2", "tender:M:T3", "tender:M:T4", "tender:N:T5"],
            "edge_type": ["buys_from"] * 5,
            "timestamp": [2010, 2011, 2012, 2013, 2011],
            "directed": [True] * 5,
        }
    )
    return nodes, pl.concat([awarded, buys], how="diagonal")


class TestAwardScreens:
    def test_market_share_is_within_market(self) -> None:
        nodes, edges = award_fixture()
        feats = award_screens(nodes, edges)
        by_id = {r["node_id"]: r for r in feats.iter_rows(named=True)}
        assert by_id["firm:M:F1"]["n_awards"] == 3
        assert by_id["firm:M:F1"]["market_share"] == pytest.approx(3 / 5)
        assert by_id["firm:N:G1"]["market_share"] == pytest.approx(1.0)  # N normalizes alone

    def test_buyer_concentration_hhi(self) -> None:
        nodes, edges = award_fixture()
        by_id = {r["node_id"]: r for r in award_screens(nodes, edges).iter_rows(named=True)}
        assert by_id["firm:M:F1"]["buyer_hhi"] == pytest.approx(1.0)  # single buyer
        assert by_id["firm:M:F3"]["buyer_hhi"] is None  # buyer unknown (Mendeley nulls)

    def test_supplier_hhi_and_rotation_entropy(self) -> None:
        nodes, edges = award_fixture()
        by_id = {r["node_id"]: r for r in award_screens(nodes, edges).iter_rows(named=True)}
        b1 = by_id["buyer:M:B1"]
        # B1's winner shares: F1 3/4, F2 1/4
        assert b1["supplier_hhi"] == pytest.approx(0.75**2 + 0.25**2)
        expected_entropy = -(0.75 * math.log(0.75) + 0.25 * math.log(0.25)) / math.log(2)
        assert b1["winner_rotation_entropy"] == pytest.approx(expected_entropy)
        assert b1["n_distinct_winners"] == 2
        # a single-winner buyer has no rotation to measure — null, not zero
        assert by_id["buyer:N:B2"]["winner_rotation_entropy"] is None


def bid_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    nodes = pl.DataFrame(
        {
            "node_id": [
                "firm:M:F1",
                "firm:M:F2",
                "firm:M:F3",
                "tender:M:T1",
                "tender:M:T2",
            ],
            "time_first_seen": [2010] * 5,
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["firm:M:F1", "firm:M:F2", "firm:M:F3", "firm:M:F1", "firm:M:F2"],
            "dst": ["tender:M:T1"] * 3 + ["tender:M:T2"] * 2,
            "edge_type": ["bids_on"] * 5,
            "timestamp": [2010] * 5,
            "amount": [100.0, 110.0, 130.0, 200.0, 220.0],
            "directed": [True] * 5,
        }
    )
    return nodes, edges


class TestBidScreens:
    def test_screens_hand_computed(self) -> None:
        nodes, edges = bid_fixture()
        by_id = {r["node_id"]: r for r in bid_screens(nodes, edges).iter_rows(named=True)}
        t1 = by_id["tender:M:T1"]
        amounts = [100.0, 110.0, 130.0]
        mean = sum(amounts) / 3
        std = math.sqrt(sum((a - mean) ** 2 for a in amounts) / 2)
        assert t1["n_bids"] == 3
        assert t1["bid_cv"] == pytest.approx(std / mean)
        assert t1["bid_spread"] == pytest.approx(30 / 100)
        assert t1["diffp"] == pytest.approx(10 / 100)
        losing_std = math.sqrt(((110 - 120) ** 2 + (130 - 120) ** 2) / 1)
        assert t1["rd"] == pytest.approx(10 / losing_std)

    def test_below_quorum_screens_are_null_not_fabricated(self) -> None:
        nodes, edges = bid_fixture()
        by_id = {r["node_id"]: r for r in bid_screens(nodes, edges).iter_rows(named=True)}
        t2 = by_id["tender:M:T2"]  # two bids: cv/spread/diffp defined, rd/skew/kurt not
        assert t2["diffp"] == pytest.approx(20 / 200)
        assert t2["rd"] is None
        assert t2["bid_skew"] is None
        assert t2["bid_kurtosis"] is None

    def test_award_only_graph_degrades_to_empty(self) -> None:
        """§9.1 degradation path: Mendeley has no bids_on edges — the bid tier
        yields an empty, correctly-typed frame; the award tier still works."""
        nodes, edges = award_fixture()
        screens = bid_screens(nodes, edges)
        assert screens.is_empty()
        assert set(screens.columns) >= {"node_id", "n_bids", "bid_cv", "diffp"}
        assert not award_screens(nodes, edges).is_empty()

    def test_co_bid_stats(self) -> None:
        nodes, edges = bid_fixture()
        by_id = {r["node_id"]: r for r in co_bid_stats(nodes, edges).iter_rows(named=True)}
        # F1 and F2 share T1 and T2; F3 shares only T1 with both
        assert by_id["firm:M:F1"]["n_co_bidders"] == 2
        assert by_id["firm:M:F1"]["co_bid_repeat_max"] == 2
        assert by_id["firm:M:F3"]["co_bid_repeat_max"] == 1

    def test_co_bid_requires_firm_identities(self) -> None:
        """Swiss García markets: bids exist but carry no firm identity — the
        co-bid screen degrades to empty rather than inventing entities."""
        nodes, edges = bid_fixture()
        anonymous = edges.with_columns(pl.col("src").str.replace("firm:", "bid:").alias("src"))
        assert co_bid_stats(nodes, anonymous).is_empty()


def precomputed_fixture() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Mendeley-shaped awarded attrs (lot_bidscount / relative_value) on years
    1 and 3, plus a García-shaped bids_on screen attr and an OCDS-shaped
    bids_on attr with NO screen keys."""
    nodes = pl.DataFrame(
        {
            "node_id": [
                "firm:M:F1",
                "tender:M:T1",
                "tender:M:T2",
                "tender:G:TG",
                "tender:O:TO",
                "bid:G:B0",
                "firm:O:FO",
            ],
            "time_first_seen": [1, 1, 3, 1, 1, 2, 2],
        }
    )
    edges = pl.DataFrame(
        {
            "src": ["tender:M:T1", "tender:M:T2", "bid:G:B0", "firm:O:FO"],
            "dst": ["firm:M:F1", "firm:M:F1", "tender:G:TG", "tender:O:TO"],
            "edge_type": ["awarded", "awarded", "bids_on", "bids_on"],
            "timestamp": [1, 3, 2, 2],
            "directed": [True] * 4,
            "raw_attrs": [
                json.dumps({"lot_id": "L1", "lot_bidscount": 4, "relative_value": 0.2}),
                json.dumps({"lot_id": "L2", "lot_bidscount": 1, "relative_value": 0.8}),
                json.dumps({"winner": 1, "number_bids": 5, "cv": 0.03, "diffp": 0.01}),
                json.dumps({"bid_id": "bid-1", "currency": "GEL", "n_tenderers": 2}),
            ],
        }
    )
    return nodes, edges


class TestPrecomputedScreens:
    def test_mendeley_award_attrs_aggregate_per_firm_and_tender(self) -> None:
        nodes, edges = precomputed_fixture()
        by_id = {r["node_id"]: r for r in precomputed_screens(nodes, edges).iter_rows(named=True)}
        f1 = by_id["firm:M:F1"]
        assert f1["pc_lot_bidscount_mean"] == pytest.approx(2.5)  # (4+1)/2
        assert f1["pc_lot_bidscount_min"] == pytest.approx(1.0)  # the single-bid lot
        assert f1["pc_relative_value_mean"] == pytest.approx(0.5)
        assert by_id["tender:M:T1"]["pc_lot_bidscount_mean"] == pytest.approx(4.0)
        assert by_id["tender:M:T1"]["pc_cv"] is None  # no bid-tier data on Mendeley

    def test_garcia_bid_screen_attrs_land_per_tender(self) -> None:
        nodes, edges = precomputed_fixture()
        by_id = {r["node_id"]: r for r in precomputed_screens(nodes, edges).iter_rows(named=True)}
        tg = by_id["tender:G:TG"]
        assert tg["pc_cv"] == pytest.approx(0.03)
        assert tg["pc_diffp"] == pytest.approx(0.01)
        assert tg["pc_number_bids"] == pytest.approx(5.0)
        assert tg["pc_kstest"] is None  # key absent in the attrs — null, never 0
        assert tg["pc_lot_bidscount_mean"] is None

    def test_attrs_without_screen_keys_produce_no_row(self) -> None:
        """OCDS bids_on attrs (bid_id/currency/…) carry none of the screen
        keys — the node must get NO row, not an all-null noise row."""
        nodes, edges = precomputed_fixture()
        ids = set(precomputed_screens(nodes, edges)["node_id"].to_list())
        assert "tender:O:TO" not in ids

    @pytest.mark.leakage
    def test_as_of_excludes_future_award_attrs(self) -> None:
        """§9.1b: at as_of=2 the year-3 award (lot_bidscount=1) must not enter
        F1's aggregates — a screen value can never encode future information."""
        nodes, edges = precomputed_fixture()
        by_id = {
            r["node_id"]: r
            for r in precomputed_screens(nodes, edges, as_of=2).iter_rows(named=True)
        }
        f1 = by_id["firm:M:F1"]
        assert f1["pc_lot_bidscount_mean"] == pytest.approx(4.0)  # year-1 award only
        assert f1["pc_lot_bidscount_min"] == pytest.approx(4.0)
        assert f1["pc_relative_value_mean"] == pytest.approx(0.2)


class TestFeatureStore:
    def test_write_read_roundtrip_with_meta_and_sql_view(self, tmp_path) -> None:
        store = GraphStore(tmp_path)
        nodes, edges = structural_fixture()
        feats = structural_features(nodes, edges)
        store.write_features("toy", "structural", feats, meta={"as_of": None})
        assert store.read_features("toy", "structural").equals(feats)
        assert (tmp_path / "toy" / "features_structural.meta.json").is_file()
        con = store.connect("toy")
        n = con.execute("SELECT count(*) FROM features_structural").fetchone()
        assert n is not None and n[0] == feats.height

    def test_feature_pack_requires_node_id(self, tmp_path) -> None:
        store = GraphStore(tmp_path)
        with pytest.raises(Exception, match="node_id"):
            store.write_features("toy", "bad", pl.DataFrame({"x": [1.0]}))
