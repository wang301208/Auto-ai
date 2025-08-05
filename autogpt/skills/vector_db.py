from __future__ import annotations  # noqa: F401

"""Vector database provider abstraction for skill embeddings."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
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

    def clear(self) -> None:  # pragma: no cover - optional method
        """Remove all entries from the database."""
        raise NotImplementedError


class MemoryVectorDB(VectorDBProvider):
    """Simple in-memory vector database implementation."""

    def __init__(self, *_args, **_kwargs) -> None:
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

    def clear(self) -> None:
        self._index.clear()


class ChromaVectorDB(VectorDBProvider):
    """`VectorDBProvider` using a persistent ChromaDB collection."""

    def __init__(self, persist_path: Path, collection_name: str = "skills") -> None:
        self.persist_path = Path(persist_path)
        self._client = chromadb.PersistentClient(path=str(self.persist_path))
        self._collection = self._client.get_or_create_collection(collection_name)

    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        # chromadb doesn't overwrite existing ids on add, so delete first
        try:
            self._collection.delete(ids=[key])
        except Exception:
            pass
        self._collection.add(
            ids=[key], embeddings=[embedding], metadatas=[metadata or {}]
        )

    def delete(self, key: str) -> None:
        self._collection.delete(ids=[key])

    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        if top_k <= 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        dists = result.get("distances", [[]])[0]
        scores = [1.0 / (1.0 + d) for d in dists]
        return list(zip(ids, scores))

    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        result = self._collection.get(ids=[key], include=["embeddings", "metadatas"])
        if not result.get("ids"):
            return None
        embedding = result["embeddings"][0]
        metadata = result["metadatas"][0]
        return embedding, metadata

    def clear(self) -> None:
        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)
