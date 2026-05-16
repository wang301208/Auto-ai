"""Phase xi: 统一自进化场 - 所有模块融为一个连续场。

不是独立的模块列表，而是一个连续的能量场:
- 每个模块是场中的一个激发点
- 模块间通过场势自动耦合
- 场的整体演化由能量最小化驱动
- 没有调用图，只有场梯度
"""

from autoai.evolution_field.field import EvolutionField, FieldNode, FieldState

__all__ = ["EvolutionField", "FieldNode", "FieldState"]
