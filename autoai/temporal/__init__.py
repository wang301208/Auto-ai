"""时间感知引擎: Agent具有时间推理能力。

不只是"现在"，Agent理解:
- 时序: 事件A先于事件B
- 紧迫度: 随时间衰减的紧迫性
- 未来模拟: 预测未来状态的时间序列
- 截止线: 软/硬deadline驱动优先级
"""
from autoai.temporal.engine import TemporalEngine, TemporalEvent, Deadline, UrgencyCurve

__all__ = ["TemporalEngine", "TemporalEvent", "Deadline", "UrgencyCurve"]
