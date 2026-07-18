"""§7 step 26c — Elliptic++ actor (wallet) adapter + history_as_of labels.

Fixture-driven (§9.1 golden-file pattern): a tiny synthetic actor dataset
with a wallet whose illicit observation arrives LATE — the case the as-of
policy exists for — plus the §9.1b leakage negative control (features from a
future-truncated file must equal the full-file features for early wallets).
"""

from pathlib import Path

import polars as pl
import pytest
from collusiongraph.adapters.financial import elliptic_pp_actor_to_ir
from collusiongraph.schema import GraphStore
from collusiongraph.training.labels import history_labels_as_of, resolve_train_labels

HEADER = "address,Time step,class,f_a,f_b"
ROWS = [
    # w1: licit at step 10, ILLICIT at step 40 (the late-flip wallet)
    "w1,10,2,1.0,2.0",
    "w1,40,1,9.0,9.0",
    # w2: illicit from its first appearance
    "w2,12,1,3.0,4.0",
    # w3: unknown-only observations
    "w3,11,3,5.0,6.0",
    # w4: appears late (post-train_end), licit
    "w4,41,2,7.0,8.0",
]
EDGES = ["input_address,output_address", "w1,w2", "w2,w3", "w4,w1", "w2,w2"]


def write_fixture(raw: Path, rows: list[str]) -> None:
    (raw / "wallets_features_classes_combined.csv").write_text(
        "\n".join([HEADER, *rows]) + "\n", encoding="utf-8"
    )
    (raw / "AddrAddr_edgelist.csv").write_text("\n".join(EDGES) + "\n", encoding="utf-8")


@pytest.fixture()
def store(tmp_path) -> GraphStore:
    raw = tmp_path / "raw"
    raw.mkdir()
    write_fixture(raw, ROWS)
    s = GraphStore(tmp_path / "interim")
    elliptic_pp_actor_to_ir(raw, s, dataset="actor_toy")
    return s


class TestActorAdapter:
    def test_nodes_first_appearance_features_and_time(self, store) -> None:
        nodes = store.read("actor_toy", "nodes")
        w1 = nodes.filter(pl.col("node_id") == "addr:w1")
        assert w1["time_first_seen"][0] == 10
        # FIRST-appearance features, not the later row's
        assert w1["raw_features"][0].to_list() == [1.0, 2.0]
        assert nodes.height == 4
        assert set(nodes["node_type"].unique()) == {"address"}

    def test_edges_are_undated_pays(self, store) -> None:
        edges = store.read("actor_toy", "edges")
        assert edges.height == 4  # incl. the self-loop, kept faithfully
        assert edges["timestamp"].null_count() == edges.height
        assert set(edges["edge_type"].unique()) == {"pays"}
        pairs = set(zip(edges["src"].to_list(), edges["dst"].to_list(), strict=True))
        assert ("addr:w2", "addr:w2") in pairs

    def test_stored_labels_are_full_knowledge_rollup(self, store) -> None:
        labels = dict(store.read("actor_toy", "labels").select("node_id", "label").iter_rows())
        assert labels["addr:w1"] == "illicit"  # late illicit dominates the rollup
        assert labels["addr:w2"] == "illicit"
        assert labels["addr:w3"] == "unknown"
        assert labels["addr:w4"] == "licit"

    def test_history_pack_holds_known_observations_only(self, store) -> None:
        hist = store.read_features("actor_toy", "label_history")
        assert set(hist.columns) == {"node_id", "step", "label"}
        assert "addr:w3" not in hist["node_id"].to_list()  # unknown rows dropped
        assert hist.filter(pl.col("node_id") == "addr:w1").height == 2


class TestHistoryAsOfPolicy:
    def test_late_illicit_does_not_leak_into_train_labels(self, store) -> None:
        hist = store.read_features("actor_toy", "label_history")
        as_of = dict(history_labels_as_of(hist, 34).select("node_id", "label").iter_rows())
        assert as_of["addr:w1"] == "licit"  # illicit arrives at 40: unknowable at 34
        assert as_of["addr:w2"] == "illicit"
        assert "addr:w3" not in as_of  # never a known observation
        assert "addr:w4" not in as_of  # first knowable after the cut
        full = dict(history_labels_as_of(hist, 49).select("node_id", "label").iter_rows())
        assert full["addr:w1"] == "illicit"

    def test_resolver_requires_the_pack_and_routes(self, store) -> None:
        hist = store.read_features("actor_toy", "label_history")
        stored = store.read("actor_toy", "labels")
        edges = store.read("actor_toy", "edges")
        out = resolve_train_labels("history_as_of", stored, edges, 34, hist)
        assert dict(out.select("node_id", "label").iter_rows())["addr:w1"] == "licit"
        with pytest.raises(ValueError, match="label_history"):
            resolve_train_labels("history_as_of", stored, edges, 34, None)


class TestUndatedTrainGraph:
    """train_graph_restrict: the splitter's undated-edge policy at the trainer
    (dated edges cut at train_end; undated edges gated on BOTH endpoints being
    train members — never a bridge to future nodes)."""

    def test_undated_edges_gated_on_endpoint_membership(self) -> None:
        from collusiongraph.training.trainer import train_graph_restrict

        nodes = pl.DataFrame({"node_id": ["a", "b", "late"], "time_first_seen": [1, 2, 99]})
        edges = pl.DataFrame(
            {
                "src": ["a", "a", "b", "a"],
                "dst": ["b", "late", "late", "b"],
                "timestamp": [None, None, 99, 1],
            }
        )
        t_nodes, t_edges = train_graph_restrict(nodes, edges, train_end=34)
        assert set(t_nodes["node_id"]) == {"a", "b"}
        kept = set(zip(t_edges["src"].to_list(), t_edges["dst"].to_list(), strict=True))
        # undated a->b kept (both members); undated a->late dropped (future
        # endpoint); dated b->late@99 dropped (future); dated a->b@1 kept
        assert kept == {("a", "b")}
        assert t_edges.height == 2  # the dated AND the undated a->b


class TestActorLeakage:  # §9.1b negative control
    def test_truncated_file_yields_identical_early_wallet_features(self, tmp_path) -> None:
        raw_full, raw_trunc = tmp_path / "full", tmp_path / "trunc"
        raw_full.mkdir()
        raw_trunc.mkdir()
        write_fixture(raw_full, ROWS)
        truncated = [r for r in ROWS if int(r.split(",")[1]) <= 34]
        write_fixture(raw_trunc, truncated)

        s_full = GraphStore(tmp_path / "i1")
        s_trunc = GraphStore(tmp_path / "i2")
        elliptic_pp_actor_to_ir(raw_full, s_full, dataset="a")
        elliptic_pp_actor_to_ir(raw_trunc, s_trunc, dataset="a")

        full_nodes = s_full.read("a", "nodes").filter(pl.col("time_first_seen") <= 34)
        trunc_nodes = s_trunc.read("a", "nodes")
        f = {
            r[0]: (r[1], list(r[2]))
            for r in full_nodes.select("node_id", "time_first_seen", "raw_features").iter_rows()
        }
        t = {
            r[0]: (r[1], list(r[2]))
            for r in trunc_nodes.select("node_id", "time_first_seen", "raw_features").iter_rows()
        }
        # every wallet first seen ≤34 has IDENTICAL features and first-seen
        # whether or not the future rows exist — nothing future leaks in
        assert f == t
