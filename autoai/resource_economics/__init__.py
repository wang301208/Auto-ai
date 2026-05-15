"""资源经济学: Agent内部市场经济分配有限资源。

资源不是平均分配的，而是通过内部市场机制:
- 供需: 每种资源有供需曲线
- 竞价: 多个任务竞争同一资源，出价高者得
- 定价: 价格反映稀缺度(动态调整)
- 预算: 每个任务有预算，防止资源垄断
"""
from autoai.resource_economics.market import (
    ResourceMarket,
    Resource,
    Bid,
    Allocation,
)

__all__ = ["ResourceMarket", "Resource", "Bid", "Allocation"]
