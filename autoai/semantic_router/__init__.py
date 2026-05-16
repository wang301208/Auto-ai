"""Phase mu: 语义路由 - 按能力寻址而非地址。

Agent不知道也不关心其他Agent在哪，只知道"谁能做什么"。
路由表由Mesh Gossip自动维护，查询走语义匹配。
"""

from autoai.semantic_router.router import SemanticRouter, CapabilityAd, RouteResult

__all__ = ["SemanticRouter", "CapabilityAd", "RouteResult"]
