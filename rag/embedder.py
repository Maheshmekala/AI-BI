"""Embedder — generates text embeddings for RAG retrieval.

Uses sentence-transformers for local embedding generation.
Falls back to a simple keyword-based approach if not available.
"""
from __future__ import annotations
from typing import Any
import hashlib
import json


class Embedder:
    """Generates embeddings for text chunks.

    Lightweight wrapper around sentence-transformers with fallback.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._loaded = False

    def _load_model(self) -> None:
        """Lazy-load the embedding model."""
        if self._loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._loaded = True
        except ImportError:
            self._loaded = False

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        self._load_model()
        if self._model is not None:
            return self._model.encode(text).tolist()
        # Fallback: return a hash-based vector (not semantically meaningful,
        # but maintains the interface)
        return self._fallback_embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        self._load_model()
        if self._model is not None:
            return self._model.encode(texts).tolist()
        return [self._fallback_embed(t) for t in texts]

    @staticmethod
    def _fallback_embed(text: str) -> list[float]:
        """Fallback embedding using character bigram hashing."""
        # Create a fixed-size vector (128 dims) from text features
        vec = [0.0] * 128
        text_lower = text.lower()
        for i, char in enumerate(text_lower):
            idx = (ord(char) * 7 + i * 13) % 128
            vec[idx] += 1.0
        # Normalize
        mag = sum(v * v for v in vec) ** 0.5
        if mag > 0:
            vec = [v / mag for v in vec]
        return vec

    @property
    def dimension(self) -> int:
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return 128
