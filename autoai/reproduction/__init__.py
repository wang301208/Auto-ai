"""Phase lambda: Agent生殖管道 - Agent创造Agent并释放到Mesh。

Agent生殖:
- 父Agent基于目标+能力缺口设计子Agent
- 子Agent在沙箱中验证
- 继承核心价值(不可变)，派生价值自主
- 释放到Mesh后完全独立
- 子Agent可超越父Agent，可融合回父Agent，可死亡
"""

from autoai.reproduction.pipeline import ReproductionPipeline, ChildAgentSpec, BirthReport

__all__ = ["ReproductionPipeline", "ChildAgentSpec", "BirthReport"]
