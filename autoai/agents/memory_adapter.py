"""Adapter bridging V1 VectorMemory to V2 Memory interface.

Enables the V2 agent architecture to use V1's rich vector memory
backends (JSONFile, Chroma, Redis, Pinecone) through the
standardized V2 Memory abstract interface.
"""

from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from autoai.memory.vector import MemoryItem, VectorMemory
from autoai.memory.message_history import MessageHistory
from autoai.memory.long_term import LongTermMemory


@dataclass
class MemoryItemV2:
    """V2-compatible memory item."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    relevance_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class Memory(metaclass=ABCMeta):
    """V2 Memory abstract interface."""

    @abstractmethod
    async def add(self, item: MemoryItemV2) -> None:
        ...

    @abstractmethod
    async def get_relevant(
        self, query: str, k: int = 5, **kwargs: Any
    ) -> list[MemoryItemV2]:
        ...

    @abstractmethod
    async def discard(self, item: MemoryItemV2) -> None:
        ...

    def __iter__(self) -> Iterable[MemoryItemV2]:
        return iter([])


class VectorMemoryAdapter(Memory):
    """Adapts V1 VectorMemory to V2 Memory interface.

    All V1 sync operations are wrapped in run_in_executor
    for async compatibility.
    """

    def __init__(
        self,
        vector_memory: VectorMemory,
        long_term_memory: LongTermMemory | None = None,
    ) -> None:
        self._vector_memory = vector_memory
        self._long_term = long_term_memory

    async def add(self, item: MemoryItemV2) -> None:
        loop = asyncio.get_event_loop()
        v1_item = MemoryItem.from_text(
            item.content, "memory_adapter", config=None
        )
        await loop.run_in_executor(
            None, lambda: self._vector_memory.add(v1_item)
        )

    async def get_relevant(
        self, query: str, k: int = 5, **kwargs: Any
    ) -> list[MemoryItemV2]:
        from autoai.config import Config

        loop = asyncio.get_event_loop()
        config = kwargs.get("config") or Config()
        results = await loop.run_in_executor(
            None,
            lambda: self._vector_memory.get_relevant(query, k, config),
        )
        return [
            MemoryItemV2(
                content=r.memory_item.summary,
                metadata={
                    "raw_content": r.memory_item.raw_content,
                    "location": r.memory_item.metadata.get("location", ""),
                },
                relevance_score=r.distance,
            )
            for r in results
        ]

    async def discard(self, item: MemoryItemV2) -> None:
        loop = asyncio.get_event_loop()
        candidates = list(self._vector_memory)
        for candidate in candidates:
            if candidate.raw_content == item.content:
                await loop.run_in_executor(
                    None, lambda c=candidate: self._vector_memory.discard(c)
                )
                return

    async def search_long_term(
        self, query: str, k: int = 5
    ) -> list[str]:
        """Search long-term memory if available."""
        if self._long_term is None:
            return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._long_term.search(query, k)
        )

    async def maybe_transfer(
        self, history: MessageHistory
    ) -> None:
        """Transfer short-term to long-term memory if threshold exceeded."""
        if self._long_term is None:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: self._long_term.maybe_transfer(history)
        )
