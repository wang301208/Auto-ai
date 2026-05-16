"""Phase mu: 永不停歇 - Agent的持续进化主循环。

不是while True，而是永不停歇的进化:
think → act → evolve → immune → chaos → optimize → dream → reproduce
每个周期Agent都变得更强。
"""

from autoai.forever_loop.loop import ForeverLoop, CycleResult, CyclePhase

__all__ = ["ForeverLoop", "CycleResult", "CyclePhase"]
