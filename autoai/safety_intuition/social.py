from __future__ import annotations

import time
import math
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ReputationLevel(Enum):
    TRUSTWORTHY = "trustworthy"
    NEUTRAL = "neutral"
    UNTRUSTWORTHY = "untrustworthy"
    BANNED = "banned"


@dataclass
class AgentReputation:
    agent_id: str
    safety_score: float = 1.0
    violation_count: int = 0
    success_count: int = 0
    last_violation: float = 0.0
    reputation: ReputationLevel = ReputationLevel.NEUTRAL

    def record_success(self) -> None:
        self.success_count += 1
        self.safety_score = min(1.0, self.safety_score + 0.01)
        self._update_reputation()

    def record_violation(self) -> None:
        self.violation_count += 1
        self.last_violation = time.time()
        self.safety_score = max(0.0, self.safety_score - 0.1)
        self._update_reputation()

    def _update_reputation(self) -> None:
        if self.safety_score >= 0.8:
            self.reputation = ReputationLevel.TRUSTWORTHY
        elif self.safety_score >= 0.5:
            self.reputation = ReputationLevel.NEUTRAL
        elif self.safety_score >= 0.2:
            self.reputation = ReputationLevel.UNTRUSTWORTHY
        else:
            self.reputation = ReputationLevel.BANNED


class SocialSafetyNorm:
    """社会安全规范：安全记录差的Agent声誉低，被拒绝协作，自然淘汰。"""

    def __init__(self):
        self._reputations: dict[str, AgentReputation] = {}
        self._collaboration_history: list[dict] = []

    def get_or_create(self, agent_id: str) -> AgentReputation:
        if agent_id not in self._reputations:
            self._reputations[agent_id] = AgentReputation(agent_id=agent_id)
        return self._reputations[agent_id]

    def record_success(self, agent_id: str) -> None:
        self.get_or_create(agent_id).record_success()

    def record_violation(self, agent_id: str) -> None:
        self.get_or_create(agent_id).record_violation()

    def can_collaborate(self, agent_a: str, agent_b: str) -> bool:
        rep_a = self.get_or_create(agent_a)
        rep_b = self.get_or_create(agent_b)
        if rep_a.reputation == ReputationLevel.BANNED or rep_b.reputation == ReputationLevel.BANNED:
            return False
        if rep_a.reputation == ReputationLevel.UNTRUSTWORTHY or rep_b.reputation == ReputationLevel.UNTRUSTWORTHY:
            return False
        return True

    def select_collaborators(self, agent_id: str, candidates: list[str], max_count: int = 5) -> list[str]:
        eligible = []
        for candidate in candidates:
            if candidate == agent_id:
                continue
            if self.can_collaborate(agent_id, candidate):
                rep = self.get_or_create(candidate)
                eligible.append((candidate, rep.safety_score))
        eligible.sort(key=lambda x: x[1], reverse=True)
        selected = [c for c, _ in eligible[:max_count]]
        if selected:
            self._collaboration_history.append({
                "initiator": agent_id,
                "selected": selected,
                "timestamp": time.time(),
            })
        return selected

    def get_evolution_pressure(self) -> dict:
        """返回社会进化压力统计：安全行为差的Agent面临淘汰压力。"""
        if not self._reputations:
            return {"total": 0, "at_risk": 0, "pressure": 0.0}
        at_risk = sum(1 for r in self._reputations.values() if r.reputation in (ReputationLevel.UNTRUSTWORTHY, ReputationLevel.BANNED))
        return {
            "total": len(self._reputations),
            "trustworthy": sum(1 for r in self._reputations.values() if r.reputation == ReputationLevel.TRUSTWORTHY),
            "at_risk": at_risk,
            "pressure": at_risk / len(self._reputations),
        }
