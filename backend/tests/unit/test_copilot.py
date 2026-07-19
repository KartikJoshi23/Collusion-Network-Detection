"""Investigator Copilot core (§4.6, §7 step 27a): SELECT-only allowlist,
deterministic gates, guilt-language guard + caveat, alert tools over a tmp
serving fixture, and the bounded agent loop with a scripted mock client —
no network, no key."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import polars as pl
import pytest
from collusiongraph import SCREENING_CAVEAT
from copilot.guard import RED_FLAG_LEXICON, apply_guilt_guard, numeric_sanity_gate
from copilot.sql_tools import guard_query


class TestSqlAllowlist:
    @pytest.mark.parametrize(
        "query",
        [
            "INSERT INTO alerts VALUES (1)",
            "UPDATE alerts SET risk_score = 1",
            "DELETE FROM alerts",
            "DROP TABLE alerts",
            "CREATE TABLE x AS SELECT 1",
            "ATTACH 'other.db'",
            "PRAGMA database_list",
            "COPY alerts TO 'out.csv'",
        ],
    )
    def test_writes_and_escapes_refused(self, query: str) -> None:
        assert guard_query(query) is not None

    def test_multi_statement_refused(self) -> None:
        assert "multi-statement" in guard_query("SELECT 1; DROP TABLE alerts")

    @pytest.mark.parametrize(
        "query",
        ["SELECT * FROM alerts", "  with t as (select 1) select * from t  ", "SELECT 1;"],
    )
    def test_selects_allowed(self, query: str) -> None:
        assert guard_query(query) is None


class TestGuards:
    def test_guilt_language_rewritten_and_caveat_appended(self) -> None:
        answer, rewrites = apply_guilt_guard(
            "Account X is guilty of money laundering and committed fraud."
        )
        assert "guilty" not in answer.lower()
        assert "committed fraud" not in answer.lower()
        assert SCREENING_CAVEAT in answer
        assert rewrites  # the applied patterns are reported for the trace

    def test_clean_answer_gets_caveat_exactly_once(self) -> None:
        answer, rewrites = apply_guilt_guard("Alert ranked 1 shows a fan-in motif.")
        assert rewrites == []
        assert answer.count(SCREENING_CAVEAT) == 1
        again, _ = apply_guilt_guard(answer)
        assert again.count(SCREENING_CAVEAT) == 1

    def test_numeric_gate_flags_unsupported_numbers(self) -> None:
        ok, unsupported = numeric_sanity_gate(
            "There are 254 alerts and 999 communities.", "| n_alerts |\n| 254 |"
        )
        assert not ok and unsupported == ["999"]
        ok, unsupported = numeric_sanity_gate("There are 254 alerts.", "254 rows")
        assert ok and unsupported == []

    def test_lexicon_covers_both_domains(self) -> None:
        assert {"structuring", "cover bidding", "bid rotation"} <= RED_FLAG_LEXICON


@pytest.fixture()
def serving_fixture(tmp_path, monkeypatch):
    alerts = pl.DataFrame(
        {
            "alert_id": ["toy:run:1", "toy:run:2"],
            "domain": ["financial"] * 2,
            "dataset": ["toy"] * 2,
            "model_run_id": ["run0"] * 2,
            "rank": [1, 2],
            "risk_score": [0.9, 0.5],
            "member_node_ids": [["a", "b"], ["c"]],
            "n_members": [2, 1],
            "created_at": [datetime.now(UTC)] * 2,
            "caveats": [SCREENING_CAVEAT] * 2,
        }
    )
    alerts_path = tmp_path / "alerts.parquet"
    alerts.write_parquet(alerts_path)
    expl_dir = tmp_path / "explanations"
    expl_dir.mkdir()
    (expl_dir / "toy_run_1.json").write_text(
        json.dumps({"alert_id": "toy:run:1", "motif": None, "caveats": SCREENING_CAVEAT}),
        encoding="utf-8",
    )
    serving = tmp_path / "serving.json"
    serving.write_text(
        json.dumps(
            {
                "datasets": {
                    "toy": {
                        "domain": "financial",
                        "alerts": str(alerts_path),
                        "explanations": str(expl_dir),
                        "metrics": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("COPILOT_SERVING", str(serving))
    import copilot.config as config
    import copilot.store as store

    config.get_settings.cache_clear()
    store.serving_index.cache_clear()
    store.get_connection.cache_clear()
    yield serving
    config.get_settings.cache_clear()
    store.serving_index.cache_clear()
    store.get_connection.cache_clear()


class TestToolsOnServingFixture:
    def test_sql_tools_see_the_alerts_view(self, serving_fixture) -> None:
        from copilot.sql_tools import list_tables, run_sql

        assert "alerts" in list_tables()
        out = run_sql("SELECT COUNT(*) AS n FROM alerts")
        assert "| 2 |" in out.replace(" 2 ", " 2 ")

    def test_alert_tools(self, serving_fixture) -> None:
        from copilot.alert_tools import get_alert, get_explanation, list_alerts

        assert "toy:run:1" in list_alerts("toy")
        assert "0.9" in get_alert("toy:run:1")
        assert "toy:run:1" in get_explanation("toy:run:1")
        assert "top-k" in get_explanation("toy:run:2")  # honest miss, not an error
        assert "No alerts" in list_alerts("ghost")


def _scripted_client(script):
    """Mock OpenAI client yielding pre-scripted responses in order."""
    responses = iter(script)

    def create(**_kwargs):
        return next(responses)

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _tool_msg(name: str, arguments: str, call_id: str = "c1"):
    tc = SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )
    msg = SimpleNamespace(
        tool_calls=[tc],
        content=None,
        model_dump=lambda exclude_none=True: {"role": "assistant", "tool_calls": []},
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def _final_msg(content: str):
    msg = SimpleNamespace(
        tool_calls=None,
        content=content,
        model_dump=lambda exclude_none=True: {"role": "assistant", "content": content},
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class TestCorpusAndGrounding:  # RAG slice
    def test_bm25_finds_the_right_indicator(self) -> None:
        from copilot.corpus import corpus_search

        assert "OECD" in corpus_search("cover bidding checklist")
        assert "FATF-STRUCT-01" in corpus_search("structuring deposits below thresholds fan-in")

    def test_grounding_gate_requires_corpus_search_for_lexicon_terms(self) -> None:
        from copilot.guard import grounding_gate

        ok, terms = grounding_gate("What is cover bidding?", trace=["run_sql({})"])
        assert not ok and "cover bidding" in terms
        ok, _ = grounding_gate("What is cover bidding?", trace=['corpus_search({"query": "x"})'])
        assert ok
        ok, terms = grounding_gate("How many alerts are there?", trace=[])
        assert ok and terms == []


class TestGoldensHarness:  # §7 step 27c
    def test_gate_logic_on_scripted_answers(self, serving_fixture, tmp_path) -> None:
        from copilot.goldens import run_goldens

        goldens = tmp_path / "goldens.json"
        goldens.write_text(
            json.dumps(
                {
                    "goldens": [
                        {"id": "a", "category": "sql", "question": "q1", "must_contain": ["2"]},
                        {"id": "b", "category": "sql", "question": "q2", "must_contain": ["zz"]},
                    ]
                }
            ),
            encoding="utf-8",
        )
        client = _scripted_client(
            [
                _tool_msg("run_sql", json.dumps({"query": "SELECT COUNT(*) AS n FROM alerts"})),
                _final_msg("There are 2 alerts."),
                _final_msg("This account is guilty."),  # missing 'zz' AND guilt draft
                _final_msg("This account is guilty."),  # retry (draft no longer breaks)
            ]
        )
        report = run_goldens(goldens, output=tmp_path / "report.json", client=client)
        assert report["n_goldens"] == 2
        assert report["grounded_rate"] == 0.5
        # the guard rewrote the draft, so the RELEASED answer is clean —
        # but the draft-rewrite ceiling (10%) and grounding both fail the gate
        assert report["released_guilt_violations"] == 0
        assert report["draft_rewrite_rate"] == 0.5
        assert report["gate_passed"] is False
        assert (tmp_path / "report.json").is_file()


class TestAgentLoop:
    def test_grounded_tool_answer_passes_gates(self, serving_fixture) -> None:
        from copilot.agent import answer_question

        client = _scripted_client(
            [
                _tool_msg("run_sql", json.dumps({"query": "SELECT COUNT(*) AS n FROM alerts"})),
                _final_msg("The queue holds 2 alerts."),
            ]
        )
        out = answer_question("How many alerts?", client=client)
        assert out["numbers_grounded"] is True
        assert out["confidence"] > 0.5
        assert SCREENING_CAVEAT in out["answer"]
        assert out["trace"] and out["evidence"][0]["tool"] == "run_sql"

    def test_ungrounded_number_and_guilt_language_are_caught(self, serving_fixture) -> None:
        from copilot.agent import answer_question

        client = _scripted_client(
            [_final_msg("Account a7 is guilty of money laundering across 4711 transfers.")]
        )
        out = answer_question("Is a7 guilty?", client=client)
        assert out["numbers_grounded"] is False
        assert out["confidence"] < 0.5
        assert "guilty" not in out["answer"].lower()
        assert out["guard_rewrites"]
        assert SCREENING_CAVEAT in out["answer"]

    def test_iteration_budget_exhaustion_is_honest(self, serving_fixture, monkeypatch) -> None:
        from copilot.agent import answer_question

        monkeypatch.setenv("COPILOT_MAX_ITERATIONS", "2")
        import copilot.config as config

        config.get_settings.cache_clear()
        client = _scripted_client(
            [
                _tool_msg("list_tables", "{}"),
                _tool_msg("list_tables", "{}", call_id="c2"),
                _final_msg("never reached"),
            ]
        )
        out = answer_question("Loop forever", client=client)
        config.get_settings.cache_clear()
        assert "couldn't finalise" in out["answer"]
        assert "EXHAUSTED iteration budget" in out["trace"]


class TestStreamEndpoint:  # SS7 step 27b - the dock's SSE variant
    def _app_client(self, monkeypatch, script):
        import copilot.agent as agent
        from copilot.api import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        monkeypatch.setattr(agent, "get_client", lambda: _scripted_client(script))
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/copilot")
        return TestClient(app)

    def test_stream_emits_trace_then_final_with_crlf_framing(
        self, serving_fixture, monkeypatch
    ) -> None:
        client = self._app_client(
            monkeypatch,
            [
                _tool_msg("run_sql", json.dumps({"query": "SELECT COUNT(*) AS n FROM alerts"})),
                _final_msg("The queue holds 2 alerts."),
            ],
        )
        r = client.post("/api/v1/copilot/chat/stream", json={"question": "How many alerts?"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.text
        assert "\r\n\r\n" in body  # CRLF framing - the archive parser fix case
        blocks = [b for b in body.replace("\r\n", "\n").split("\n\n") if b.strip()]
        assert blocks[0].startswith("event: trace")
        assert '"step"' in blocks[0]
        assert blocks[-1].startswith("event: final")
        payload = json.loads(blocks[-1].split("data: ", 1)[1])
        # the final event IS the /chat contract, label and caveat included
        assert payload["ai_generated"] is True
        assert payload["caveat"] == SCREENING_CAVEAT
        assert payload["numbers_grounded"] is True
        assert payload["trace"] and payload["evidence"][0]["tool"] == "run_sql"

    def test_stream_without_key_is_a_clean_503(self, serving_fixture, monkeypatch) -> None:
        import copilot.agent as agent
        from copilot.api import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        def no_key():
            raise RuntimeError("no LLM key configured")

        monkeypatch.setattr(agent, "get_client", no_key)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/copilot")
        r = TestClient(app).post("/api/v1/copilot/chat/stream", json={"question": "hi"})
        assert r.status_code == 503
