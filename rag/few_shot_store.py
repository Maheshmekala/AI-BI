"""Few-Shot Store — stores successful question→SQL pairs for retrieval."""
from __future__ import annotations
import json
import hashlib
from datetime import datetime
from typing import Any


class FewShotExample:
    """A single question→SQL example for few-shot learning."""

    def __init__(
        self,
        question: str,
        sql: str,
        tables: list[str],
        explanation: str = "",
        created_at: str | None = None,
    ):
        self.question = question
        self.sql = sql
        self.tables = tables
        self.explanation = explanation
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "sql": self.sql,
            "tables": self.tables,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


class FewShotStore:
    """Store and retrieve question→SQL examples for few-shot prompting.

    Examples are stored in-memory and persisted to a JSON file.
    Retrieval is keyword-based (can be upgraded to semantic search).
    """

    def __init__(self, persist_path: str | None = None):
        self._examples: list[FewShotExample] = []
        self._persist_path = persist_path
        self._load()

    def add_example(
        self,
        question: str,
        sql: str,
        tables: list[str] | None = None,
        explanation: str = "",
    ) -> FewShotExample:
        """Store a successful query example."""
        example = FewShotExample(
            question=question,
            sql=sql,
            tables=tables or [],
            explanation=explanation,
        )
        self._examples.append(example)
        self._save()
        return example

    def search(
        self, question: str, top_k: int = 3
    ) -> list[FewShotExample]:
        """Find similar examples based on keyword overlap."""
        query_words = set(question.lower().split())

        scored = []
        for ex in self._examples:
            ex_words = set(ex.question.lower().split())
            overlap = len(query_words & ex_words)
            if overlap > 1:  # At least 2 words in common
                scored.append((overlap, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:top_k]]

    def get_prompt_context(self, question: str, top_k: int = 3) -> str:
        """Build a few-shot prompt context string."""
        examples = self.search(question, top_k)
        if not examples:
            return ""

        parts = ["\nHere are some examples of similar questions and their SQL queries:\n"]
        for i, ex in enumerate(examples, 1):
            parts.append(f"Example {i}:")
            parts.append(f"Question: {ex.question}")
            parts.append(f"SQL: {ex.sql}")
            if ex.explanation:
                parts.append(f"Explanation: {ex.explanation}")
            parts.append("")

        return "\n".join(parts)

    def remove_example(self, index: int) -> bool:
        """Remove an example by index."""
        if 0 <= index < len(self._examples):
            self._examples.pop(index)
            self._save()
            return True
        return False

    def clear(self) -> None:
        self._examples.clear()
        self._save()

    def count(self) -> int:
        return len(self._examples)

    def all_examples(self) -> list[dict[str, Any]]:
        return [ex.to_dict() for ex in self._examples]

    def _load(self) -> None:
        if not self._persist_path:
            return
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
                for item in data:
                    self._examples.append(FewShotExample(**item))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            with open(self._persist_path, "w") as f:
                json.dump([ex.to_dict() for ex in self._examples], f, indent=2)
        except Exception:
            pass
