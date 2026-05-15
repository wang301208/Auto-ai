"""自我意识回路: Agent感知自身的认知负载、能力边界和知识缺口。

这是Agent的"内省"能力 - 不仅仅是执行任务，而是理解自己:
- 我现在认知负载是多少？需要休息/简化吗？
- 我的能力边界在哪？什么我做不了？需要学习什么？
- 我的知识缺口是什么？哪些领域我完全无知？
"""
from autoai.self_awareness.loop import (
    SelfAwarenessLoop,
    CognitiveLoad,
    CapabilityBoundary,
    KnowledgeGap,
    AwarenessSnapshot,
)

__all__ = [
    "SelfAwarenessLoop",
    "CognitiveLoad",
    "CapabilityBoundary",
    "KnowledgeGap",
    "AwarenessSnapshot",
]
