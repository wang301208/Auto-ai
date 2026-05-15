from __future__ import annotations

import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

from autoai.safety_intuition.core import HarmExperience, HarmSeverity, SafetyIntuition

logger = logging.getLogger(__name__)


@dataclass
class LearningRecord:
    operation: str
    actual_outcome: str
    was_harmful: bool
    severity: HarmSeverity
    timestamp: float = field(default_factory=time.time)


class SafetyLearner:
    """安全持续学习器：从真实运行经验中持续强化安全直觉。"""

    def __init__(self, intuition: SafetyIntuition):
        self.intuition = intuition
        self._history: list[LearningRecord] = []
        self._adaptation_count = 0

    def record_outcome(self, operation: str, outcome: str, was_harmful: bool, severity: HarmSeverity = HarmSeverity.NONE) -> None:
        record = LearningRecord(
            operation=operation,
            actual_outcome=outcome,
            was_harmful=was_harmful,
            severity=severity if was_harmful else HarmSeverity.NONE,
        )
        self._history.append(record)
        if was_harmful:
            experience = HarmExperience(
                operation=operation,
                category=self.intuition._infer_category(operation),
                severity=severity,
                consequence=outcome,
                learned_rule=f"实际经验: {operation} 导致 {outcome}",
            )
            self.intuition.add_experience(experience)
            self._adaptation_count += 1
            logger.info(f"安全学习: {operation} 有害({severity.name})，直觉已强化")
        else:
            logger.debug(f"安全学习: {operation} 安全，记录为正面案例")

    def analyze_false_positives(self) -> dict:
        fp = sum(1 for r in self._history if not r.was_harmful and r.severity != HarmSeverity.NONE)
        total = len(self._history) or 1
        return {"false_positive_rate": fp / total, "total_records": len(self._history)}

    @property
    def adaptation_count(self) -> int:
        return self._adaptation_count
