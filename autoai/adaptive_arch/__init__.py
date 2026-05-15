"""自适应架构: 运行时架构重构。

Agent的架构不是固定的，而是根据负载和性能动态调整:
- 组件热插拔: 运行时加载/卸载模块
- 拓扑重构: 改变组件间的连接关系
- 弹性伸缩: 根据负载增减实例数
- 降级容灾: 在资源不足时优雅降级
"""
from autoai.adaptive_arch.architecture import (
    AdaptiveArchitecture,
    Component,
    Topology,
)

__all__ = ["AdaptiveArchitecture", "Component", "Topology"]
