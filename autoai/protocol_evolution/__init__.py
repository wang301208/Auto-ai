"""自主协议进化: Agent群体协商并进化其通信协议。

协议不是人类预设的，而是Agent群体通过实践涌现和进化的:
- 协商: 多Agent投票决定协议变更
- 适配: 根据通信失败率自动调整协议
- 版本: 协议有版本号，支持向后兼容
- 涌现: 新协议特性可以从实践中发现
"""
from autoai.protocol_evolution.negotiator import (
    ProtocolEvolver,
    ProtocolVersion,
    ProtocolVote,
    NegotiationRound,
)

__all__ = [
    "ProtocolEvolver",
    "ProtocolVersion",
    "ProtocolVote",
    "NegotiationRound",
]
