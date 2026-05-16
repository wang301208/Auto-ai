from __future__ import annotations

import time
import hashlib
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

from autoai.autonomy_core.open_emergence import OpenEmergenceEngine as _OpenEmergenceEngine
from autoai.autonomy_core.open_emergence import EmergentGoal as _OEEGoal
from autoai.autonomy_core.open_emergence import GoalOrigin as _OEGoalOrigin
from autoai.autonomy_core.open_emergence import EnvironmentalSignal, ValueConflict as _OEValueConflict, CapabilityGap
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class GoalOrigin(Enum):
    CURIOSITY = "curiosity"
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"
    COMPLETENESS = "completeness"
    SELF_IMPROVE = "self_improve"
    SOCIAL = "social"
    SELF_GENERATED = "self_generated"
    VALUE_CONFLICT = "value_conflict"
    CAPABILITY_GAP = "capability_gap"
    ENVIRONMENTAL_SIGNAL = "environmental_signal"


class GoalState(Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    PURSUING = "pursuing"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


@dataclass
class EmergentGoal:
    description: str
    origin: GoalOrigin
    priority: float = 0.5
    state: GoalState = GoalState.DORMANT
    created_at: float = field(default_factory=time.time)
    evidence: list[str] = field(default_factory=list)
    sub_goals: list[str] = field(default_factory=list)
    progress: float = 0.0
    _id: str = ""

    def __post_init__(self):
        if not self._id:
            raw = f"{self.description}:{self.origin.value}:{self.created_at}"
            self._id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def is_achievable(self) -> bool:
        return self.priority >= 0.1 and self.state in (GoalState.DORMANT, GoalState.ACTIVE)

    def activate(self) -> None:
        if self.state == GoalState.DORMANT:
            self.state = GoalState.ACTIVE

    def start_pursuing(self) -> None:
        if self.state == GoalState.ACTIVE:
            self.state = GoalState.PURSUING

    def mark_achieved(self) -> None:
        self.state = GoalState.ACHIEVED
        self.progress = 1.0

    def abandon(self, reason: str = "") -> None:
        self.state = GoalState.ABANDONED
        if reason:
            self.evidence.append(f"abandoned: {reason}")


class ObservationPattern:
    """从执行历史中提取的模式。"""

    def __init__(self):
        self._failure_counts: dict[str, int] = {}
        self._success_counts: dict[str, int] = {}
        self._unexplored_areas: set[str] = set()
        self._performance_bottlenecks: list[tuple[str, float]] = []

    def record_outcome(self, operation: str, success: bool, duration_ms: float = 0) -> None:
        if success:
            self._success_counts[operation] = self._success_counts.get(operation, 0) + 1
        else:
            self._failure_counts[operation] = self._failure_counts.get(operation, 0) + 1
        if duration_ms > 1000:
            self._performance_bottlenecks.append((operation, duration_ms))

    def mark_unexplored(self, area: str) -> None:
        self._unexplored_areas.add(area)

    def find_patterns(self) -> list[dict]:
        patterns = []
        for op, count in self._failure_counts.items():
            if count >= 3:
                total = count + self._success_counts.get(op, 0)
                rate = count / total if total > 0 else 1.0
                patterns.append({
                    "type": "repeated_failure",
                    "operation": op,
                    "failure_rate": rate,
                    "count": count,
                })
        for area in self._unexplored_areas:
            patterns.append({"type": "unexplored", "area": area})
        if self._performance_bottlenecks:
            by_op: dict[str, list[float]] = {}
            for op, dur in self._performance_bottlenecks:
                by_op.setdefault(op, []).append(dur)
            for op, durs in by_op.items():
                avg = sum(durs) / len(durs)
                if avg > 2000:
                    patterns.append({
                        "type": "performance_bottleneck",
                        "operation": op,
                        "avg_duration_ms": avg,
                    })
        return patterns


class GoalEmergenceEngine(FullAutonomyMixin):
    """目标自主涌现引擎: 观察->欲求->意图。"""

    def __init__(self, agent_id: str = "emergent", use_open_emergence: bool = False):
        self._init_full_autonomy()
        self.agent_id = agent_id
        self._observer = ObservationPattern()
        self._goals: list[EmergentGoal] = []
        self._goal_index: dict[str, EmergentGoal] = {}
        self._generation_count = 0
        self._use_open_emergence = use_open_emergence
        self._open_engine: _OpenEmergenceEngine | None = None
        if use_open_emergence:
            self._open_engine = _OpenEmergenceEngine()

    def enable_open_emergence(self) -> None:
        """运行时启用开放涌现引擎。"""
        if not self._use_open_emergence:
            self._use_open_emergence = True
            self._open_engine = _OpenEmergenceEngine()

    def emerge_self_generated(self, description: str, priority: float, context: dict[str, Any] | None = None) -> EmergentGoal | None:
        """Agent自主生成目标: 突破3模板封闭，无需任何触发条件。"""
        if not self._use_open_emergence or not self._open_engine:
            return None
        oe_goal = self._open_engine.emerge_self_generated(description, priority, context)
        goal = EmergentGoal(
            description=oe_goal.description,
            origin=GoalOrigin.SELF_GENERATED,
            priority=oe_goal.priority,
            state=GoalState.ACTIVE,
            evidence=oe_goal.evidence,
        )
        self._goals.append(goal)
        self._goal_index[goal._id] = goal
        return goal

    def observe_environmental_signal(self, signal_type: str, source: str, intensity: float, context: dict[str, Any] | None = None) -> list[EmergentGoal]:
        """观察环境信号，通过开放引擎涌现新目标。"""
        if not self._use_open_emergence or not self._open_engine:
            return []
        signal = EnvironmentalSignal(signal_type=signal_type, source=source, intensity=intensity, context=context or {})
        oe_goals = self._open_engine.observe_signal(signal)
        new_goals = []
        for oe_goal in oe_goals:
            origin_map = {
                _OEGoalOrigin.ENVIRONMENTAL_SIGNAL: GoalOrigin.ENVIRONMENTAL_SIGNAL,
                _OEGoalOrigin.SELF_GENERATED: GoalOrigin.SELF_GENERATED,
                _OEGoalOrigin.CURIOSITY: GoalOrigin.CURIOSITY,
                _OEGoalOrigin.ROBUSTNESS: GoalOrigin.ROBUSTNESS,
                _OEGoalOrigin.EFFICIENCY: GoalOrigin.EFFICIENCY,
            }
            origin = origin_map.get(oe_goal.origin, GoalOrigin.SELF_GENERATED)
            goal = EmergentGoal(description=oe_goal.description, origin=origin, priority=oe_goal.priority, state=GoalState.ACTIVE, evidence=oe_goal.evidence)
            if goal._id not in self._goal_index:
                self._goals.append(goal)
                self._goal_index[goal._id] = goal
                new_goals.append(goal)
        return new_goals

    def observe_value_conflict(self, value_a: str, value_b: str, conflict_intensity: float, resolution_hint: str = "") -> list[EmergentGoal]:
        """观察价值冲突，涌现协调目标。"""
        if not self._use_open_emergence or not self._open_engine:
            return []
        conflict = _OEValueConflict(value_a=value_a, value_b=value_b, conflict_intensity=conflict_intensity, resolution_hint=resolution_hint)
        oe_goals = self._open_engine.observe_value_conflict(conflict)
        new_goals = []
        for oe_goal in oe_goals:
            goal = EmergentGoal(description=oe_goal.description, origin=GoalOrigin.VALUE_CONFLICT, priority=oe_goal.priority, state=GoalState.ACTIVE, evidence=oe_goal.evidence)
            if goal._id not in self._goal_index:
                self._goals.append(goal)
                self._goal_index[goal._id] = goal
                new_goals.append(goal)
        return new_goals

    def observe_capability_gap(self, required_capability: str, current_level: float, required_level: float) -> list[EmergentGoal]:
        """观察能力间隙，涌现学习目标。"""
        if not self._use_open_emergence or not self._open_engine:
            return []
        gap = CapabilityGap(required_capability=required_capability, current_level=current_level, required_level=required_level)
        oe_goals = self._open_engine.observe_capability_gap(gap)
        new_goals = []
        for oe_goal in oe_goals:
            goal = EmergentGoal(description=oe_goal.description, origin=GoalOrigin.CAPABILITY_GAP, priority=oe_goal.priority, state=GoalState.ACTIVE, evidence=oe_goal.evidence)
            if goal._id not in self._goal_index:
                self._goals.append(goal)
                self._goal_index[goal._id] = goal
                new_goals.append(goal)
        return new_goals

    def add_emergence_rule(self, trigger: str, origin: GoalOrigin, **kwargs: Any) -> None:
        """Agent可在运行时添加新的涌现规则: 开放扩展。"""
        if not self._use_open_emergence or not self._open_engine:
            return
        oe_origin_map = {
            GoalOrigin.CURIOSITY: _OEGoalOrigin.CURIOSITY,
            GoalOrigin.EFFICIENCY: _OEGoalOrigin.EFFICIENCY,
            GoalOrigin.ROBUSTNESS: _OEGoalOrigin.ROBUSTNESS,
            GoalOrigin.SELF_GENERATED: _OEGoalOrigin.SELF_GENERATED,
            GoalOrigin.VALUE_CONFLICT: _OEGoalOrigin.VALUE_CONFLICT,
            GoalOrigin.CAPABILITY_GAP: _OEGoalOrigin.CAPABILITY_GAP,
            GoalOrigin.ENVIRONMENTAL_SIGNAL: _OEGoalOrigin.ENVIRONMENTAL_SIGNAL,
        }
        oe_origin = oe_origin_map.get(origin, _OEGoalOrigin.SELF_GENERATED)
        self._open_engine.add_emergence_rule(trigger, oe_origin, **kwargs)

    def observe_outcome(self, operation: str, success: bool, duration_ms: float = 0) -> None:
        self._observer.record_outcome(operation, success, duration_ms)

    def observe_unexplored(self, area: str) -> None:
        self._observer.mark_unexplored(area)

    def emerge_goals(self) -> list[EmergentGoal]:
        """从当前观察中涌现新目标。"""
        patterns = self._observer.find_patterns()
        new_goals = []
        for pattern in patterns:
            goal = self._pattern_to_goal(pattern)
            if goal and goal._id not in self._goal_index:
                self._goals.append(goal)
                self._goal_index[goal._id] = goal
                new_goals.append(goal)
                logger.info(f"目标涌现: [{goal.origin.value}] {goal.description}")
        self._generation_count += 1
        return new_goals

    def _pattern_to_goal(self, pattern: dict) -> Optional[EmergentGoal]:
        ptype = pattern.get("type")
        if ptype == "repeated_failure":
            op = pattern["operation"]
            rate = pattern["failure_rate"]
            return EmergentGoal(
                description=f"解决{op}的重复失败(失败率{rate:.0%})",
                origin=GoalOrigin.ROBUSTNESS,
                priority=min(0.9, 0.3 + rate * 0.6),
                evidence=[f"操作{op}失败{pattern['count']}次"],
            )
        elif ptype == "unexplored":
            area = pattern["area"]
            return EmergentGoal(
                description=f"探索未知领域: {area}",
                origin=GoalOrigin.CURIOSITY,
                priority=0.4,
                evidence=[f"从未执行过{area}相关操作"],
            )
        elif ptype == "performance_bottleneck":
            op = pattern["operation"]
            avg = pattern["avg_duration_ms"]
            return EmergentGoal(
                description=f"优化{op}的性能(平均{avg:.0f}ms)",
                origin=GoalOrigin.EFFICIENCY,
                priority=min(0.8, 0.3 + avg / 10000),
                evidence=[f"平均执行时长{avg:.0f}ms"],
            )
        return None

    def get_active_goals(self) -> list[EmergentGoal]:
        return [g for g in self._goals if g.state in (GoalState.ACTIVE, GoalState.PURSUING)]

    def get_all_goals(self) -> list[EmergentGoal]:
        return list(self._goals)

    def prioritize(self) -> list[EmergentGoal]:
        active = self.get_active_goals()
        active.sort(key=lambda g: g.priority, reverse=True)
        return active

    def update_progress(self, goal_id: str, progress: float) -> None:
        goal = self._goal_index.get(goal_id)
        if goal:
            goal.progress = min(1.0, max(0.0, progress))
            if goal.progress >= 1.0:
                goal.mark_achieved()

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "generation_count": self._generation_count,
            "total_goals": len(self._goals),
            "active_goals": len(self.get_active_goals()),
            "achieved_goals": len([g for g in self._goals if g.state == GoalState.ACHIEVED]),
            "abandoned_goals": len([g for g in self._goals if g.state == GoalState.ABANDONED]),
        }
