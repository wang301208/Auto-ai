from __future__ import annotations  # noqa: F401

"""Vector database provider abstraction for skill embeddings."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import numpy as np

Embedding = List[float]


class VectorDBProvider(ABC):
    """Abstract interface for a vector database."""

    @abstractmethod
    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        """Store an embedding with optional metadata."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove an embedding from the index."""

    @abstractmethod
    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        """Return the ``top_k`` most similar keys to the given embedding."""

    @abstractmethod
    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        """Return the stored embedding and metadata for ``key`` if present."""


class MemoryVectorDB(VectorDBProvider):
    """Simple in-memory vector database implementation."""

    def __init__(self) -> None:
        self._index: Dict[str, Tuple[Embedding, Dict]] = {}

    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        self._index[key] = (embedding, metadata or {})

    def delete(self, key: str) -> None:
        self._index.pop(key, None)

    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        if not self._index:
            return []

        query_vec = np.array(embedding)
        results: List[Tuple[str, float]] = []
        for key, (vec, _) in self._index.items():
            stored_vec = np.array(vec)
            # cosine similarity
            score = float(
                np.dot(query_vec, stored_vec)
                / (np.linalg.norm(query_vec) * np.linalg.norm(stored_vec) + 1e-10)
            )
            results.append((key, score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        return self._index.get(key)
