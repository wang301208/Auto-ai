"""价值对齐动态校准: 价值函数不是静态的，而是随经验演化。

核心理念: 初始价值由人类设定(宪法层)，但价值的具体权重
和边界条件由Agent在与世界交互中动态调整。

机制:
- 宪议: 每次行动后检查是否与核心价值一致
- 校准: 根据反馈调整价值权重(不修改核心价值本身)
- 冲突解决: 当价值冲突时(效率vs安全)，动态仲裁
- 演化: 价值随时间演化(但核心价值不可变)
"""
from autoai.value_alignment.calibrator import (
    ValueCalibrator,
    Value,
    ValueJudgment,
    ValueConflict,
)

__all__ = [
    "ValueCalibrator",
    "Value",
    "ValueJudgment",
    "ValueConflict",
]
