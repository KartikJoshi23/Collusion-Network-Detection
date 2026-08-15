"""Golden-file tests for the procurement adapters (§7 step 6, §9.1).

The fixtures deliberately exercise both degradation paths of the
award-network-first rule (§4.2 rule 1):
* Mendeley — award-only (no losing-bidder identities anywhere), incl. a
  null-buyer row that must not produce a buyer node or buys_from edge;
* García — one toy market WITH firm identities and one WITHOUT (mirroring
  the real 4-of-6-markets situation).

Regenerate goldens deliberately with
``python backend/tests/unit/test_procurement_adapters.py`` and justify in the
commit message.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from collusiongraph.adapters.procurement import garcia_to_ir, mendeley_to_ir
from collusiongraph.schema import GraphStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TOY_MARKETS = {"ToyFirms": True, "ToyAnon": False}


def ir_as_plain_dict(store: GraphStore, dataset: str) -> dict:
    out: dict = {}
    for table in ("nodes", "edges", "labels"):
        df = store.read(dataset, table).sort(pl.all())
        out[table] = json.loads(df.write_json())
    return out


def run_adapter(tmp_path, name: str) -> tuple[dict, dict]:
    store = GraphStore(tmp_path)
    if name == "mendeley_eu":
        stats = mendeley_to_ir(FIXTURES / "mendeley_eu", store)
    else:
        stats = garcia_to_ir(FIXTURES / "garcia_rodriguez", store, markets=TOY_MARKETS)
    return ir_as_plain_dict(store, name), stats


@pytest.mark.parametrize("name", ["mendeley_eu", "garcia_rodriguez"])
def test_adapter_matches_golden(tmp_path, name: str) -> None:
    actual, _ = run_adapter(tmp_path, name)
    golden_path = FIXTURES / name / "expected_ir.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual == golden, f"adapter output diverged from {golden_path}"


class TestMendeleyAwardFirst:
    def test_counts(self, tmp_path) -> None:
        _, stats = run_adapter(tmp_path, "mendeley_eu")
        assert stats["n_nodes"] == 8  # 3 firms + 3 tenders + 2 buyers
        assert stats["n_edges"] == 6  # 4 awarded + 2 buys_from
        assert stats["label_counts"] == {"illicit": 4, "licit": 2}

    def test_no_bid_tier_edges_exist(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path, "mendeley_eu")
        edge_types = {e["edge_type"] for e in actual["edges"]}
        assert edge_types == {"awarded", "buys_from"}  # award core only (§4.2 rule 1)

    def test_null_buyer_produces_no_node_or_edge(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path, "mendeley_eu")
        buyer_nodes = [n for n in actual["nodes"] if n["node_type"] == "buyer"]
        assert len(buyer_nodes) == 2
        assert all("null" not in n["node_id"] for n in buyer_nodes)
        t2_buys = [e for e in actual["edges"] if e["edge_type"] == "buys_from" and "T2" in e["dst"]]
        assert t2_buys == []


class TestGarciaTiers:
    def test_counts(self, tmp_path) -> None:
        _, stats = run_adapter(tmp_path, "garcia_rodriguez")
        assert stats["n_nodes"] == 10  # 3 tenders + 5 bids + 2 firms
        assert stats["n_edges"] == 10  # 5 bid->tender + 3 firm->tender + 2 awarded
        assert stats["markets"]["ToyFirms"]["firm_identities"] is True
        assert stats["markets"]["ToyAnon"]["firm_identities"] is False

    def test_identity_market_gets_firms_and_awards(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path, "garcia_rodriguez")
        awarded = [e for e in actual["edges"] if e["edge_type"] == "awarded"]
        assert {e["dst"] for e in awarded} == {"firm:ToyFirms:1", "firm:ToyFirms:2"}

    def test_anonymous_market_degrades_to_bid_tier(self, tmp_path) -> None:
        """The §9.1 degradation-path proof: no firm nodes, no awarded edges,
        but the bid-price tier still fully materializes."""
        actual, _ = run_adapter(tmp_path, "garcia_rodriguez")
        anon_nodes = [n for n in actual["nodes"] if ":ToyAnon:" in n["node_id"]]
        assert {n["node_type"] for n in anon_nodes} == {"tender", "bid"}
        anon_edges = [e for e in actual["edges"] if ":ToyAnon:" in e["dst"]]
        assert {e["edge_type"] for e in anon_edges} == {"bids_on"}
        assert all(e["amount"] is not None for e in anon_edges)

    def test_bid_labels_follow_collusive_competitor(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path, "garcia_rodriguez")
        bid_labels = {
            r["node_id"]: r["label"] for r in actual["labels"] if r["node_id"].startswith("bid:")
        }
        assert bid_labels["bid:ToyFirms:0"] == "illicit"
        assert bid_labels["bid:ToyFirms:1"] == "illicit"
        assert bid_labels["bid:ToyFirms:2"] == "licit"
        assert bid_labels["bid:ToyAnon:0"] == "licit"


def _regenerate_goldens() -> None:  # pragma: no cover — manual, deliberate use only
    import tempfile

    for name in ("mendeley_eu", "garcia_rodriguez"):
        with tempfile.TemporaryDirectory() as tmp:
            actual, _ = run_adapter(Path(tmp), name)
        path = FIXTURES / name / "expected_ir.json"
        path.write_text(json.dumps(actual, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("regenerated", path)


if __name__ == "__main__":
    _regenerate_goldens()
