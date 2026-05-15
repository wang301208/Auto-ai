"""全息集成器: 一个API统一访问Agent的所有能力模块。

不再需要分别导入memory/mesh/evolution/governance/...，
一个HoloAgent实例提供所有能力的统一入口。

设计哲学: Agent是一个整体，不是模块的拼凑。
"""
from autoai.holistic.agent import HoloAgent, HoloStatus

__all__ = ["HoloAgent", "HoloStatus"]
