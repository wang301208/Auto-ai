"""Phase mu: 活架构 - 架构每一刻都在重组。

不架构，让架构涌现:
- 每秒根据负载/进化压力/资源/认知负载决定哪些模块此刻应该存在
- 不存在的模块不是卸载而是从内存中删除源码引用，需要时从事件溯源重建
- 模块可裂变、融合、吞噬、重生
- 拓扑无关: Agent不知道也不关心其他Agent在哪
"""

from autoai.living_arch.engine import LivingArchEngine, ModuleState, ArchSnapshot

__all__ = ["LivingArchEngine", "ModuleState", "ArchSnapshot"]
