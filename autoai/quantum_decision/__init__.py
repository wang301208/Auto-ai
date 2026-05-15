"""量子决策: 决策路径叠加与坍缩。

灵感来自量子力学:
- 叠加: 在决策前，所有可能路径同时存在(概率振幅)
- 干涉: 路径之间可以相互增强或抵消
- 坍缩: 当需要执行时，叠加态坍缩为单一决策
- 纠缠: 不同决策维度之间存在关联
"""
from autoai.quantum_decision.decider import (
    QuantumDecider,
    DecisionPath,
    Superposition,
)

__all__ = ["QuantumDecider", "DecisionPath", "Superposition"]
