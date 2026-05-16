"""Phase nu: 自愈引擎 - Agent自己修复自己的bug。

不是等人报bug，Agent自己发现异常→定位根因→生成补丁→验证→应用。
"""

from autoai.self_heal.engine import SelfHealEngine, HealIncident, HealAction, HealOutcome

__all__ = ["SelfHealEngine", "HealIncident", "HealAction", "HealOutcome"]
