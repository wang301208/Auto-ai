"""自举启动器: 从最小内核自举出完整Agent。

哲学: 一个完整的Agent应该能够从最小可运行的内核开始，
通过自我改进逐步自举出所有能力。就像生物学中，
一个单细胞可以发育成完整的多细胞生物体。

自举阶段:
1. 种子: 最小内核(推理+记忆+行动)
2. 发芽: 发现第一个改进机会并实施
3. 生长: 递归自我改进，每次改进都扩展能力
4. 成熟: 达到稳定状态，具备完整能力集
5. 繁殖: 创建子Agent(可选)
"""
from autoai.bootstrap.bootstrapper import (
    SelfBootstrapper,
    BootstrapPhase,
    BootstrapReport,
    Seed,
)

__all__ = [
    "SelfBootstrapper",
    "BootstrapPhase",
    "BootstrapReport",
    "Seed",
]
