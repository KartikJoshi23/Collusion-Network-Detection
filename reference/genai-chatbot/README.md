# Gen-AI Chatbot — archived port source (Investigator Copilot)

**Status: reference only — not shipped, not imported, not linted.**
This is the triaged archive of the pre-existing Gen-AI Chatbot codebase, kept as the
port source for the Phase-2 **Investigator Copilot** (implementation-plan.md §4.6;
port scheduled Week 11, milestone MC). Do not modify it in place — port into
`backend/copilot/` and `frontend/src/views/copilot/` when Week 11 arrives.

## What was archived (the §4.6 "Port" + "Keep as reference" lists)

- `backend/app/graph/` — LangGraph orchestrator, state, all 15 agents, prompts
- `backend/app/retrieval/` — hybrid BM25 + dense retrieval, RRF, reranker
- `backend/app/tools/` — SQL (DuckDB) + RAG tool implementations
- `backend/app/data/` — ingestion machinery (pdf_chunker, pdf_ingestion, embeddings,
  duckdb_loader) + `schema.yaml` kept **as a structural template only** (its TechNova
  content gets replaced by the CollusionGraph artifact-store schema)
- `backend/app/api/chat.py` — SSE chat endpoint; `llm.py`, `config.py`, `main.py`
- `backend/requirements.txt`, `backend/Dockerfile` — dependency/pattern reference
- `eval/run_goldens.py` + `eval/goldens.json` — goldens harness; the JSON is a
  **structural template** for the 20–30 investigator goldens to be rebuilt
- `frontend/src/` — all seven chat components + glue (App, api.ts, types)
- `docs/` — `agent_communication.html`, `architecture.html`, `FIX_FRONTEND.md`
  (contains the mandatory SSE CRLF parser fix), `docker-compose.yml` (as pattern)
- `.env.example` — placeholder-only config template

## What was deliberately NOT brought into the repository (the §4.6 "Delete" list)

TechNova datasets (`Structured data/`, `Unstructured data/`, `TechNova_Data.zip`,
`technova.duckdb`), `facts*.yaml` domain content, `query_results/`, logs (`eval_20_output.log`,
`r1–r3.txt`), all root one-off scripts (`run_*.py`, `generate_extra_*.py`, `verify_spof.py`),
`__pycache__/`, `node_modules/`, nested `.claude/` settings, and **`.env`** (which contains a
live OpenAI API key — see security note).

## Security note (R18)

The original folder's `.env` holds a **live OpenAI API key**, and the original
`FIX_FRONTEND.md` embedded the key in an example block (redacted in this archived copy).
The key must be **rotated/revoked** at platform.openai.com. The original `Gen-AI Chatbot/`
folder is gitignored at the repo root and must never be committed.
