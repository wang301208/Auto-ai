"""因果推理引擎: 超越相关性，理解因果关系。

核心区分:
- 相关: A和B同时出现(可能巧合)
- 因果: A导致B出现(干预A会影响B)

实现:
- 因果图: 有向无环图(DAG)表示变量间的因果依赖
- do-演算: 模拟干预实验(P(Y|do(X)))
- 反事实推理: "如果当时做了不同的选择会怎样？"
"""
from autoai.causal_reasoning.engine import (
    CausalGraph,
    CausalNode,
    CausalEdge,
    CausalReasoner,
    InterventionResult,
)

__all__ = [
    "CausalGraph",
    "CausalNode",
    "CausalEdge",
    "CausalReasoner",
    "InterventionResult",
]
