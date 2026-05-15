"""进化压力系统: Agent群体中的自然选择与适应性进化。

核心思想: 不是所有Agent都一样好。通过环境压力，
优秀的Agent策略被保留并扩散，低效的被淘汰。

机制:
- 适应度评估: 多维评估(效率/稳健性/创新/协作)
- 选择压力: 基于适应度的存活概率
- 策略遗传: 优秀Agent的策略被继承/变异/交叉
- 生态位分化: 不同Agent适应不同环境，避免同质化
"""
from autoai.evolution_pressure.fitness import (
    EvolutionPressure,
    FitnessEvaluator,
    AgentGenome,
    FitnessReport,
    NicheSpec,
)

__all__ = [
    "EvolutionPressure",
    "FitnessEvaluator",
    "AgentGenome",
    "FitnessReport",
    "NicheSpec",
]
