from __future__ import annotations

from typing import Iterator, Sequence
from uuid import uuid4

try:
    import chromadb
except ImportError:
    chromadb = None

from autoai.config import Config
from autoai.logs import logger

from .. import MemoryItem, MemoryItemRelevance
from ..utils import get_embedding
from .base import VectorMemoryProvider


class ChromaMemory(VectorMemoryProvider):
    """由ChromaDB驱动的记忆后端。"""

    def __init__(self, config: Config) -> None:
        if chromadb is None:
            raise ImportError("chromadb未安装；请安装以使用ChromaMemory")
        persist_dir = config.workspace_path / "chroma"
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(config.memory_index)
        self._memories: dict[str, MemoryItem] = {}
        logger.debug(
            f"Initialized {self.__class__.__name__} with persist dir {persist_dir}"
        )

    def __iter__(self) -> Iterator[MemoryItem]:
        return iter(self._memories.values())

    def __contains__(self, x: MemoryItem) -> bool:
        return any(m == x for m in self._memories.values())

    def __len__(self) -> int:
        return len(self._memories)

    def add(self, item: MemoryItem) -> int:
        memory_id = str(uuid4())
        self._memories[memory_id] = item
        embedding = (
            item.e_summary.tolist()
            if hasattr(item.e_summary, "tolist")
            else list(item.e_summary)
        )
        self._collection.add(ids=[memory_id], embeddings=[embedding])
        logger.debug(f"将项添加到记忆: {item.dump()}")
        return len(self._memories)

    def discard(self, item: MemoryItem) -> None:
        remove_ids = [mid for mid, mem in self._memories.items() if mem == item]
        if not remove_ids:
            return
        self._collection.delete(ids=remove_ids)
        for mid in remove_ids:
            self._memories.pop(mid, None)

    def clear(self) -> None:
        self._collection.delete(ids=list(self._memories.keys()))
        self._memories.clear()

    def get_relevant(
        self, query: str, k: int, config: Config
    ) -> Sequence[MemoryItemRelevance]:
        if len(self._memories) == 0:
            return []
        e_query = get_embedding(query, config)
        result = self._collection.query(
            query_embeddings=[e_query],
            n_results=min(k, len(self._memories)),
        )
        ids = result.get("ids", [[]])[0]
        relevances = [
            MemoryItemRelevance.of(self._memories[mid], query, e_query)
            for mid in ids
            if mid in self._memories
        ]
        return relevances
