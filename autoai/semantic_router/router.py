"""语义路由: 按能力寻址，而非地址。"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class AdStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class CapabilityAd:
    """能力广告: Agent在Mesh中广播自己能做什么。"""
    agent_id: str
    capability: str
    description: str = ""
    quality: float = 0.5
    cost: float = 0.5
    latency_ms: float = 100.0
    tags: set[str] = field(default_factory=set)
    status: AdStatus = AdStatus.ACTIVE
    advertised_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0

    @property
    def is_available(self) -> bool:
        if self.status != AdStatus.ACTIVE:
            return False
        age = time.time() - self.advertised_at
        return age < self.ttl_seconds

    @property
    def value_score(self) -> float:
        return self.quality / max(self.cost, 0.01) / max(self.latency_ms / 100.0, 0.01)


@dataclass
class RouteResult:
    """路由结果: 按能力寻址的结果。"""
    query: str
    matched_agents: list[str]
    best_agent: str = ""
    best_score: float = 0.0
    candidates_count: int = 0

    @property
    def found(self) -> bool:
        return len(self.matched_agents) > 0


class SemanticRouter:
    """语义路由器: 按能力而非地址寻址。"""

    def __init__(self):
        self._ads: dict[str, list[CapabilityAd]] = {}
        self._agent_ads: dict[str, list[CapabilityAd]] = {}
        self._route_count: int = 0
        self._cache: dict[str, RouteResult] = {}
        self._cache_ttl: float = 30.0

    def advertise(self, ad: CapabilityAd) -> None:
        """广播能力广告。"""
        cap = ad.capability.lower()
        self._ads.setdefault(cap, []).append(ad)
        self._agent_ads.setdefault(ad.agent_id, []).append(ad)
        logger.debug(f"语义路由: {ad.agent_id} 广播能力 '{ad.capability}'")

    def revoke(self, agent_id: str, capability: str | None = None) -> int:
        """撤销能力广告。"""
        count = 0
        if capability:
            cap = capability.lower()
            ads = self._ads.get(cap, [])
            for ad in ads:
                if ad.agent_id == agent_id:
                    ad.status = AdStatus.REVOKED
                    count += 1
        else:
            for ad in self._agent_ads.get(agent_id, []):
                ad.status = AdStatus.REVOKED
                count += 1
        return count

    def route(self, capability: str, min_quality: float = 0.0, max_cost: float = float("inf"), max_latency: float = float("inf")) -> RouteResult:
        """路由: 按能力寻址。"""
        self._route_count += 1
        cache_key = f"{capability}:{min_quality}:{max_cost}:{max_latency}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.candidates_count < self._cache_ttl:
                return cached
        cap = capability.lower()
        candidates = []
        direct_ads = self._ads.get(cap, [])
        for ad in direct_ads:
            if ad.is_available and ad.quality >= min_quality and ad.cost <= max_cost and ad.latency_ms <= max_latency:
                candidates.append((ad.agent_id, ad.value_score))
        if not candidates:
            for ad_cap, ads in self._ads.items():
                if ad_cap == cap:
                    continue
                sim = self._compute_similarity(cap, ad_cap)
                if sim > 0.3:
                    for ad in ads:
                        if ad.is_available and ad.quality >= min_quality and ad.cost <= max_cost:
                            score = ad.value_score * sim
                            candidates.append((ad.agent_id, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        matched = [c[0] for c in candidates[:10]]
        best = matched[0] if matched else ""
        best_score = candidates[0][1] if candidates else 0.0
        result = RouteResult(
            query=capability,
            matched_agents=matched,
            best_agent=best,
            best_score=best_score,
            candidates_count=len(candidates),
        )
        self._cache[cache_key] = result
        return result

    def _compute_similarity(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        set_a = set(a.replace("_", " ").split())
        set_b = set(b.replace("_", " ").split())
        if not set_a or not set_b:
            return 0.0
        overlap = len(set_a & set_b)
        total = len(set_a | set_b)
        return overlap / total if total > 0 else 0.0

    def discover_capabilities(self) -> dict[str, int]:
        """发现Mesh中所有可用能力。"""
        result = {}
        for cap, ads in self._ads.items():
            active = sum(1 for ad in ads if ad.is_available)
            if active > 0:
                result[cap] = active
        return result

    def agent_capabilities(self, agent_id: str) -> list[str]:
        """查询某Agent的所有能力。"""
        return [
            ad.capability for ad in self._agent_ads.get(agent_id, [])
            if ad.is_available
        ]

    def refresh(self) -> int:
        """清理过期广告。"""
        expired = 0
        for ads in self._ads.values():
            for ad in ads:
                if not ad.is_available and ad.status == AdStatus.ACTIVE:
                    ad.status = AdStatus.EXPIRED
                    expired += 1
        self._cache.clear()
        return expired

    @property
    def stats(self) -> dict[str, Any]:
        total_ads = sum(len(ads) for ads in self._ads.values())
        active_ads = sum(
            1 for ads in self._ads.values() for ad in ads if ad.is_available
        )
        return {
            "total_ads": total_ads,
            "active_ads": active_ads,
            "capability_types": len(self._ads),
            "agents_registered": len(self._agent_ads),
            "routes_performed": self._route_count,
        }
