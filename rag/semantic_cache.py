"""Semantic Cache — caches question→SQL pairs for fast reuse.

If a user asks the same question (or a very similar one),
the cached SQL is returned directly without calling the LLM.
"""
from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime
from typing import Any


class SemanticCache:
    """Cache for question→SQL pairs with TTL and similarity matching.

    Uses simple n-gram overlap for similarity matching.
    Can be upgraded to vector-similarity search for better matching.
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 500):
        self._cache: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._max_entries = max_entries

    def get(self, question: str, min_similarity: float = 0.85) -> str | None:
        """Look up a cached SQL for this or a similar question.

        Args:
            question: The user's question.
            min_similarity: Minimum similarity score (0-1) to consider a hit.

        Returns:
            Cached SQL string if found, None otherwise.
        """
        self._evict_expired()

        question_lower = question.lower().strip()
        question_words = set(question_lower.split())

        best_match = None
        best_score = 0

        for key, entry in self._cache.items():
            # Check exact match first
            if key == question_lower:
                best_score = 1.0
                best_match = entry["sql"]
                break

            # Check n-gram overlap
            cached_words = set(key.split())
            if question_words and cached_words:
                overlap = len(question_words & cached_words)
                union = len(question_words | cached_words)
                score = overlap / max(union, 1)
                if score > best_score:
                    best_score = score
                    best_match = entry["sql"]

        if best_score >= min_similarity and best_match:
            # Update access time
            cache_key = question_lower if best_score == 1.0 else \
                next(k for k, v in self._cache.items() if v["sql"] == best_match)
            if cache_key in self._cache:
                self._cache[cache_key]["accessed_at"] = time.time()
                self._cache[cache_key]["access_count"] = \
                    self._cache[cache_key].get("access_count", 0) + 1
            return best_match

        return None

    def set(self, question: str, sql: str) -> None:
        """Cache a question→SQL pair."""
        self._evict_expired()

        key = question.lower().strip()

        # Evict oldest if at capacity
        if len(self._cache) >= self._max_entries:
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["created_at"])
            del self._cache[oldest_key]

        self._cache[key] = {
            "sql": sql,
            "question": question,
            "created_at": time.time(),
            "accessed_at": time.time(),
            "access_count": 0,
        }

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict[str, Any]:
        self._evict_expired()
        return {
            "size": len(self._cache),
            "max_entries": self._max_entries,
            "ttl_seconds": self._ttl,
            "total_accesses": sum(
                e.get("access_count", 0) for e in self._cache.values()
            ),
        }

    def _evict_expired(self) -> None:
        """Remove entries that have exceeded TTL."""
        now = time.time()
        expired = [
            k for k, v in self._cache.items()
            if now - v["created_at"] > self._ttl
        ]
        for k in expired:
            del self._cache[k]
