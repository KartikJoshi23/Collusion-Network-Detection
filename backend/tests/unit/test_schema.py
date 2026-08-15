"""IR schema tests (§4.2, §3.2): conformance, round-trip, catalog, caveat lock."""

import polars as pl
import pyarrow as pa
import pytest
from collusiongraph import SCREENING_CAVEAT
from collusiongraph.schema import (
    Alert,
    Domain,
    GraphStore,
    MotifType,
    SchemaError,
    conform,
)
from pydantic import ValidationError


def tiny_nodes() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "node_id": ["tx:1", "tx:2"],
            "node_type": ["transaction", "transaction"],
            "domain": ["financial", "financial"],
            "time_first_seen": [1, 2],
            "raw_features": [[0.5, 1.0], [0.25, 2.0]],
            "raw_attrs": [None, '{"fee": 0.1}'],
        }
    )


def tiny_edges() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src": ["tx:1"],
            "dst": ["tx:2"],
            "edge_type": ["pays"],
            "timestamp": [1],
            "amount": [None],
            "directed": [True],
            "raw_attrs": [None],
        }
    )


class TestConform:
    def test_valid_table_conforms(self) -> None:
        arrow = conform("nodes", tiny_nodes())
        assert arrow.num_rows == 2
        assert arrow.schema.field("raw_features").type == pa.list_(pa.float32())

    def test_missing_nullable_column_added_as_nulls(self) -> None:
        df = tiny_nodes().drop("raw_features")
        arrow = conform("nodes", df)
        assert arrow.column("raw_features").null_count == 2

    def test_missing_required_column_rejected(self) -> None:
        with pytest.raises(SchemaError, match="missing required"):
            conform("nodes", tiny_nodes().drop("node_id"))

    def test_extra_column_rejected(self) -> None:
        with pytest.raises(SchemaError, match="unknown columns"):
            conform("edges", tiny_edges().with_columns(pl.lit(1).alias("surprise")))

    def test_null_in_required_column_rejected(self) -> None:
        df = tiny_edges().with_columns(pl.lit(None, dtype=pl.Utf8).alias("src"))
        with pytest.raises(SchemaError, match="nulls in non-nullable"):
            conform("edges", df)

    def test_unknown_table_rejected(self) -> None:
        with pytest.raises(SchemaError, match="unknown IR table"):
            conform("mystery", tiny_nodes())


class TestGraphStore:
    def test_write_read_roundtrip(self, tmp_path) -> None:
        store = GraphStore(tmp_path)
        store.write("demo", "nodes", tiny_nodes())
        store.write("demo", "edges", tiny_edges())
        assert store.read("demo", "nodes").height == 2
        assert store.read("demo", "edges")["edge_type"].to_list() == ["pays"]

    def test_meta_roundtrip(self, tmp_path) -> None:
        store = GraphStore(tmp_path)
        store.write_meta("demo", {"time_unit": "elliptic_time_step", "n_nodes": 2})
        assert store.read_meta("demo")["time_unit"] == "elliptic_time_step"

    def test_duckdb_catalog_views(self, tmp_path) -> None:
        store = GraphStore(tmp_path)
        store.write("demo", "nodes", tiny_nodes())
        con = store.connect("demo")
        assert con.execute("SELECT count(*) FROM nodes").fetchone()[0] == 2

    def test_read_before_ingest_is_explicit(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match="run the adapter"):
            GraphStore(tmp_path).read("demo", "nodes")


class TestAlertCaveat:
    def _alert(self, **overrides) -> Alert:
        base = dict(
            alert_id="a1",
            domain=Domain.FINANCIAL,
            dataset="elliptic_pp",
            model_run_id="run0",
            rank=1,
            risk_score=0.97,
            member_node_ids=["tx:1", "tx:2"],
            n_members=2,
            motif_type=MotifType.CYCLE,
        )
        base.update(overrides)
        return Alert(**base)

    def test_default_caveat_is_the_fixed_string(self) -> None:
        assert self._alert().caveats == SCREENING_CAVEAT

    def test_weakened_caveat_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be altered"):
            self._alert(caveats="definitely guilty")

    def test_alert_conforms_to_parquet_schema(self) -> None:
        alert = self._alert()
        df = pl.DataFrame([alert.model_dump(mode="python")])
        arrow = conform("alerts", df)
        assert arrow.column("caveats").to_pylist() == [SCREENING_CAVEAT]
