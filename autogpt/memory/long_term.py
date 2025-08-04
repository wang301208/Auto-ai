from __future__ import annotations

from dataclasses import dataclass

from autogpt.config import Config
from autogpt.memory.message_history import MessageHistory
from autogpt.memory.vector import MemoryItem, VectorMemory


@dataclass
class LongTermMemory:
    """Manage long-term vector memories separate from MessageHistory."""

    provider: VectorMemory
    config: Config
    enabled: bool = True
    threshold: int = 10

    def add(self, text: str) -> None:
        """Add a piece of text to long-term memory."""
        if not self.enabled:
            return
        item = MemoryItem.from_text(text, "agent_history", self.config)
        self.provider.add(item)

    def search(self, query: str, k: int = 5) -> list[str]:
        """Search long-term memory for relevant items."""
        if not self.enabled:
            return []
        results = self.provider.get_relevant(query, k, self.config)
        return [r.memory_item.summary for r in results]

    def maybe_transfer(self, history: MessageHistory) -> None:
        """Move short-term summary into long-term memory when threshold exceeded."""
        if not self.enabled:
            return
        if len(history) >= self.threshold:
            self.add(history.summary)
            history.messages.clear()
            history.last_trimmed_index = 0
            history.summary = "I was created"
