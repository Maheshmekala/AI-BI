"""Retriever — retrieves relevant schema context + few-shot examples for RAG."""
from __future__ import annotations
from typing import Any

from .schema_index import SchemaIndex
from .few_shot_store import FewShotStore


class Retriever:
    """Retrieves relevant context for a user question.

    Combines schema context from SchemaIndex with
    few-shot examples from FewShotStore.
    """

    def __init__(
        self,
        schema_index: SchemaIndex | None = None,
        few_shot_store: FewShotStore | None = None,
    ):
        self.schema_index = schema_index or SchemaIndex()
        self.few_shot_store = few_shot_store or FewShotStore()

    def retrieve(self, question: str, top_k_schemas: int = 3, top_k_examples: int = 3) -> dict[str, Any]:
        """Retrieve all relevant context for a question.

        Returns:
            Dict with:
            - schema_context: str — relevant table/column descriptions
            - few_shot_context: str — similar question→SQL examples
            - tables: list[str] — table names mentioned
            - relevance_score: float — how well the context matches
        """
        schema_context = self.schema_index.get_relevant_context(question, top_k_schemas)
        few_shot_context = self.few_shot_store.get_prompt_context(question, top_k_examples)

        # Extract table names mentioned in schema context
        tables = []
        for line in schema_context.split("\n"):
            if line.startswith("Table: "):
                tables.append(line.replace("Table: ", "").strip())

        return {
            "schema_context": schema_context,
            "few_shot_context": few_shot_context,
            "tables": tables,
            "relevance_score": len(tables) / max(top_k_schemas, 1),
        }
