from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from autoai.event_sourcing.stream import EventStream, AgentEvent, EventRecord, AgentEventType

logger = logging.getLogger(__name__)


class Projection:
    """事件投影: 从事件流中提取特定维度的视图。"""

    def __init__(self, name: str, filter_fn: Callable[[AgentEvent], bool] | None = None):
        self.name = name
        self.filter_fn = filter_fn
        self._state: dict[str, Any] = {}
        self._last_sequence = 0

    def apply(self, event: AgentEvent) -> None:
        if self.filter_fn and not self.filter_fn(event):
            return
        self._update_state(event)

    def _update_state(self, event: AgentEvent) -> None:
        key = f"{event.event_type.value}:{event.agent_id}"
        self._state.setdefault(key, []).append(event.content[:200])
        self._last_sequence += 1

    @property
    def state(self) -> dict:
        return dict(self._state)


class MaterializedView:
    """物化视图: 预计算的查询优化, CQRS读模型。"""

    def __init__(self, stream: EventStream):
        self.stream = stream
        self._views: dict[str, Projection] = {}
        self._setup_default_views()

    def _setup_default_views(self) -> None:
        self._views["thoughts"] = Projection(
            "thoughts", lambda e: e.event_type == AgentEventType.THOUGHT
        )
        self._views["decisions"] = Projection(
            "decisions", lambda e: e.event_type == AgentEventType.DECISION
        )
        self._views["actions"] = Projection(
            "actions", lambda e: e.event_type == AgentEventType.ACTION
        )
        self._views["mutations"] = Projection(
            "mutations", lambda e: e.event_type == AgentEventType.SELF_MODIFY
        )
        self._views["emotions"] = Projection(
            "emotions", lambda e: e.event_type == AgentEventType.EMOTION
        )

    def rebuild_all(self, until: int | None = None) -> None:
        events = self.stream.replay(until=until)
        for view in self._views.values():
            view._state.clear()
            view._last_sequence = 0
            for event in events:
                view.apply(event)

    def query(self, view_name: str) -> dict:
        view = self._views.get(view_name)
        if not view:
            return {}
        return view.state

    def add_view(self, name: str, filter_fn: Callable[[AgentEvent], bool]) -> None:
        self._views[name] = Projection(name, filter_fn)

    def list_views(self) -> list[str]:
        return list(self._views.keys())

    def get_agent_timeline(self, agent_id: str) -> list[dict]:
        records = self.stream.get_events(agent_id=agent_id)
        return [
            {
                "seq": r.sequence_number,
                "type": r.event.event_type.value,
                "content": r.event.content[:100],
                "time": r.event.timestamp,
            }
            for r in records
        ]
