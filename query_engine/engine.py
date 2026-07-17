"""
Core engine: takes natural language questions + datasets and returns
structured results with data, visualizations, and recommendations.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from data_sources.base import Dataset
from llm import LLMProvider, LLMMessage, SYSTEM_PROMPTS, get_llm


@dataclass
class ChartRecommendation:
    chart_type: str  # "bar", "line", "scatter", "pie", "area", "heatmap", "histogram"
    title: str
    x_column: str
    y_column: str | list[str]
    aggregation: str = "none"  # "sum", "mean", "count", "none"
    color_column: str | None = None
    description: str = ""


@dataclass
class QueryResult:
    answer: str = ""
    data: pd.DataFrame | None = None
    charts: list[ChartRecommendation] = field(default_factory=list)
    sql_query: str | None = None
    code_snippet: str | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "charts": [c.__dict__ for c in self.charts],
            "sql_query": self.sql_query,
            "code_snippet": self.code_snippet,
            "error": self.error,
            "metadata": self.metadata,
        }


class QueryEngine:
    """Main query engine — turns natural language into data insights."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm()
        self._history: list[dict] = []

    def _build_dataset_context(self, dataset: Dataset) -> str:
        """Build a concise textual description of a dataset for the LLM prompt.

        Sends only schema info, a few sample rows (max 10), and basic stats
        for the first 8 numeric columns — enough for the LLM to generate good SQL.
        """
        summary = dataset.summary()
        lines = []
        lines.append(f"Dataset: {dataset.name}")
        lines.append(f"Table name (use this in FROM clause): {dataset.table_name}")
        lines.append(f"Rows: {summary['rows']} | Columns: {summary['columns']}")
        lines.append(f"\nAll column names (use ONLY these, no others):")
        lines.append(f"  {', '.join(summary['column_names'])}")
        lines.append(f"\nNumeric columns: {summary['numeric_columns']}")
        lines.append(f"Categorical columns: {summary['categorical_columns']}")
        lines.append(f"Date/time columns: {summary['date_columns']}")

        # Missing data (only columns with any)
        missing = [f"{k}({v})" for k, v in summary["missing_data"].items() if v > 0]
        if missing:
            lines.append(f"\nMissing values: {', '.join(missing)}")

        # Sample rows — max 10, compact JSON (column info, not all values)
        sample = summary.get("sample", [])[:10]
        if sample:
            lines.append(f"\n--- Sample Data (first {len(sample)} rows, {len(sample[0])} columns) ---")
            # Compact: one row per line, values only (no indentation explosion)
            for i, row in enumerate(sample):
                lines.append(f"  Row {i+1}: {json.dumps(row, default=str)}")

        # Basic stats — first 8 numeric columns only
        if summary.get("basic_stats"):
            stats = {k: v for k, v in list(summary["basic_stats"].items())[:8]}
            lines.append("\n--- Summary Statistics (first 8 numeric columns) ---")
            lines.append(json.dumps(stats, indent=2, default=str))

        return "\n".join(lines)

    def _parse_chart_recommendations(self, text: str) -> list[ChartRecommendation]:
        """Extract chart recommendations from LLM response text."""
        charts = []

        def _sanitize(val: Any) -> str:
            """Sanitize a column name value — must be a plain string, no objects."""
            if val is None:
                return ""
            if isinstance(val, str):
                val = val.strip()
                # Clean contamination patterns
                val = val.replace("[object Object]", "").replace("object Object", "").strip()
                return val
            if isinstance(val, list):
                if len(val) > 0:
                    return _sanitize(val[0])
                return ""
            if isinstance(val, dict):
                # Object found — this is the [object Object] root cause
                # Try to extract a useful column name from common keys
                for k in ("column", "name", "field", "x", "y", "value"):
                    if k in val and isinstance(val[k], str):
                        return _sanitize(val[k])
                return ""
            try:
                s = str(val).replace("[object Object]", "").strip()
                return s
            except Exception:
                return ""

        # Strategy 1: Find code blocks and parse JSON with brace-depth counting
        # Handle case-insensitive and various code block markers
        json_pattern = r"```(?:json|jsonc|javascript|js|python)?\s*\n?(.*?)\n?```"
        matches = re.findall(json_pattern, text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            content = match.strip()
            for start_marker, end_marker in [("{", "}"), ("[", "]")]:
                if not content.startswith(start_marker):
                    continue
                depth = 0
                end_pos = 0
                for i, ch in enumerate(content):
                    if ch == start_marker:
                        depth += 1
                    elif ch == end_marker:
                        depth -= 1
                        if depth == 0:
                            end_pos = i + 1
                            break
                if end_pos == 0:
                    continue
                try:
                    data = json.loads(content[:end_pos])
                except json.JSONDecodeError:
                    continue
                items = [data] if isinstance(data, dict) else data
                for item in items:
                    if isinstance(item, dict) and "chart_type" in item:
                        charts.append(ChartRecommendation(
                            chart_type=_sanitize(item["chart_type"]),
                            title=_sanitize(item.get("title") or item.get("desc") or ""),
                            x_column=_sanitize(item.get("x_column") or item.get("x") or ""),
                            y_column=_sanitize(item.get("y_column") or item.get("y") or ""),
                            aggregation=_sanitize(item.get("aggregation") or "none"),
                            color_column=_sanitize(item.get("color_column")),
                            description=_sanitize(item.get("description") or item.get("desc") or ""),
                        ))
                break

        # Strategy 2: If no charts found from code blocks, try finding JSON inline
        if not charts:
            # Look for JSON objects containing "chart_type" anywhere in the text
            inline_json_pattern = r'\{[^{}]*"chart_type"[^{}]*\}'
            inline_matches = re.findall(inline_json_pattern, text, re.DOTALL)
            for match_data in inline_matches:
                try:
                    data = json.loads(match_data)
                    if isinstance(data, dict) and "chart_type" in data:
                        charts.append(ChartRecommendation(
                            chart_type=_sanitize(data["chart_type"]),
                            title=_sanitize(data.get("title") or ""),
                            x_column=_sanitize(data.get("x_column") or data.get("x") or ""),
                            y_column=_sanitize(data.get("y_column") or data.get("y") or ""),
                            aggregation=_sanitize(data.get("aggregation") or "none"),
                            color_column=_sanitize(data.get("color_column")),
                            description=_sanitize(data.get("description") or data.get("desc") or ""),
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

        # Fallback: parse structured chart hints in text
        chart_hints = re.findall(
            r"(?:chart|plot|graph|visualization)[:\s]+(\w+(?:\s+\w+)*)\s*[:\-]\s*x[:\s]*(\w+)\s*[,\s]+y[:\s]*(\w+)",
            text, re.IGNORECASE,
        )
        for hint in chart_hints:
            charts.append(ChartRecommendation(
                chart_type="bar" if hint[0].lower() in ("bar", "column") else "line" if "line" in hint[0].lower() else "bar",
                title=_sanitize(hint[0].strip()),
                x_column=_sanitize(hint[1].strip()),
                y_column=_sanitize(hint[2].strip()),
            ))

        # Final filter: remove any chart with contaminated or empty column names
        valid_charts = []
        for c in charts:
            if c.chart_type and _sanitize(c.x_column) and _sanitize(c.y_column):
                # Check for contamination in the already-set values
                ok = True
                for field in [c.x_column, c.y_column, c.color_column or "", c.title, c.description]:
                    s = str(field)
                    if "object Object" in s or "[object" in s or "{" in s:
                        ok = False
                        break
                if ok:
                    valid_charts.append(c)
        return valid_charts

    def _clean_answer(self, text: str) -> str:
        """Strip SQL and JSON code blocks from the answer text — keep only explanations."""
        import re
        # Remove SQL code blocks first: ```sql ... ```
        text = re.sub(r'```sql\s*\n.*?```', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove JSON code blocks: ```json ... ```
        text = re.sub(r'```json\s*\n.*?```', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove JSON inline code blocks: ```jsonc, ```javascript, ```js
        text = re.sub(r'```(?:jsonc|javascript|js)\s*\n.*?```', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove empty ```...``` that remain
        text = re.sub(r'```\s*\n.*?```', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove any leftover standalone triple backticks
        text = re.sub(r'```\w*', '', text)
        # Clean up excessive blank lines left behind
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # Remove any [object Object] text leaked from LLM
        text = text.replace("[object Object]", "").replace("object Object", "")
        return text.strip()

    def _execute_pandas(self, code: str, df: pd.DataFrame) -> str:
        """Safely execute a pandas code snippet and return the result string."""
        try:
            local_vars = {"df": df, "pd": pd}
            exec(code, {"__builtins__": {}}, local_vars)
            result = local_vars.get("result", local_vars.get("_", ""))
            return str(result)
        except Exception as exc:
            return f"Execution error: {exc}"

    def query(
        self,
        question: str,
        dataset: Dataset | None = None,
        context: str = "",
        system_prompt_key: str = "data_analyst",
        generate_charts: bool = True,
    ) -> QueryResult:
        """Answer a natural language question against a dataset by generating SQL.

        The LLM receives:
        - Dataset schema (columns, types)
        - First 10 sample rows (for context only)
        - Basic stats for numeric columns

        It generates a DuckDB SQL query, which we execute, then render as a chart.
        """
        result = QueryResult()

        try:
            # Build system prompt
            default_system = SYSTEM_PROMPTS.get(system_prompt_key, SYSTEM_PROMPTS["data_analyst"])
            system = (
                "You are a SQL expert for DuckDB. Your job is to answer data questions "
                "by generating DuckDB-compatible SQL queries.\n\n"
                f"{default_system}\n\n"
                "IMPORTANT RULES:\n"
                "1. Based on the schema and question, generate a SQL query inside ```sql ... ```\n"
                "2. Then provide a concise plain-text explanation of the results (what the data shows)\n"
                "3. Use DuckDB SQL syntax (e.g., DATE_TRUNC, EXTRACT, CORR, REGR_SLOPE)\n"
                "4. Limit results to 5000 rows unless the user asks for more\n"
                "5. Use meaningful column aliases in SQL\n"
                "6. If a chart would help visualize the answer, include chart recommendations as JSON\n"
                "7. CRITICAL: ONLY use column names that appear EXACTLY in the column list below. "
                "Do NOT invent or guess column names like 'date', 'id', 'name', 'value', 'category', etc. "
                "if they are not in the dataset.\n"
                "8. CRITICAL for chart recommendations: x_column and y_column must be REAL dataset column names from the list above. "
                "Do NOT use SQL aliases you created in your query.\n"
                "9. At the end of your answer, suggest 3 follow-up questions starting with '💡 '"
            )

            # Build user prompt with dataset context
            user_parts = []
            if dataset:
                user_parts.append(self._build_dataset_context(dataset))
            if context:
                user_parts.append(f"Additional context: {context}")
            user_parts.append(f"User question: {question}")

            if generate_charts:
                user_parts.append(
                    "\n\nAfter your SQL query, provide chart recommendations "
                    "in a JSON code block if a visualization would help answer the question. "
                    "Each chart should have: chart_type, title, x_column, "
                    "y_column (string, NOT a list), aggregation (sum/mean/count/none), description.\n"
                    "Available chart types: bar, line, scatter, pie, area, histogram, box, violin, "
                    "heatmap, sunburst, funnel, waterfall, treemap, gauge, sankey, parallel_coordinates, candlestick.\n"
                    "Example: ```json\n{\"chart_type\": \"bar\", \"title\": \"Sales by Region\", "
                    "\"x_column\": \"region\", \"y_column\": \"sales\", \"aggregation\": \"sum\"}\n```\n\n"
                    "CRITICAL: x_column and y_column MUST be the EXACT column names from the dataset schema listed above. "
                    "Do NOT use SQL aliases like 'avg_produced_energy' or 'count_report_date'. "
                    "Use the ORIGINAL column names from the dataset.\n\n"
                    "At the END of your answer, suggest 3 follow-up questions the user could ask next, "
                    "each on a new line starting with '💡 '.\n"
                    "Format like this:\n"
                    "💡 What is the trend of energy production over time?\n"
                    "💡 Which site produces the most energy on average?\n"
                    "💡 Show me a comparison of battery levels across all sites"
                )

            user_prompt = "\n\n".join(user_parts)

            messages = [
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user_prompt),
            ]

            # Get LLM response
            response = self.llm.chat(messages)
            result.answer = self._clean_answer(response.content)
            result.metadata = {
                "model": response.model,
                "provider": response.provider,
                "latency_ms": response.latency_ms,
                "usage": response.usage,
            }

            # Extract chart recommendations
            if generate_charts:
                result.charts = self._parse_chart_recommendations(response.content)

        except Exception as exc:
            result.error = str(exc)
            result.answer = f"I encountered an error processing your question: {exc}"

        # Record history
        self._history.append({
            "question": question,
            "dataset": dataset.name if dataset else None,
            "result": result.to_dict(),
        })

        return result

    def generate_sql(
        self,
        question: str,
        schema: dict[str, list[dict]],
        dialect: str = "postgresql",
    ) -> str:
        """Generate a SQL query from natural language."""
        system = SYSTEM_PROMPTS["sql_generator"]
        schema_str = json.dumps(schema, indent=2)
        prompt = (
            f"Database schema:\n{schema_str}\n\n"
            f"SQL dialect: {dialect}\n\n"
            f"Question: {question}\n\n"
            f"Generate ONLY the SQL query in a ```sql block."
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=prompt),
        ]
        response = self.llm.chat(messages)
        # Extract SQL from code block
        sql_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", response.content, re.DOTALL)
        return sql_match.group(1).strip() if sql_match else response.content.strip()

    def get_history(self) -> list[dict]:
        return self._history

    def clear_history(self) -> None:
        self._history = []
