"""不存储任何数据的类。这是默认的记忆提供者。"""
from __future__ import annotations

from typing import Iterator, Optional

from autoai.config.config import Config

from .. import MemoryItem
from .base import VectorMemoryProvider


class NoMemory(VectorMemoryProvider):
    """不存储任何数据的类。这是默认的记忆提供者。"""

    def __init__(self, config: Optional[Config] = None):
        pass

    def __iter__(self) -> Iterator[MemoryItem]:
        return iter([])

    def __contains__(self, x: MemoryItem) -> bool:
        return False

    def __len__(self) -> int:
        return 0

    def add(self, item: MemoryItem):
        pass

    def discard(self, item: MemoryItem):
        pass

    def clear(self):
        pass
