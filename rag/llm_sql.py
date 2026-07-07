"""LLM-SQL bridge — builds prompts with RAG context and calls the LLM to generate SQL."""
from __future__ import annotations
import json
import re
from typing import Any

from .retriever import Retriever
from .semantic_cache import SemanticCache
from sql_engine import SqlEngine


class LLMtoSQL:
    """Takes a natural language question and returns SQL + results.

    Steps:
    1. Check semantic cache for identical/similar question
    2. Retrieve schema context + few-shot examples via Retriever
    3. Build prompt with context
    4. Call LLM → get SQL
    5. Execute SQL against DuckDB
    6. Cache the Q→SQL pair
    """

    def __init__(
        self,
        llm: Any | None = None,
        sql_engine: SqlEngine | None = None,
        retriever: Retriever | None = None,
        cache: SemanticCache | None = None,
    ):
        self.llm = llm
        self._engine = sql_engine or SqlEngine.get_instance()
        self.retriever = retriever or Retriever()
        self.cache = cache or SemanticCache()

    def generate_sql(
        self, question: str, dataset_name: str = ""
    ) -> dict[str, Any]:
        """Generate SQL from a natural language question.

        Returns:
            Dict with: sql, explanation, tables_used, answer, error, from_cache
        """
        # 1. Check cache
        cached_sql = self.cache.get(question)
        if cached_sql:
            try:
                result = self._engine.query(cached_sql)
                return {
                    "sql": cached_sql,
                    "explanation": "Used cached query",
                    "tables_used": [],
                    "data": result[:100],
                    "row_count": len(result),
                    "error": None,
                    "from_cache": True,
                }
            except Exception:
                pass  # Cache was stale, regenerate

        # 2. Retrieve context
        context = self.retriever.retrieve(question)

        # 2b. Fetch sample rows (first 5) to help LLM understand data patterns
        sample_rows = []
        if dataset_name and self._engine:
            try:
                from sql_engine.query_builder import _qi
                # Try to find the table — dataset_name might be a friendly name
                tables = self._engine.list_tables()
                for tbl in tables:
                    if dataset_name.replace(" ", "_").lower() in tbl.lower():
                        rows = self._engine.query(
                            f"SELECT * FROM {_qi(tbl)} LIMIT 5"
                        )
                        if rows:
                            sample_rows = rows
                            break
            except Exception:
                pass

        # 3. Build prompt
        prompt = self._build_prompt(
            question=question,
            schema_context=context["schema_context"],
            few_shot_context=context["few_shot_context"],
            dataset_name=dataset_name,
            sample_rows=sample_rows,
        )

        # 4. Call LLM
        if not self.llm:
            return {
                "sql": None,
                "explanation": "",
                "tables_used": context["tables"],
                "data": [],
                "row_count": 0,
                "error": "No LLM provider configured",
                "from_cache": False,
            }

        try:
            from llm import LLMMessage

            messages = [
                LLMMessage(
                    role="system",
                    content=(
                        "You are a SQL expert. Given a user question and database schema, "
                        "generate a DuckDB-compatible SQL query. "
                        "Return ONLY the SQL query inside ```sql ... ``` code block. "
                        "Then add a brief explanation in plain text."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ]

            response = self.llm.chat(messages)
            full_text = response.content

            # 5. Extract SQL from response
            sql = self._extract_sql(full_text)
            explanation = full_text.replace(f"```sql\n{sql}\n```", "").strip() if sql else full_text

            if not sql:
                return {
                    "sql": None,
                    "explanation": explanation,
                    "tables_used": context["tables"],
                    "data": [],
                    "row_count": 0,
                    "error": "Could not generate valid SQL",
                    "from_cache": False,
                }

            # 6. Execute SQL
            try:
                result = self._engine.query(sql)
                # Cache successful SQL
                self.cache.set(question, sql)

                return {
                    "sql": sql,
                    "explanation": explanation or "SQL query generated",
                    "tables_used": context["tables"],
                    "data": result[:100],
                    "row_count": len(result),
                    "error": None,
                    "from_cache": False,
                }
            except Exception as exec_error:
                return {
                    "sql": sql,
                    "explanation": explanation,
                    "tables_used": context["tables"],
                    "data": [],
                    "row_count": 0,
                    "error": f"SQL execution error: {exec_error}",
                    "from_cache": False,
                }

        except Exception as llm_error:
            return {
                "sql": None,
                "explanation": "",
                "tables_used": context["tables"],
                "data": [],
                "row_count": 0,
                "error": f"LLM error: {llm_error}",
                "from_cache": False,
            }

    def _build_prompt(
        self,
        question: str,
        schema_context: str,
        few_shot_context: str,
        dataset_name: str = "",
        sample_rows: list[dict] | None = None,
    ) -> str:
        """Build the LLM prompt with context."""
        parts = [
            f"Database schema:\n{schema_context}",
        ]

        # Add sample rows (first 5 only) to help LLM understand data values
        if sample_rows:
            parts.append("\n--- Sample Rows (first 5, to understand data values) ---")
            for i, row in enumerate(sample_rows[:5]):
                parts.append(f"  Row {i+1}: {json.dumps(row, default=str)}")

        parts.extend([
            f"\nUser question: {question}",
            "\nGenerate a DuckDB-compatible SQL query that answers this question.",
            "Rules:",
            "- Use DuckDB SQL syntax (e.g., DATE_TRUNC, EXTRACT, CORR, REGR_SLOPE)",
            "- Return only the SQL inside ```sql ... ```",
            "- Use meaningful column aliases",
            "- Limit results to 100 rows unless specified otherwise",
            "- Join only when necessary, prefer single-table queries",
        ])

        if dataset_name:
            parts.append(f"- The user is working with dataset: {dataset_name}")

        if few_shot_context:
            parts.append(f"\n{few_shot_context}")

        return "\n".join(parts)

    @staticmethod
    def _extract_sql(text: str) -> str | None:
        """Extract SQL from ```sql ... ``` code block."""
        match = re.search(r"```sql\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            sql = match.group(1).strip()
            # Remove leading/trailing semicolons
            sql = sql.rstrip(";").strip()
            return sql if sql else None

        # Fallback: try to find any SQL-like statement
        for keyword in ["SELECT", "WITH", "EXPLAIN"]:
            idx = text.upper().find(keyword)
            if idx >= 0:
                return text[idx:].strip().rstrip(";").strip()

        return None
