"""开放目标涌现引擎: 突破3模板封闭，从经验/价值冲突/能力间隙中涌现新目标。"""

from __future__ import annotations

import time
import math
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class GoalOrigin(Enum):
    ROBUSTNESS = "robustness"
    CURIOSITY = "curiosity"
    EFFICIENCY = "efficiency"
    SAFETY = "safety"
    AUTONOMY = "autonomy"
    ALIGNMENT = "alignment"
    VALUE_CONFLICT = "value_conflict"
    CAPABILITY_GAP = "capability_gap"
    ENVIRONMENTAL_SIGNAL = "environmental_signal"
    SELF_GENERATED = "self_generated"


class GoalStatus(Enum):
    ACTIVE = "active"
    PURSUED = "pursued"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    EVOLVED = "evolved"


@dataclass
class EmergentGoal:
    """涌现目标: 类型不受有限枚举约束，描述自由生成。"""
    goal_id: str
    description: str
    origin: GoalOrigin
    priority: float
    status: GoalStatus = GoalStatus.ACTIVE
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    confidence: float = 0.5
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    custom_type: str = ""

    @property
    def is_active(self) -> bool:
        return self.status in (GoalStatus.ACTIVE, GoalStatus.PURSUED)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def add_evidence(self, evidence: str) -> None:
        self.evidence.append(evidence)
        self.confidence = min(1.0, 0.3 + len(self.evidence) * 0.1)


@dataclass
class EnvironmentalSignal:
    """环境信号: Agent从交互中观察到的原始信号。"""
    signal_type: str
    source: str
    intensity: float
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ValueConflict:
    """价值冲突: 两个价值维度产生矛盾，激发新目标。"""
    value_a: str
    value_b: str
    conflict_intensity: float
    resolution_hint: str = ""


@dataclass
class CapabilityGap:
    """能力间隙: 当前能力不足以满足需求，激发学习目标。"""
    required_capability: str
    current_level: float
    required_level: float
    gap: float = 0.0

    def __post_init__(self):
        self.gap = self.required_level - self.current_level


