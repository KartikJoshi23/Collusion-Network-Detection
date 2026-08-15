"""SQL Agent — tool-using loop.

Runs a bounded OpenAI function-calling loop:
  user_query + intent + schema + 3 few-shot examples
       ↓
  model chooses list_tables / describe_table / sample_rows / count_rows / run_sql
       ↓
  tool result fed back
       ↓
  ... up to MAX_ITERATIONS iterations ...
       ↓
  final natural-language answer grounded in the last run_sql result
"""

from __future__ import annotations

import json
import logging
import re

from app.graph.prompts import SQL_AGENT_SYSTEM, load_schema_text
from app.graph.state import AgentState, SqlResult
from app.llm import get_model_name, get_openai_client
from app.retrieval.fewshot import get_fewshot_selector
from app.tools import sql_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8  # upper bound on tool-calling turns


def _build_fewshot(intent: dict) -> str:
    if not intent:
        return ""
    selector = get_fewshot_selector()
    goldens = [
        g for g in selector.by_intent(intent, k=5)
        if g.get("category", "").startswith("sql")
    ][:3]
    if not goldens:
        return ""
    blocks: list[str] = []
    for g in goldens:
        blocks.append(
            f"Example: {g['question']}\nExpected SQL shape:\n```sql\n{g.get('expected_sql_shape','(no shape)')}\n```"
        )
    return "\n\n".join(blocks)


def _extract_sql(final_content: str) -> str:
    """Pull the last fenced SQL block out of the model's final message."""
    matches = re.findall(r"```sql\s*(.*?)```", final_content, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[-1].strip()
    return ""


def sql_agent_node(state: AgentState) -> dict:
    client = get_openai_client()
    model = get_model_name()

    intent = state.get("intent") or {}
    query = state.get("enriched_query") or state["user_query"]

    few_shots = _build_fewshot(intent)

    user_msg_parts = [
        f"User question: {query}",
        "",
        f"Structured intent:\n```json\n{json.dumps(intent, indent=2)}\n```",
        "",
        f"Database schema:\n```yaml\n{load_schema_text()}\n```",
    ]
    if few_shots:
        user_msg_parts += ["", "Reference golden examples:", few_shots]

    messages: list[dict] = [
        {"role": "system", "content": SQL_AGENT_SYSTEM},
        {"role": "user", "content": "\n".join(user_msg_parts)},
    ]

    executed_sql = ""
    last_run_result = ""
    iterations = 0

    for iteration in range(MAX_ITERATIONS):
        iterations = iteration + 1
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=sql_tools.TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.0,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            # Model produced its final answer.
            final_answer = msg.content or ""
            executed_sql = _extract_sql(final_answer) or executed_sql
            logger.info("SQL Agent done in %s iteration(s); sql=%s", iterations, bool(executed_sql))
            sql_result: SqlResult = {
                "sql": executed_sql,
                "rows_markdown": last_run_result,
                "row_count": last_run_result.count("\n|") if last_run_result else 0,
                "error": None,
                "iterations": iterations,
            }
            trace = state.get("trace", []) + [f"sql_agent -> {iterations} iter"]
            return {"sql_result": sql_result, "draft_answer": final_answer, "trace": trace}

        # Execute every tool call the model requested, append results.
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = sql_tools.TOOL_DISPATCH.get(name)
            if handler is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = handler(args)
                except Exception as e:  # noqa: BLE001 (we want to surface tool errors to the model)
                    result = f"Tool raised: {e}"
            if name == "run_sql":
                executed_sql = args.get("query", executed_sql) or executed_sql
                last_run_result = result
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    logger.warning("SQL Agent hit MAX_ITERATIONS (%s) without finalising.", MAX_ITERATIONS)
    trace = state.get("trace", []) + [f"sql_agent -> EXHAUSTED after {iterations}"]
    return {
        "sql_result": {
            "sql": executed_sql,
            "rows_markdown": last_run_result,
            "row_count": 0,
            "error": f"Agent exceeded {MAX_ITERATIONS} tool-calling iterations without finalising.",
            "iterations": iterations,
        },
        "draft_answer": "I couldn't finalise this query within the iteration budget. Please try rephrasing.",
        "trace": trace,
    }
