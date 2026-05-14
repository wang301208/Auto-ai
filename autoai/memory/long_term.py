from __future__ import annotations

from dataclasses import dataclass

from autoai.config import Config
from autoai.memory.message_history import MessageHistory
from autoai.memory.vector import MemoryItem, VectorMemory


@dataclass
class LongTermMemory:
    """管理与MessageHistory分离的长期向量记忆。"""

    provider: VectorMemory
    config: Config
    enabled: bool = True
    threshold: int = 10

    def add(self, text: str) -> None:
        """将一段文本添加到长期记忆。"""
        if not self.enabled:
            return
        item = MemoryItem.from_text(text, "agent_history", self.config)
        self.provider.add(item)

    def search(self, query: str, k: int = 5) -> list[str]:
        """在长期记忆中搜索相关项。"""
        if not self.enabled:
            return []
        results = self.provider.get_relevant(query, k, self.config)
        return [r.memory_item.summary for r in results]

    def maybe_transfer(self, history: MessageHistory) -> None:
        """超过阈值时将短期摘要移入长期记忆。"""
        if not self.enabled:
            return
        if len(history) >= self.threshold:
            self.add(history.summary)
            recent_count = min(3, len(history.messages))
            kept = list(history.messages[-recent_count:]) if recent_count else []
            history.messages.clear()
            history.messages.extend(kept)
            history.last_trimmed_index = 0
            history.summary = (
                f"Recent context transferred to long-term memory. "
                f"Prior summary: {history.summary[:200]}"
            )
