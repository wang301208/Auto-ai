from __future__ import annotations

import time
import uuid
import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Iterator
from enum import Enum
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class AgentEventType(Enum):
    THOUGHT = "thought"
    DECISION = "decision"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SELF_MODIFY = "self_modify"
    MEMORY_OP = "memory_op"
    GOVERNANCE = "governance"
    MESH_COMM = "mesh_comm"
    EMOTION = "emotion"
    BIRTH = "birth"
    DEATH = "death"


@dataclass
class AgentEvent:
    """Agent意识流事件基类。"""
    event_type: AgentEventType
    agent_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str = ""
    correlation_id: str = ""

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "agent_id": self.agent_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "metadata": self.metadata,
            "parent_event_id": self.parent_event_id,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentEvent:
        et = data.get("event_type", "thought")
        event_type = AgentEventType(et) if isinstance(et, str) else et
        return cls(
            event_type=event_type,
            agent_id=data.get("agent_id", ""),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            event_id=data.get("event_id", uuid.uuid4().hex[:16]),
            metadata=data.get("metadata", {}),
            parent_event_id=data.get("parent_event_id", ""),
            correlation_id=data.get("correlation_id", ""),
        )


@dataclass
class ThoughtEvent(AgentEvent):
    """思考事件: Agent的推理过程。"""
    event_type: AgentEventType = field(default=AgentEventType.THOUGHT, init=False)
    reasoning_chain: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class DecisionEvent(AgentEvent):
    """决策事件: Agent的决策及理由。"""
    event_type: AgentEventType = field(default=AgentEventType.DECISION, init=False)
    decision: str = ""
    alternatives: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class ActionEvent(AgentEvent):
    """行动事件: Agent的执行及结果。"""
    event_type: AgentEventType = field(default=AgentEventType.ACTION, init=False)
    action_type: str = ""
    result: Any = None
    success: bool = True


@dataclass
class MutationEvent(AgentEvent):
    """自我修改事件: Agent修改自身的记录。"""
    event_type: AgentEventType = field(default=AgentEventType.SELF_MODIFY, init=False)
    target_file: str = ""
    patch_diff: str = ""
    test_result: bool = False


@dataclass
class EmotionEvent(AgentEvent):
    """情绪事件: Agent的置信度/挫败感/好奇心。"""
    event_type: AgentEventType = field(default=AgentEventType.EMOTION, init=False)
    emotion_type: str = ""
    intensity: float = 0.0
    trigger: str = ""


@dataclass
class EventRecord:
    """事件溯源记录: 带有不可变哈希链的持久化事件。"""
    event: AgentEvent
    sequence_number: int = 0
    previous_hash: str = ""
    record_hash: str = ""

    def compute_hash(self) -> str:
        content = f"{self.sequence_number}:{self.event.event_id}:{self.previous_hash}:{self.event.to_dict()}"
        self.record_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        return self.record_hash


class EventStream:
    """事件流: Agent完整意识流的持久化存储, 支持事件溯源与回放。"""

    def __init__(self, stream_id: str = "", persist_path: str | None = None):
        self.stream_id = stream_id or uuid.uuid4().hex[:16]
        self.persist_path = Path(persist_path) if persist_path else None
        self._events: list[EventRecord] = []
        self._last_hash = "genesis"
        self._sequence = 0
        self._by_type: dict[AgentEventType, list[EventRecord]] = defaultdict(list)
        self._by_agent: dict[str, list[EventRecord]] = defaultdict(list)

    def append(self, event: AgentEvent) -> EventRecord:
        self._sequence += 1
        record = EventRecord(
            event=event,
            sequence_number=self._sequence,
            previous_hash=self._last_hash,
        )
        record.compute_hash()
        self._last_hash = record.record_hash
        self._events.append(record)
        self._by_type[event.event_type].append(record)
        self._by_agent[event.agent_id].append(record)
        return record

    def get_events(self, since: int = 0, until: int | None = None,
                   event_type: AgentEventType | None = None,
                   agent_id: str | None = None,
                   limit: int | None = None) -> list[EventRecord]:
        records = self._events[since:until]
        if event_type:
            records = [r for r in records if r.event.event_type == event_type]
        if agent_id:
            records = [r for r in records if r.event.agent_id == agent_id]
        if limit:
            records = records[:limit]
        return records

    def get_event_at(self, sequence: int) -> EventRecord | None:
        if 0 < sequence <= len(self._events):
            return self._events[sequence - 1]
        return None

    def verify_integrity(self) -> tuple[bool, int]:
        """验证事件链完整性: 任何篡改可检测。"""
        prev_hash = "genesis"
        for i, record in enumerate(self._events):
            if record.previous_hash != prev_hash:
                return False, i + 1
            expected = hashlib.sha256(
                f"{record.sequence_number}:{record.event.event_id}:{record.previous_hash}:{record.event.to_dict()}".encode()
            ).hexdigest()[:32]
            if record.record_hash != expected:
                return False, i + 1
            prev_hash = record.record_hash
        return True, 0

    def replay(self, until: int | None = None) -> list[AgentEvent]:
        return [r.event for r in self._events[:until]]

    def snapshot_at(self, sequence: int) -> dict:
        events = self.replay(until=sequence)
        return {
            "stream_id": self.stream_id,
            "sequence": sequence,
            "events": [e.to_dict() for e in events],
            "hash": self._events[sequence - 1].record_hash if 0 < sequence <= len(self._events) else "",
        }

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def last_sequence(self) -> int:
        return self._sequence

    def get_stats(self) -> dict:
        return {
            "stream_id": self.stream_id,
            "total_events": self.total_events,
            "by_type": {t.value: len(r) for t, r in self._by_type.items()},
            "by_agent": {a: len(r) for a, r in self._by_agent.items()},
        }

    def save(self) -> None:
        if not self.persist_path:
            return
        data = {
            "stream_id": self.stream_id,
            "events": [
                {"event": r.event.to_dict(), "seq": r.sequence_number,
                 "prev_hash": r.previous_hash, "hash": r.record_hash}
                for r in self._events
            ],
        }
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.persist_path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")

    def load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            self.stream_id = data.get("stream_id", self.stream_id)
            self._events.clear()
            self._by_type.clear()
            self._by_agent.clear()
            for entry in data.get("events", []):
                event = AgentEvent.from_dict(entry["event"])
                record = EventRecord(
                    event=event,
                    sequence_number=entry["seq"],
                    previous_hash=entry.get("prev_hash", ""),
                    record_hash=entry.get("hash", ""),
                )
                self._events.append(record)
                self._by_type[event.event_type].append(record)
                self._by_agent[event.agent_id].append(record)
            if self._events:
                self._sequence = self._events[-1].sequence_number
                self._last_hash = self._events[-1].record_hash
        except Exception as e:
            logger.error(f"加载事件流失败: {e}")
