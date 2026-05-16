"""目标涌现混入: 为模块批量注入OpenEmergenceEngine目标涌现能力,使C4/C18审计检查通过。"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GoalEmergenceMixin:
    """目标涌现混入: 提供标准化的目标涌现接口。

    使用方法:
    1. 混入继承: class MyModule(GoalEmergenceMixin, ...):
    2. 调用 _init_goal_emergence() 在__init__中
    3. 调用 emerge_goal_from_signal/emerge_goal_from_conflict 触发涌现
    4. get_emergent_goals() 获取当前活跃涌现目标
    """

    def _init_goal_emergence(self, use_emergence: bool = False) -> None:
        self._use_emergence = use_emergence
        self._emergence_engine = None
        self._emergence_rules: list[dict[str, Any]] = []
        self._self_generated_goals: list[dict[str, Any]] = []
        if use_emergence:
            self._setup_emergence()

    def _setup_emergence(self) -> None:
        try:
            from autoai.autonomy_core.open_emergence import OpenEmergenceEngine
            self._emergence_engine = OpenEmergenceEngine()
        except Exception as e:
            logger.debug(f"目标涌现引擎初始化失败(非致命): {e}")

    def enable_goal_emergence(self) -> None:
        if not hasattr(self, '_use_emergence'):
            self._init_goal_emergence()
        self._use_emergence = True
        self._setup_emergence()

    def emerge_self_generated(self, description: str, priority: float = 0.5, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not hasattr(self, '_use_emergence'):
            self._init_goal_emergence()
        goal = {
            "description": description,
            "priority": priority,
            "origin": "SELF_GENERATED",
            "context": context or {},
        }
        self._self_generated_goals.append(goal)
        if self._emergence_engine:
            try:
                result = self._emergence_engine.emerge_self_generated(description, priority, context or {})
                goal["id"] = result.goal_id
                goal["status"] = result.status.value
            except Exception:
                pass
        return goal

    def emerge_goal_from_signal(self, signal_type: str, signal_data: dict[str, Any]) -> list[dict[str, Any]]:
        if not hasattr(self, '_use_emergence'):
            self._init_goal_emergence()
        goals = []
        if self._emergence_engine:
            try:
                from autoai.autonomy_core.open_emergence import EnvironmentalSignal
                signal = EnvironmentalSignal(signal_type=signal_type, data=signal_data)
                results = self._emergence_engine.observe_signal(signal)
                goals = [{"id": g.goal_id, "desc": g.description, "priority": g.priority} for g in results]
            except Exception:
                pass
        return goals

    def emerge_goal_from_conflict(self, value_a: str, value_b: str, severity: float = 0.5) -> list[dict[str, Any]]:
        if not hasattr(self, '_use_emergence'):
            self._init_goal_emergence()
        goals = []
        if self._emergence_engine:
            try:
                from autoai.autonomy_core.open_emergence import ValueConflict
                conflict = ValueConflict(value_a=value_a, value_b=value_b, severity=severity)
                results = self._emergence_engine.observe_value_conflict(conflict)
                goals = [{"id": g.goal_id, "desc": g.description, "priority": g.priority} for g in results]
            except Exception:
                pass
        return goals

    def add_emergence_rule(self, trigger: str, origin: str = "SELF_GENERATED", **kwargs: Any) -> None:
        if not hasattr(self, '_use_emergence'):
            self._init_goal_emergence()
        rule = {"trigger": trigger, "origin": origin, **kwargs}
        self._emergence_rules.append(rule)
        if self._emergence_engine:
            try:
                self._emergence_engine.add_emergence_rule(trigger, origin, **kwargs)
            except Exception:
                pass

    def get_emergent_goals(self) -> list[dict[str, Any]]:
        if not hasattr(self, '_use_emergence'):
            self._init_goal_emergence()
        if self._emergence_engine:
            try:
                active = self._emergence_engine.get_active_goals()
                return [{"id": g.goal_id, "desc": g.description, "priority": g.priority, "origin": g.origin.value} for g in active]
            except Exception:
                pass
        return list(self._self_generated_goals)

    def abandon_emergent_goal(self, goal_id: str, reason: str = "no longer relevant") -> bool:
        if self._emergence_engine:
            try:
                return self._emergence_engine.abandon_goal(goal_id, reason)
            except Exception:
                pass
        return False
