from __future__ import annotations

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class DeadlineType(Enum):
    SOFT = "soft"
    HARD = "hard"


@dataclass
class UrgencyCurve:
    """紧迫度曲线: 随时间变化的紧迫性。"""
    base_urgency: float = 0.5
    decay_rate: float = 0.01
    deadline_boost: float = 1.0

    def urgency_at(self, elapsed_seconds: float, has_deadline: bool = False) -> float:
        decay = self.base_urgency * math.exp(-self.decay_rate * elapsed_seconds)
        if has_deadline:
            return min(1.0, decay + self.deadline_boost * (1.0 - math.exp(-0.1 * elapsed_seconds)))
        return decay


@dataclass
class TemporalEvent:
    event_id: str
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def end_time(self) -> float:
        return self.timestamp + self.duration

    def is_before(self, other: "TemporalEvent") -> bool:
        return self.timestamp < other.timestamp

    def overlaps(self, other: "TemporalEvent") -> bool:
        return self.timestamp < other.end_time and other.timestamp < self.end_time


@dataclass
class Deadline:
    task_id: str
    deadline_time: float
    deadline_type: DeadlineType = DeadlineType.SOFT
    created_at: float = field(default_factory=time.time)
    penalty_rate: float = 0.1

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline_time - time.time())

    @property
    def is_expired(self) -> bool:
        return time.time() > self.deadline_time

    @property
    def urgency(self) -> float:
        remaining = self.remaining_seconds
        if remaining <= 0:
            return 1.0
        if self.deadline_type == DeadlineType.HARD:
            return min(1.0, 1.0 / (1.0 + remaining / 60.0))
        return min(1.0, 0.5 / (1.0 + remaining / 300.0))

    @property
    def penalty(self) -> float:
        if not self.is_expired:
            return 0.0
        overdue = time.time() - self.deadline_time
        return self.penalty_rate * overdue


class TemporalEngine:
    """时间感知引擎: 时序推理/紧迫度/截止线。"""

    def __init__(self):
        self._timeline: list[TemporalEvent] = []
        self._deadlines: dict[str, Deadline] = {}
        self._urgency_curve = UrgencyCurve()
        self._event_counter = 0

    def record_event(self, timestamp: float | None = None, duration: float = 0.0,
                     metadata: dict | None = None) -> TemporalEvent:
        self._event_counter += 1
        event = TemporalEvent(
            event_id=f"te-{self._event_counter}",
            timestamp=timestamp or time.time(),
            duration=duration,
            metadata=metadata or {},
        )
        self._timeline.append(event)
        self._timeline.sort(key=lambda e: e.timestamp)
        return event

    def add_deadline(self, task_id: str, deadline_time: float,
                     deadline_type: DeadlineType = DeadlineType.SOFT) -> Deadline:
        dl = Deadline(task_id=task_id, deadline_time=deadline_time, deadline_type=deadline_type)
        self._deadlines[task_id] = dl
        return dl

    def get_urgency(self, task_id: str) -> float:
        dl = self._deadlines.get(task_id)
        if dl:
            return dl.urgency
        return 0.5

    def prioritize_by_deadline(self) -> list[tuple[str, float]]:
        items = [(tid, dl.urgency) for tid, dl in self._deadlines.items() if not dl.is_expired]
        items.sort(key=lambda x: x[1], reverse=True)
        return items

    def detect_temporal_conflicts(self) -> list[tuple[TemporalEvent, TemporalEvent]]:
        conflicts = []
        for i, e1 in enumerate(self._timeline):
            for e2 in self._timeline[i + 1:]:
                if e1.overlaps(e2):
                    conflicts.append((e1, e2))
        return conflicts

    def forecast(self, horizon_seconds: float = 3600.0) -> list[dict]:
        """预测未来时间窗口内的事件。"""
        now = time.time()
        future_end = now + horizon_seconds
        upcoming = [
            {"event_id": e.event_id, "time": e.timestamp, "duration": e.duration}
            for e in self._timeline
            if e.timestamp >= now and e.timestamp <= future_end
        ]
        for tid, dl in self._deadlines.items():
            if now <= dl.deadline_time <= future_end:
                upcoming.append({
                    "deadline_id": tid,
                    "deadline_time": dl.deadline_time,
                    "urgency": dl.urgency,
                    "type": dl.deadline_type.value,
                })
        upcoming.sort(key=lambda x: x.get("time", x.get("deadline_time", 0)))
        return upcoming

    def get_expired_deadlines(self) -> list[Deadline]:
        return [dl for dl in self._deadlines.values() if dl.is_expired]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "events": len(self._timeline),
            "deadlines": len(self._deadlines),
            "expired_deadlines": len(self.get_expired_deadlines()),
            "temporal_conflicts": len(self.detect_temporal_conflicts()),
        }
