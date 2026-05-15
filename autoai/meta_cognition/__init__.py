"""元认知控制器: Agent对自身认知过程的高阶监控与调控。

元认知 = 对认知的认知。Agent不仅仅是思考，还监控:
- 我现在用的是什么推理策略？效果如何？
- 我的注意力分配是否合理？
- 我的思维是否陷入了局部最优？
- 我是否需要切换到不同的认知模式？

这是Agent的"思维的思维" - 终极自主的核心。
"""
from autoai.meta_cognition.controller import (
    MetaCognitionController,
    CognitiveMode,
    AttentionBudget,
    ThinkingAboutThinking,
)

__all__ = [
    "MetaCognitionController",
    "CognitiveMode",
    "AttentionBudget",
    "ThinkingAboutThinking",
]
