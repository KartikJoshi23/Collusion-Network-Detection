"""Golden-file + behavior tests for the OCDS adapter (§7 step 30, §4.3 D5, §9.1).

The fixture exercises every degradation path in one pass:
* a bids-bearing release with a JOINT bid (two tenderers on one bid — the
  co-bid substrate the D5 publisher was selected for) and a losing bidder;
* an award-only release (award-network-first core, §4.2 rule 1);
* bids without identified tenderers and a buyer without an id — skipped and
  counted, never guessed at;
* an undated release — skipped and counted (§9.1b: undated edges cannot enter
  a temporal split honestly).

Regenerate the golden deliberately with
``python backend/tests/unit/test_ocds_adapter.py`` and justify in the commit
message.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from collusiongraph.adapters.procurement import ocds_to_ir
from collusiongraph.schema import GraphStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def run_adapter(tmp_path) -> tuple[dict, dict]:
    store = GraphStore(tmp_path)
    stats = ocds_to_ir(FIXTURES / "ocds_georgia", store)
    out: dict = {}
    for table in ("nodes", "edges", "labels"):
        df = store.read("ocds_georgia", table).sort(pl.all())
        out[table] = json.loads(df.write_json())
    return out, stats


def test_adapter_matches_golden(tmp_path) -> None:
    actual, _ = run_adapter(tmp_path)
    golden_path = FIXTURES / "ocds_georgia" / "expected_ir.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual == golden, f"adapter output diverged from {golden_path}"


class TestOcdsMapping:
    def test_counts(self, tmp_path) -> None:
        _, stats = run_adapter(tmp_path)
        assert stats["n_releases"] == 4
        assert stats["releases_skipped_no_date"] == 1  # ocds-toy-d
        assert stats["node_counts"] == {"buyer": 1, "firm": 3, "tender": 3}
        assert stats["edge_counts"] == {"awarded": 2, "bids_on": 3, "buys_from": 2}
        assert stats["bids_kept"] == 2
        assert stats["bids_skipped_no_tenderer"] == 2  # empty + id-less tenderer
        assert stats["years"] == {"2015": 1, "2016": 2}

    def test_award_only_release_builds_core_graph(self, tmp_path) -> None:
        """§4.2 rule 1: ocds-toy-b has no bids block yet yields awarded + buys_from."""
        actual, _ = run_adapter(tmp_path)
        b_edges = {
            e["edge_type"] for e in actual["edges"] if e["dst"] == "tender:georgia:ocds-toy-b"
        } | {e["edge_type"] for e in actual["edges"] if e["src"] == "tender:georgia:ocds-toy-b"}
        assert b_edges == {"buys_from", "awarded"}

    def test_joint_bid_yields_one_edge_per_tenderer(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path)
        bid2 = [
            e
            for e in actual["edges"]
            if e["edge_type"] == "bids_on" and json.loads(e["raw_attrs"])["bid_id"] == "bid-2"
        ]
        assert {e["src"] for e in bid2} == {"firm:georgia:F2", "firm:georgia:F3"}
        assert all(json.loads(e["raw_attrs"])["n_tenderers"] == 2 for e in bid2)
        assert all(e["amount"] == 13000 for e in bid2)

    def test_losing_bidders_are_materialized(self, tmp_path) -> None:
        """The D5 selection criterion: firms that bid and did NOT win exist in the IR."""
        actual, _ = run_adapter(tmp_path)
        awarded_to = {e["dst"] for e in actual["edges"] if e["edge_type"] == "awarded"}
        bidders = {e["src"] for e in actual["edges"] if e["edge_type"] == "bids_on"}
        assert bidders - awarded_to == {"firm:georgia:F2", "firm:georgia:F3"}

    def test_idless_buyer_and_tenderers_are_dropped(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path)
        node_ids = {n["node_id"] for n in actual["nodes"]}
        assert {n for n in node_ids if n.startswith("buyer:")} == {"buyer:georgia:B1"}
        # ocds-toy-c: tender node exists, but no edges at all touch it
        touched = {e["src"] for e in actual["edges"]} | {e["dst"] for e in actual["edges"]}
        assert "tender:georgia:ocds-toy-c" in node_ids
        assert "tender:georgia:ocds-toy-c" not in touched

    def test_undated_release_contributes_nothing(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path)
        node_ids = {n["node_id"] for n in actual["nodes"]}
        assert not any("ocds-toy-d" in n or "F4" in n or "B2" in n for n in node_ids)

    def test_all_labels_unknown(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path)
        assert len(actual["labels"]) == 6  # 3 firms + 3 tenders; buyers unlabeled
        assert {r["label"] for r in actual["labels"]} == {"unknown"}
        assert {r["label_source"] for r in actual["labels"]} == {"ocds_unlabeled"}


@pytest.mark.leakage
def test_first_seen_never_postdates_first_edge(tmp_path) -> None:
    """§9.1b data-level guard: a node's time_first_seen is a true first —
    no incident edge may be timestamped earlier (F1-pattern at the adapter).
    Also pins the min-across-years rule: F1 appears in 2015 and 2016."""
    actual, _ = run_adapter(tmp_path)
    first_seen = {n["node_id"]: n["time_first_seen"] for n in actual["nodes"]}
    for e in actual["edges"]:
        for endpoint in (e["src"], e["dst"]):
            assert first_seen[endpoint] <= e["timestamp"], (
                f"{endpoint} first seen {first_seen[endpoint]} "
                f"but touched by an edge at {e['timestamp']}"
            )
    assert first_seen["firm:georgia:F1"] == 2015


def _regenerate_golden() -> None:  # pragma: no cover — manual, deliberate use only
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        actual, _ = run_adapter(Path(tmp))
    path = FIXTURES / "ocds_georgia" / "expected_ir.json"
    path.write_text(json.dumps(actual, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("regenerated", path)


if __name__ == "__main__":
    _regenerate_golden()
