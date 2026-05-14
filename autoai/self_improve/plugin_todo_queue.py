"""收集缺少工具间隙的插件任务的队列."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from autoai.event_bus import EventMessage, MessageQueue

NEED_TOOL = "NEED_TOOL"


@dataclass
class PluginTodo:
    gap: str
    context: str
    goal: str


class PluginTodoQueue:
    """由JSON文件支持的插件TODO项持久队列."""

    def __init__(
        self,
        file_path: Path | str,
        message_queue: MessageQueue | None = None,
        max_queue_size: Optional[int] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.message_queue = message_queue
        self.max_queue_size = max_queue_size
        self._lock = threading.Lock()
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
        """记录给定间隙的失败，超过阈值后入队."""
        with self._lock:
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
                    self._counters[gap] = 0
                    self._save()
                    if self.message_queue:
                        self.message_queue.publish(
                            EventMessage(
                                event_type="plugin_gap",
                                payload={"gap": gap, "context": context, "goal": goal},
                                source_agent="plugin_todo_queue",
                            )
                        )
                    return
                elif is_duplicate:
                    self._counters[gap] = 0
            self._save()

    def pending(self) -> Iterable[PluginTodo]:
        with self._lock:
            return list(self._queue)

    def pop(self) -> PluginTodo | None:
        with self._lock:
            if not self._queue:
                return None
            item = self._queue.pop(0)
            self._save()
            return item
