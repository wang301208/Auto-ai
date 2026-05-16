"""Phase lambda: 混沌引擎 - Agent免疫系统与反脆弱系统。

核心哲学:
- 不防御，进化: Agent自己攻击自己，发现漏洞，修补，更强
- 反脆弱: 主动注入故障，系统在故障中变得更强
- 免疫记忆: 攻击经验成为未来防御的直觉
- 持续自攻击: 永不停止的红色团队对抗自身
"""

from autoai.chaos.immune import ImmuneSystem, AttackVector, AttackResult
from autoai.chaos.antifragile import AntiFragileEngine, FaultInjection, RecoveryReport

__all__ = [
    "ImmuneSystem", "AttackVector", "AttackResult",
    "AntiFragileEngine", "FaultInjection", "RecoveryReport",
]
