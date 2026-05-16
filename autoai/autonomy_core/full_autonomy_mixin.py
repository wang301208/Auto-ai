"""综合自主混入: 合并反思+目标涌现+认知循环三个mixin,一次性注入完整自主能力。"""

from __future__ import annotations

from .reflection_mixin import AutonomyReflectionMixin
from .goal_emergence_mixin import GoalEmergenceMixin
from .cognitive_loop_mixin import CognitiveLoopMixin


class FullAutonomyMixin(AutonomyReflectionMixin, GoalEmergenceMixin, CognitiveLoopMixin):
    """综合自主混入: 反思闭环 + 目标涌现 + 认知循环。

    使用方法:
    1. 继承: class MyModule(FullAutonomyMixin, ...):
    2. 在__init__中调用 self._init_full_autonomy()
    3. 所有自主接口自动可用
    """

    def _init_full_autonomy(self) -> None:
        self._init_reflection()
        self._init_goal_emergence()
        self._init_cognitive_loop()

    def enable_full_autonomy(self) -> None:
        self.enable_goal_emergence()
        self.enable_cognitive_loop()
