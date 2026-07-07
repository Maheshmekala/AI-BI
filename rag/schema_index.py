"""Schema Index — builds and maintains a searchable index of table schemas."""
from __future__ import annotations
import json
import hashlib
from typing import Any

from sql_engine import SqlEngine
from data_sources.base import Dataset


class SchemaIndex:
    """Index of dataset schemas for RAG retrieval.

    Stores table names, column names, types, sample values,
    null percentages, and relationships between tables.
    """

    def __init__(self, engine: SqlEngine | None = None) -> None:
        self._engine = engine or SqlEngine.get_instance()
        self._schemas: dict[str, dict[str, Any]] = {}

    def index_dataset(self, dataset: Dataset) -> dict[str, Any]:
        """Index a dataset's schema for RAG retrieval."""
        table = dataset.table_name
        cols = dataset.columns_info

        # Get sample values for each column
        sample_values = {}
        for c in cols:
            try:
                samples = self._engine.query(
                    f"SELECT DISTINCT {_qi(c['name'])} AS val "
                    f"FROM {_qi(table)} "
                    f"WHERE {_qi(c['name'])} IS NOT NULL "
                    f"LIMIT 10"
                )
                sample_values[c["name"]] = [s["val"] for s in samples]
            except Exception:
                sample_values[c["name"]] = []

        # Get column statistics
        col_stats = {}
        for c in cols:
            try:
                stats = self._engine.query(
                    f"SELECT count(*) AS total, "
                    f"count(DISTINCT {_qi(c['name'])}) AS unique_vals "
                    f"FROM {_qi(table)}"
                )
                if stats:
                    total = stats[0]["total"]
                    unique = stats[0]["unique_vals"]
                    col_stats[c["name"]] = {
                        "unique_count": unique,
                        "distinct_percentage": round(unique / max(total, 1) * 100, 1),
                    }
            except Exception:
                col_stats[c["name"]] = {}

        schema = {
            "table_name": table,
            "dataset_name": dataset.name,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "columns": [
                {
                    "name": c["name"],
                    "type": c["dtype"],
                    "nullable": c.get("nullable", True),
                    "sample_values": sample_values.get(c["name"], []),
                    "stats": col_stats.get(c["name"], {}),
                }
                for c in cols
            ],
        }

        self._schemas[table] = schema
        return schema

    def get_schema_text(self, table: str) -> str:
        """Return a human-readable schema description for LLM prompts."""
        schema = self._schemas.get(table)
        if not schema:
            return f"Table: {table} (not indexed)"

        parts = [
            f"Table: {schema['table_name']}",
            f"Description: {schema['dataset_name']} ({schema['row_count']} rows, {schema['column_count']} columns)",
            "\nColumns:",
        ]

        for col in schema["columns"]:
            nullable = "NULLABLE" if col["nullable"] else "NOT NULL"
            samples = col["sample_values"][:5]
            sample_str = f", e.g. {samples}" if samples else ""
            parts.append(f"  - {col['name']} ({col['type']}, {nullable}){sample_str}")

        return "\n".join(parts)

    def get_all_schema_text(self) -> str:
        """Return schema descriptions for all indexed tables."""
        texts = []
        for table in self._schemas:
            texts.append(self.get_schema_text(table))
        return "\n\n".join(texts)

    def search_tables(self, query: str) -> list[dict[str, Any]]:
        """Simple keyword-based table search (can be upgraded to vector search)."""
        query_lower = query.lower()
        results = []

        for table, schema in self._schemas.items():
            score = 0
            if query_lower in table.lower():
                score += 10
            if query_lower in schema["dataset_name"].lower():
                score += 5
            for col in schema["columns"]:
                if query_lower in col["name"].lower():
                    score += 3

            if score > 0:
                results.append({
                    "table": table,
                    "dataset_name": schema["dataset_name"],
                    "score": score,
                    "schema": schema,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:5]

    def get_relevant_context(self, question: str, top_k: int = 3) -> str:
        """Get the most relevant schema context for a question."""
        results = self.search_tables(question)
        if not results:
            # Return all schemas if nothing matches
            return self.get_all_schema_text()

        texts = []
        for r in results[:top_k]:
            texts.append(self.get_schema_text(r["table"]))
        return "\n\n".join(texts)

    def fingerprint(self) -> str:
        """Return a hash of the entire index for change detection."""
        raw = json.dumps(self._schemas, default=str, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def clear(self) -> None:
        self._schemas.clear()


def _qi(name: str) -> str:
    return f'"{name}"'
