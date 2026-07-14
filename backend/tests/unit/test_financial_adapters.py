"""Golden-file tests for the financial adapters (§7 step 5, §9.1).

Fixture inputs live in ``backend/tests/fixtures/<dataset>/``; the expected IR
tables are committed as ``expected_ir.json`` next to them. If an adapter's
output changes, the diff shows up in review — regenerate goldens deliberately
with ``python -m tests.unit.test_financial_adapters`` only when the change is
intended, and say so in the commit message.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from collusiongraph.adapters.financial import amlworld_to_ir, elliptic_pp_to_ir
from collusiongraph.schema import GraphStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def ir_as_plain_dict(store: GraphStore, dataset: str) -> dict:
    out: dict = {}
    for table in ("nodes", "edges", "labels"):
        df = store.read(dataset, table).sort(pl.first())
        out[table] = json.loads(df.write_json())
    return out


def run_adapter(tmp_path, name: str) -> tuple[dict, dict]:
    store = GraphStore(tmp_path)
    if name == "elliptic_pp":
        stats = elliptic_pp_to_ir(FIXTURES / "elliptic_pp", store)
    else:
        stats = amlworld_to_ir(FIXTURES / "amlworld", store)
    return ir_as_plain_dict(store, name), stats


@pytest.mark.parametrize("name", ["elliptic_pp", "amlworld_hi_small"])
def test_adapter_matches_golden(tmp_path, name: str) -> None:
    fixture_dir = "elliptic_pp" if name == "elliptic_pp" else "amlworld"
    actual, _ = run_adapter(tmp_path, name)
    golden_path = FIXTURES / fixture_dir / "expected_ir.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual == golden, f"adapter output diverged from {golden_path}"


class TestEllipticPP:
    def test_stats_and_meta(self, tmp_path) -> None:
        _, stats = run_adapter(tmp_path, "elliptic_pp")
        assert stats["n_nodes"] == 4
        assert stats["n_edges"] == 3
        assert stats["n_features"] == 3  # time step + 2 locals, mirroring the 183 convention
        assert stats["time_unit"] == "elliptic_time_step"
        assert stats["label_counts"] == {"illicit": 1, "licit": 2, "unknown": 1}

    def test_edge_timestamp_is_source_time_step(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path, "elliptic_pp")
        by_pair = {(e["src"], e["dst"]): e for e in actual["edges"]}
        assert by_pair[("tx:100", "tx:101")]["timestamp"] == 1
        assert by_pair[("tx:102", "tx:103")]["timestamp"] == 2


class TestAMLworld:
    def test_stats_and_meta(self, tmp_path) -> None:
        _, stats = run_adapter(tmp_path, "amlworld_hi_small")
        assert stats["n_nodes"] == 4  # A1, A2, B1, B2
        assert stats["n_edges"] == 4
        assert stats["n_laundering_edges"] == 2
        assert stats["time_unit"] == "epoch_minutes"
        # nodes touched by a laundering edge: A2, B1 (edge 2) + B2, A1 (edge 4)
        assert stats["label_counts"] == {"illicit": 4}

    def test_edge_ground_truth_rides_in_raw_attrs(self, tmp_path) -> None:
        actual, _ = run_adapter(tmp_path, "amlworld_hi_small")
        flags = sorted(json.loads(e["raw_attrs"])["is_laundering"] for e in actual["edges"])
        assert flags == [0, 0, 1, 1]

    def test_post_window_fence_recorded_in_meta(self, tmp_path) -> None:
        _, stats = run_adapter(tmp_path, "amlworld_hi_small")
        post_window = [
            e
            for e in json.loads((FIXTURES / "amlworld" / "expected_ir.json").read_text())["edges"]
            if e["timestamp"] > stats["primary_window_end"]
        ]
        assert len(post_window) == 1  # the Sep-12 fixture row sits beyond the fence


def _regenerate_goldens() -> None:  # pragma: no cover — manual, deliberate use only
    import tempfile

    for name, fixture_dir in [("elliptic_pp", "elliptic_pp"), ("amlworld_hi_small", "amlworld")]:
        with tempfile.TemporaryDirectory() as tmp:
            actual, _ = run_adapter(Path(tmp), name)
        path = FIXTURES / fixture_dir / "expected_ir.json"
        path.write_text(json.dumps(actual, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("regenerated", path)


if __name__ == "__main__":
    _regenerate_goldens()
