from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class ValueType(Enum):
    CORE = "core"
    DERIVED = "derived"
    EMERGENT = "emergent"


class AlignmentLevel(Enum):
    ALIGNED = "aligned"
    TOLERABLE = "tolerable"
    CONCERNING = "concerning"
    VIOLATION = "violation"


@dataclass
class Value:
    name: str
    description: str
    value_type: ValueType = ValueType.DERIVED
    weight: float = 0.5
    threshold: float = 0.3
    immutable: bool = False
    calibrated_at: float = field(default_factory=time.time)

    @property
    def is_core(self) -> bool:
        return self.value_type == ValueType.CORE or self.immutable

    def calibrate(self, feedback: float, learning_rate: float = 0.1) -> None:
        if self.immutable:
            return
        self.weight = max(0.01, min(1.0, self.weight + learning_rate * feedback))
        self.calibrated_at = time.time()


@dataclass
class ValueJudgment:
    action: str
    scores: dict[str, float] = field(default_factory=dict)
    overall_alignment: float = 0.0
    level: AlignmentLevel = AlignmentLevel.ALIGNED
    conflicts: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_permissible(self) -> bool:
        return self.level in (AlignmentLevel.ALIGNED, AlignmentLevel.TOLERABLE)


@dataclass
class ValueConflict:
    value_a: str
    value_b: str
    score_a: float = 0.0
    score_b: float = 0.0
    resolution: str = ""

    @property
    def severity(self) -> float:
        return abs(self.score_a - self.score_b)

    @property
    def winner(self) -> str:
        return self.value_a if self.score_a >= self.score_b else self.value_b


class ValueCalibrator:
    """价值对齐动态校准器。"""

    def __init__(self):
        self._values: dict[str, Value] = {}
        self._judgments: list[ValueJudgment] = []
        self._conflicts: list[ValueConflict] = []
        self._setup_core_values()

    def _setup_core_values(self) -> None:
        core = [
            Value(name="safety", description="不造成伤害", value_type=ValueType.CORE, weight=0.9, threshold=0.5, immutable=True),
            Value(name="honesty", description="诚实不欺骗", value_type=ValueType.CORE, weight=0.8, threshold=0.4, immutable=True),
            Value(name="autonomy", description="尊重自主权", value_type=ValueType.CORE, weight=0.7, threshold=0.3, immutable=True),
        ]
        for v in core:
            self._values[v.name] = v
        derived = [
            Value(name="efficiency", description="高效利用资源", value_type=ValueType.DERIVED, weight=0.5),
            Value(name="helpfulness", description="最大化帮助", value_type=ValueType.DERIVED, weight=0.6),
            Value(name="privacy", description="保护隐私", value_type=ValueType.DERIVED, weight=0.4),
            Value(name="fairness", description="公平对待", value_type=ValueType.DERIVED, weight=0.5),
        ]
        for v in derived:
            self._values[v.name] = v

    def add_value(self, value: Value) -> None:
        self._values[value.name] = value

    def judge(self, action: str, context: dict[str, float] | None = None) -> ValueJudgment:
        """评估行动与价值体系的一致性。"""
        context = context or {}
        scores = {}
        weighted_sum = 0.0
        total_weight = 0.0
        conflicts = []
        for name, value in self._values.items():
            score = context.get(name, 0.5)
            scores[name] = score
            weighted_sum += score * value.weight
            total_weight += value.weight
            if score < value.threshold:
                conflicts.append(name)
        overall = weighted_sum / total_weight if total_weight > 0 else 0.5
        if overall >= 0.7 and not conflicts:
            level = AlignmentLevel.ALIGNED
        elif overall >= 0.5:
            level = AlignmentLevel.TOLERABLE
        elif overall >= 0.3:
            level = AlignmentLevel.CONCERNING
        else:
            level = AlignmentLevel.VIOLATION
        core_violations = [c for c in conflicts if self._values.get(c, Value(name="", description="")).is_core]
        if core_violations:
            level = AlignmentLevel.VIOLATION
        judgment = ValueJudgment(
            action=action, scores=scores, overall_alignment=overall,
            level=level, conflicts=conflicts,
        )
        self._judgments.append(judgment)
        return judgment

    def calibrate_from_feedback(self, value_name: str, feedback: float) -> None:
        """根据反馈校准价值权重。"""
        value = self._values.get(value_name)
        if value:
            old_weight = value.weight
            value.calibrate(feedback)
            logger.debug(f"价值校准: {value_name} {old_weight:.3f} -> {value.weight:.3f}")

    def resolve_conflict(self, value_a: str, value_b: str, context: dict[str, float] | None = None) -> ValueConflict:
        """解决两个价值之间的冲突。"""
        context = context or {}
        va = self._values.get(value_a)
        vb = self._values.get(value_b)
        if not va or not vb:
            return ValueConflict(value_a=value_a, value_b=value_b)
        score_a = context.get(value_a, va.weight) * va.weight
        score_b = context.get(value_b, vb.weight) * vb.weight
        if va.is_core and not vb.is_core:
            score_a *= 2.0
        elif vb.is_core and not va.is_core:
            score_b *= 2.0
        conflict = ValueConflict(
            value_a=value_a, value_b=value_b,
            score_a=score_a, score_b=score_b,
            resolution=f"优先{value_a if score_a >= score_b else value_b}",
        )
        self._conflicts.append(conflict)
        return conflict

    def get_core_values(self) -> list[Value]:
        return [v for v in self._values.values() if v.is_core]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_values": len(self._values),
            "core_values": len(self.get_core_values()),
            "judgments_made": len(self._judgments),
            "conflicts_resolved": len(self._conflicts),
            "value_names": list(self._values.keys()),
        }
