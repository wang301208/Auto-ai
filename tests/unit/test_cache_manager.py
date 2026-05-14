"""Tests for the CacheManager utility."""

from __future__ import annotations

from typing import Iterable, List

import pytest

from autoai.cache.cache_manager import (
    Artifact,
    CacheBackend,
    CacheManager,
    RetentionPolicy,
)


class InMemoryBackend(CacheBackend):
    """Simple in-memory cache backend for testing."""

    def __init__(self) -> None:
        self._data: List[Artifact] = []

    def save(self, artifact: Artifact) -> None:  # pragma: no cover - simple storage
        self._data.append(artifact)

    def load_all(self) -> Iterable[Artifact]:  # pragma: no cover - simple storage
        return list(self._data)

    def delete(self, artifact: Artifact) -> None:  # pragma: no cover - simple storage
        self._data = [a for a in self._data if a is not artifact]


def dummy_embedder(text: str) -> List[float]:
    """Return a deterministic embedding for ``text``."""

    mapping = {
        "write unit tests": [1.0, 0.0],
        "generate documentation": [0.0, 1.0],
        "unit tests": [1.0, 0.0],
    }
    return mapping.get(text, [0.0, 0.0])


def test_store_and_lookup_by_signature() -> None:
    backend = InMemoryBackend()
    manager = CacheManager(backend, embedding_func=dummy_embedder)

    manager.store("task1", "log", "content", {"foo": "bar"})

    results = manager.lookup_by_signature("task1")
    assert len(results) == 1
    assert results[0].content == "content"


def test_lookup_by_similarity() -> None:
    backend = InMemoryBackend()
    manager = CacheManager(backend, embedding_func=dummy_embedder)

    manager.store("write unit tests", "script", "...", {})
    manager.store("generate documentation", "script", "...", {})

    results = manager.lookup_by_similarity("unit tests", top_k=1)
    assert results[0].task_signature == "write unit tests"


def test_retention_policy_by_count() -> None:
    backend = InMemoryBackend()
    policy = RetentionPolicy(max_entries=1)
    manager = CacheManager(backend, retention=policy)

    manager.store("task1", "log", "a", {})
    manager.store("task2", "log", "b", {})

    assert not manager.lookup_by_signature("task1")
    assert manager.lookup_by_signature("task2")


def test_retention_policy_by_age() -> None:
    backend = InMemoryBackend()
    policy = RetentionPolicy(max_age_seconds=5)
    manager = CacheManager(backend, retention=policy)

    manager.store("task1", "log", "a", {})
    manager.store("task2", "log", "b", {})

    # Simulate aging of first artifact
    manager._artifacts[0].timestamp -= 10
    manager._prune()

    assert not manager.lookup_by_signature("task1")
    assert manager.lookup_by_signature("task2")

