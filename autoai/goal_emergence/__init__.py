"""目标自主涌现: Agent从环境反馈/执行历史/记忆中自主发现并设定目标。

核心理念: 目标不是人类预设的，而是Agent在与世界交互中涌现的。
- 观察: 从历史中提取模式(重复失败/未探索领域/性能瓶颈)
- 欲望: 将观察转化为内在驱动力(好奇心/效率追求/稳健性需求)
- 意图: 将欲求形式化为可执行的目标并排入任务队列
"""
from autoai.goal_emergence.generator import GoalEmergenceEngine, EmergentGoal, GoalOrigin
from autoai.goal_emergence.desire import DesireSystem, Desire, DesireType

__all__ = [
    "GoalEmergenceEngine",
    "EmergentGoal",
    "GoalOrigin",
    "DesireSystem",
    "Desire",
    "DesireType",
]
