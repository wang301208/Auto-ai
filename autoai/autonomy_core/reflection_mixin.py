"""自主反思混入: 为模块批量注入reflect->derive_actions->get_reflection_actions闭环基础设施。"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AutonomyReflectionMixin:
    """自主反思混入: 提供标准化的reflect->derive_actions->get_reflection_actions闭环。

    使用方法:
    1. 在类中混入: class MyModule(AutonomyReflectionMixin, ...):
    2. 调用 _record_reflection() 记录反思结果
    3. 调用 _derive_param_adjustment() 生成参数调整
    4. 调用 _derive_behavior_modification() 生成行为修改
    5. reflect() / get_reflection_actions() / get_behavior_modifications() 自动可用
    """

    def _init_reflection(self) -> None:
        self._last_reflection: Optional[dict[str, Any]] = None
        self._reflection_actions: list[dict[str, Any]] = []
        self._behavior_modifications: list[dict[str, Any]] = []
        self._param_adjustments: dict[str, float] = {}
        self._reflection_count: int = 0

    def _record_reflection(self, observation: str, quality: float, context: dict[str, Any] | None = None) -> None:
        if not hasattr(self, '_last_reflection'):
            self._init_reflection()
        self._last_reflection = {
            "observation": observation,
            "quality": quality,
            "timestamp": time.time(),
            "context": context or {},
        }
        self._reflection_count += 1
        self._derive_actions(quality, context)

    def _derive_actions(self, quality: float, context: dict[str, Any] | None = None) -> None:
        self._reflection_actions = []
        self._behavior_modifications = []
        self._param_adjustments = {}
        if quality < 0.3:
            self._behavior_modifications.append({
                "type": "conservative_mode",
                "reason": f"反思质量{quality:.2f}过低,切换保守模式",
                "priority": 1.0 - quality,
            })
            self._reflection_actions.append({"action": "reduce_risk", "urgency": "high"})
        elif quality < 0.6:
            self._behavior_modifications.append({
                "type": "moderate_adjustment",
                "reason": f"反思质量{quality:.2f}中等,适度调整",
                "priority": 0.5,
            })
            self._reflection_actions.append({"action": "incremental_improve", "urgency": "medium"})
        else:
            self._behavior_modifications.append({
                "type": "maintain_course",
                "reason": f"反思质量{quality:.2f}良好,维持方向",
                "priority": 0.1,
            })
            self._reflection_actions.append({"action": "continue", "urgency": "low"})
        if context:
            for key, value in context.items():
                if isinstance(value, (int, float)):
                    adjustment = (0.5 - value) * 0.1
                    if abs(adjustment) > 0.001:
                        self._param_adjustments[key] = adjustment

    def reflect(self) -> Optional[dict[str, Any]]:
        if not hasattr(self, '_last_reflection'):
            self._init_reflection()
        return self._last_reflection

    def get_reflection_actions(self) -> list[dict[str, Any]]:
        if not hasattr(self, '_last_reflection'):
            self._init_reflection()
        return list(self._reflection_actions)

    def get_behavior_modifications(self) -> list[dict[str, Any]]:
        if not hasattr(self, '_last_reflection'):
            self._init_reflection()
        return list(self._behavior_modifications)

    def get_param_adjustments(self) -> dict[str, float]:
        if not hasattr(self, '_last_reflection'):
            self._init_reflection()
        return dict(self._param_adjustments)

    @property
    def reflection_count(self) -> int:
        if not hasattr(self, '_last_reflection'):
            self._init_reflection()
        return self._reflection_count
