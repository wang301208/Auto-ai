from __future__ import annotations

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class DesireType(Enum):
    CURIOSITY = "curiosity"
    MASTERY = "mastery"
    AUTONOMY = "autonomy"
    EFFICIENCY = "efficiency"
    SAFETY = "safety"
    CONNECTION = "connection"


@dataclass
class Desire:
    desire_type: DesireType
    strength: float = 0.5
    last_satisfied: float = 0.0
    satisfaction_count: int = 0
    frustration_count: int = 0

    @property
    def urgency(self) -> float:
        time_since = time.time() - self.last_satisfied
        decay = min(1.0, time_since / 3600.0)
        frustration_factor = 1.0 + self.frustration_count * 0.1
        return min(1.0, self.strength * decay * frustration_factor)

    def satisfy(self) -> None:
        self.last_satisfied = time.time()
        self.satisfaction_count += 1
        self.frustration_count = max(0, self.frustration_count - 1)

    def frustrate(self) -> None:
        self.frustration_count += 1


class DesireSystem:
    """内在驱动力系统: Agent的动机不仅仅是外部任务，还有内在欲求。"""

    def __init__(self):
        self._desires: dict[DesireType, Desire] = {}
        for dt in DesireType:
            self._desires[dt] = Desire(desire_type=dt, strength=0.5)
        self._desires[DesireType.CURIOSITY].strength = 0.7
        self._desires[DesireType.SAFETY].strength = 0.8
        self._desires[DesireType.AUTONOMY].strength = 0.6

    def get_desire(self, dtype: DesireType) -> Desire:
        return self._desires[dtype]

    def get_urgent_desires(self, threshold: float = 0.3) -> list[Desire]:
        all_desires = list(self._desires.values())
        urgent = [d for d in all_desires if d.urgency >= threshold]
        urgent.sort(key=lambda d: d.urgency, reverse=True)
        return urgent

    def satisfy(self, dtype: DesireType) -> None:
        self._desires[dtype].satisfy()

    def frustrate(self, dtype: DesireType) -> None:
        self._desires[dtype].frustrate()

    def get_motivation_vector(self) -> dict[str, float]:
        return {dt.value: d.urgency for dt, d in self._desires.items()}

    def adjust_strength(self, dtype: DesireType, delta: float) -> None:
        d = self._desires[dtype]
        d.strength = max(0.0, min(1.0, d.strength + delta))

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "desires": {dt.value: {"strength": d.strength, "urgency": d.urgency,
                                   "satisfied": d.satisfaction_count}
                        for dt, d in self._desires.items()},
            "most_urgent": max(self._desires.values(), key=lambda d: d.urgency).desire_type.value,
        }
