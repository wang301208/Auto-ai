"""Queue to collect plugin tasks for missing tool gaps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from autogpt.event_bus import MessageQueue

NEED_TOOL = "NEED_TOOL"


@dataclass
class PluginTodo:
    gap: str
    context: str
    goal: str


class PluginTodoQueue:
    """Persistent queue for plugin TODO items backed by a JSON file."""

    def __init__(
        self,
        file_path: Path | str,
        message_queue: MessageQueue | None = None,
        max_queue_size: Optional[int] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.message_queue = message_queue
        self.max_queue_size = max_queue_size
        if not self.file_path.exists():
            self.file_path.write_text(json.dumps({"counters": {}, "queue": []}))
        self._load()

    def _load(self) -> None:
        data = json.loads(self.file_path.read_text())
        self._counters: dict[str, int] = data.get("counters", {})
        self._queue: List[PluginTodo] = [
            PluginTodo(**item) for item in data.get("queue", [])
        ]

    def _save(self) -> None:
        data = {
            "counters": self._counters,
            "queue": [todo.__dict__ for todo in self._queue],
        }
        self.file_path.write_text(json.dumps(data, indent=2))

    def record_failure(
        self, gap: str, context: str, goal: str, *, threshold: int = 3
    ) -> None:
        """Record a failure for a given gap, enqueue after threshold."""
        count = self._counters.get(gap, 0) + 1
        self._counters[gap] = count
        if count >= threshold:
            todo = PluginTodo(gap=gap, context=context, goal=goal)

            is_duplicate = todo in self._queue
            has_space = (
                self.max_queue_size is None or len(self._queue) < self.max_queue_size
            )

            if not is_duplicate and has_space:
                self._queue.append(todo)
                self._counters[gap] = 0  # reset counter after enqueue
                if self.message_queue:
                    self.message_queue.publish(
                        {
                            "type": "plugin_gap",
                            "payload": {"gap": gap, "context": context, "goal": goal},
                        }
                    )
            elif is_duplicate:
                # Already queued, reset counter but don't enqueue another
                self._counters[gap] = 0
            # else: queue is full, keep counter so we retry later
        self._save()

    def pending(self) -> Iterable[PluginTodo]:
        return list(self._queue)

    def pop(self) -> PluginTodo | None:
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._save()
        return item