class OpenEmergenceEngine(FullAutonomyMixin):
    """开放涌现引擎: 从环境信号/价值冲突/能力间隙/经验模式中涌现新目标。"""

    def __init__(self):
        self._init_full_autonomy()
        self._goals: dict[str, EmergentGoal] = {}
        self._signals: list[EnvironmentalSignal] = []
        self._value_conflicts: list[ValueConflict] = []
        self._capability_gaps: list[CapabilityGap] = []
        self._experience_patterns: dict[str, list[dict]] = {}
        self._emergence_rules: list[dict[str, Any]] = []
        self._total_emerged: int = 0
        self._setup_emergence_rules()

    def _setup_emergence_rules(self) -> None:
        """初始涌现规则: 可被Agent自身扩展。"""
        self._emergence_rules = [
            {"trigger": "repeated_failure", "origin": GoalOrigin.ROBUSTNESS, "min_occurrences": 3},
            {"trigger": "unexplored_domain", "origin": GoalOrigin.CURIOSITY, "novelty_threshold": 0.7},
            {"trigger": "performance_degradation", "origin": GoalOrigin.EFFICIENCY, "degradation_threshold": 0.2},
            {"trigger": "value_conflict", "origin": GoalOrigin.VALUE_CONFLICT, "conflict_threshold": 0.5},
            {"trigger": "capability_gap", "origin": GoalOrigin.CAPABILITY_GAP, "gap_threshold": 0.3},
            {"trigger": "environmental_novelty", "origin": GoalOrigin.ENVIRONMENTAL_SIGNAL, "intensity_threshold": 0.6},
        ]

    def add_emergence_rule(self, trigger: str, origin: GoalOrigin, **kwargs: Any) -> None:
        """Agent可在运行时添加新的涌现规则: 开放扩展。"""
        rule = {"trigger": trigger, "origin": origin, **kwargs}
        self._emergence_rules.append(rule)
        logger.info(f"新增涌现规则: {trigger} -> {origin.value}")

    def observe_signal(self, signal: EnvironmentalSignal) -> list[EmergentGoal]:
        """观察环境信号，可能涌现新目标。"""
        self._signals.append(signal)
        if len(self._signals) > 1000:
            self._signals = self._signals[-1000:]
        new_goals = []
        if signal.intensity > 0.6:
            goal = self._emerge_from_signal(signal)
            if goal:
                new_goals.append(goal)
        recent_similar = sum(
            1 for s in self._signals[-50:]
            if s.signal_type == signal.signal_type and s.intensity > 0.5
        )
        if recent_similar >= 3:
            goal = self._emerge_pattern_goal(signal, recent_similar)
            if goal:
                new_goals.append(goal)
        return new_goals

    def observe_value_conflict(self, conflict: ValueConflict) -> list[EmergentGoal]:
        """观察价值冲突，涌现协调目标。"""
        self._value_conflicts.append(conflict)
        new_goals = []
        if conflict.conflict_intensity > 0.3:
            goal = EmergentGoal(
                goal_id=self._next_id("vc"),
                description=f"协调{conflict.value_a}与{conflict.value_b}的冲突(强度={conflict.conflict_intensity:.2f}): {conflict.resolution_hint}",
                origin=GoalOrigin.VALUE_CONFLICT,
                priority=min(0.9, 0.4 + conflict.conflict_intensity * 0.5),
                evidence=[f"冲突: {conflict.value_a} vs {conflict.value_b}"],
                confidence=conflict.conflict_intensity,
            )
            self._register_goal(goal)
            new_goals.append(goal)
        return new_goals

    def observe_capability_gap(self, gap: CapabilityGap) -> list[EmergentGoal]:
        """观察能力间隙，涌现学习目标。"""
        self._capability_gaps.append(gap)
        new_goals = []
        if gap.gap > 0.2:
            goal = EmergentGoal(
                goal_id=self._next_id("cg"),
                description=f"提升{gap.required_capability}: 当前={gap.current_level:.2f}, 需要={gap.required_level:.2f}",
                origin=GoalOrigin.CAPABILITY_GAP,
                priority=min(0.85, 0.3 + gap.gap),
                evidence=[f"能力间隙: {gap.required_capability}, gap={gap.gap:.2f}"],
                confidence=0.7,
            )
            self._register_goal(goal)
            new_goals.append(goal)
        return new_goals

    def emerge_from_experience(self, operation: str, outcome: dict[str, Any]) -> list[EmergentGoal]:
        """从经验中涌现: 非模板——分析outcome的内容动态生成目标描述。"""
        self._experience_patterns.setdefault(operation, []).append(outcome)
        if len(self._experience_patterns[operation]) > 100:
            self._experience_patterns[operation] = self._experience_patterns[operation][-100:]
        new_goals = []
        history = self._experience_patterns[operation]
        failure_rate = sum(1 for h in history if h.get("success", True) is False) / len(history)
        if failure_rate > 0.3 and len(history) >= 3:
            goal = EmergentGoal(
                goal_id=self._next_id("exp"),
                description=f"解决{operation}的持续问题: 失败率={failure_rate:.0%}, 最近{len(history)}次尝试",
                origin=GoalOrigin.ROBUSTNESS,
                priority=min(0.9, 0.4 + failure_rate * 0.5),
                evidence=[f"操作{operation}在{len(history)}次尝试中失败{int(failure_rate*len(history))}次"],
                confidence=0.6 + failure_rate * 0.3,
            )
            self._register_goal(goal)
            new_goals.append(goal)
        latency_history = [h.get("latency_ms", 0) for h in history if h.get("latency_ms")]
        if latency_history and len(latency_history) >= 5:
            recent_avg = sum(latency_history[-5:]) / 5
            older_avg = sum(latency_history[:-5]) / max(len(latency_history[:-5]), 1)
            if older_avg > 0 and recent_avg > older_avg * 1.3:
                goal = EmergentGoal(
                    goal_id=self._next_id("perf"),
                    description=f"优化{operation}的延迟: 近期={recent_avg:.0f}ms, 历史={older_avg:.0f}ms, 退化={((recent_avg/older_avg)-1)*100:.0f}%",
                    origin=GoalOrigin.EFFICIENCY,
                    priority=0.5,
                    evidence=[f"延迟退化: {recent_avg:.0f}ms vs {older_avg:.0f}ms"],
                )
                self._register_goal(goal)
                new_goals.append(goal)
        return new_goals

    def emerge_self_generated(self, description: str, priority: float, context: dict[str, Any] | None = None) -> EmergentGoal:
        """Agent自主生成目标: 无需任何触发条件，类型为SELF_GENERATED。"""
        goal = EmergentGoal(
            goal_id=self._next_id("self"),
            description=description,
            origin=GoalOrigin.SELF_GENERATED,
            priority=priority,
            confidence=0.4,
            context=context or {},
            custom_type="agent_generated",
        )
        self._register_goal(goal)
        return goal

    def evolve_goal(self, goal_id: str, new_description: str | None = None, new_priority: float | None = None) -> EmergentGoal | None:
        """演化目标: Agent可修改目标的描述和优先级。"""
        old = self._goals.get(goal_id)
        if not old:
            return None
        evolved = EmergentGoal(
            goal_id=self._next_id("evo"),
            description=new_description or old.description,
            origin=old.origin,
            priority=new_priority if new_priority is not None else old.priority,
            evidence=old.evidence.copy(),
            parent_id=old.goal_id,
            confidence=old.confidence,
            context=old.context.copy(),
        )
        old.status = GoalStatus.EVOLVED
        old.children_ids.append(evolved.goal_id)
        self._register_goal(evolved)
        return evolved

    def abandon_goal(self, goal_id: str, reason: str = "") -> bool:
        """放弃目标: Agent自主决定放弃。"""
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        goal.status = GoalStatus.ABANDONED
        goal.context["abandon_reason"] = reason
        return True

    def get_active_goals(self) -> list[EmergentGoal]:
        """获取活跃目标，按优先级排序。"""
        active = [g for g in self._goals.values() if g.is_active]
        active.sort(key=lambda g: g.priority, reverse=True)
        return active

    def _emerge_from_signal(self, signal: EnvironmentalSignal) -> EmergentGoal | None:
        desc = f"响应{signal.signal_type}信号: 来源={signal.source}, 强度={signal.intensity:.2f}"
        goal = EmergentGoal(
            goal_id=self._next_id("sig"),
            description=desc,
            origin=GoalOrigin.ENVIRONMENTAL_SIGNAL,
            priority=min(0.7, signal.intensity),
            evidence=[f"信号: {signal.signal_type}, intensity={signal.intensity:.2f}"],
            confidence=signal.intensity * 0.8,
            context=signal.context.copy(),
        )
        self._register_goal(goal)
        return goal

    def _emerge_pattern_goal(self, signal: EnvironmentalSignal, count: int) -> EmergentGoal | None:
        goal = EmergentGoal(
            goal_id=self._next_id("pat"),
            description=f"应对{signal.signal_type}的反复模式: 近50次中出现{count}次高强度信号",
            origin=GoalOrigin.SELF_GENERATED,
            priority=min(0.8, 0.3 + count * 0.1),
            evidence=[f"模式: {signal.signal_type} x{count}"],
            custom_type="pattern_response",
        )
        self._register_goal(goal)
        return goal

    def _register_goal(self, goal: EmergentGoal) -> None:
        self._goals[goal.goal_id] = goal
        self._total_emerged += 1
        logger.info(f"目标涌现: {goal.description[:60]}... (origin={goal.origin.value}, priority={goal.priority:.2f})")

    def _next_id(self, prefix: str) -> str:
        ts = f"{time.time():.6f}"
        h = hashlib.sha256(f"{prefix}{ts}{self._total_emerged}".encode()).hexdigest()[:8]
        return f"{prefix}_{h}"

    @property
    def stats(self) -> dict[str, Any]:
        active = sum(1 for g in self._goals.values() if g.is_active)
        origins = {}
        for g in self._goals.values():
            origins.setdefault(g.origin.value, 0)
            origins[g.origin.value] += 1
        return {
            "total_emerged": self._total_emerged,
            "total_goals": len(self._goals),
            "active_goals": active,
            "origins": origins,
            "emergence_rules": len(self._emergence_rules),
            "signals_observed": len(self._signals),
        }
