"""世界模型: Agent维护一个内部预测模型用于反事实模拟。

Agent不仅在真实世界中行动，还在内部"模拟世界"中:
- 预测: 行动X会导致什么结果？
- 反事实: 如果当时做了Y会怎样？
- 规划: 在模拟中尝试多种方案，选最优的执行
- 学习: 对比预测vs实际，修正世界模型
"""
from autoai.world_model.model import (
    WorldModel,
    WorldState,
    Prediction,
    SimulationResult,
)

__all__ = [
    "WorldModel",
    "WorldState",
    "Prediction",
    "SimulationResult",
]
