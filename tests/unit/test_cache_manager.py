from pathlib import Path

from autogpt.cache.cache_manager import (
    CacheManager,
    DiskCacheBackend,
    SQLiteCacheBackend,
    RetentionPolicy,
)


def dummy_embedder(text: str):
    """Deterministic embedding for tests."""

    import hashlib

    h = hashlib.md5(text.encode("utf-8")).digest()
    return [float(b) for b in h[:8]]


def test_store_and_lookup_by_signature(tmp_path: Path):
    backend = DiskCacheBackend(tmp_path)
    manager = CacheManager(backend, embedding_func=dummy_embedder)
    manager.store("task1", "log", "content", {"foo": "bar"})
    results = manager.lookup_by_signature("task1")
    assert len(results) == 1
    assert results[0].content == "content"


def test_lookup_by_similarity(tmp_path: Path):
    backend = DiskCacheBackend(tmp_path)
    manager = CacheManager(backend, embedding_func=dummy_embedder)
    manager.store("write unit tests", "script", "...", {})
    manager.store("generate documentation", "script", "...", {})
    results = manager.lookup_by_similarity("unit tests", top_k=1)
    assert results[0].task_signature == "write unit tests"


def test_retention_policy_by_count(tmp_path: Path):
    backend = DiskCacheBackend(tmp_path)
    policy = RetentionPolicy(max_entries=1)
    manager = CacheManager(backend, retention=policy)
    manager.store("task1", "log", "a", {})
    manager.store("task2", "log", "b", {})
    assert not manager.lookup_by_signature("task1")
    assert manager.lookup_by_signature("task2")


def test_sqlite_backend(tmp_path: Path):
    db_path = tmp_path / "cache.db"
    backend = SQLiteCacheBackend(db_path)
    manager = CacheManager(backend)
    manager.store("task1", "log", "a", {})
    assert manager.lookup_by_signature("task1")
