# sourcery skip: snake-case-functions
"""Tests for ChromaMemory class"""

from autoai.config import Config
from autoai.memory.vector import MemoryItem
from autoai.memory.vector.providers.chroma import ChromaMemory


def test_chroma_memory_add_retrieve_clear(
    config: Config, memory_item: MemoryItem, mock_get_embedding: None
) -> None:
    index = ChromaMemory(config)
    index.add(memory_item)
    results = index.get_relevant("test content", 1, config)
    assert results[0].memory_item == memory_item
    index.clear()
    assert len(index) == 0


def test_chroma_memory_discard(config: Config, memory_item: MemoryItem) -> None:
    index = ChromaMemory(config)
    index.add(memory_item)
    index.discard(memory_item)
    assert len(index) == 0
