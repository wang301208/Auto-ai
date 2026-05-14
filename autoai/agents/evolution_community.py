"""Evolution Community: Cross-agent experience exchange and collective learning.

Phase 20.3: Agents form a community for:
  - Experience broadcasting (share fix patterns across agents)
  - Collective learning (aggregate success/failure statistics)
  - Model distillation (compress community knowledge into compact rules)
  - Peer review (agents review each other's modifications)
  - Reputation tracking (successful agents gain influence)

This is the "social layer" that enables agents to learn from each other
without central coordination.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from governance.experience_store import ExperienceStore
from autoai.agents.knowledge_mesh import KnowledgeMesh, KnowledgeQuery
from autoai.agents.consensus_engine import ConsensusEngine, VoteChoice
from autoai.logs import logger


class ReviewVerdict(Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


@dataclass
class CommunityMember:
    agent_id: str
    reputation: float = 1.0
    contributions: int = 0
    successful_fixes: int = 0
    failed_fixes: int = 0
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    specializations: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.successful_fixes + self.failed_fixes
        return self.successful_fixes / total if total > 0 else 0.5


@dataclass
class PeerReview:
    review_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reviewer_id: str = ""
    target_agent_id: str = ""
    modification_id: str = ""
    verdict: ReviewVerdict = ReviewVerdict.APPROVE
    comments: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DistilledRule:
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pattern: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0
    sample_count: int = 0
    source_agents: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvolutionCommunity:
    """Community of evolving agents sharing knowledge and reviewing each other.

    Usage:
        community = EvolutionCommunity()
        community.join("a1", specializations=["python", "architecture"])
        community.join("a2", specializations=["testing", "security"])
        community.broadcast_experience("a1", "circular_import_fix", "Use lazy imports...")
        rules = community.distill_knowledge()
    """

    def __init__(
        self,
        knowledge_mesh: KnowledgeMesh | None = None,
        experience_store: ExperienceStore | None = None,
        min_reviews_for_approval: int = 2,
        reputation_boost: float = 0.1,
        reputation_decay: float = 0.99,
    ) -> None:
        self._mesh = knowledge_mesh or KnowledgeMesh()
        self._experience = experience_store or ExperienceStore()
        self._min_reviews = min_reviews_for_approval
        self._rep_boost = reputation_boost
        self._rep_decay = reputation_decay
        self._members: dict[str, CommunityMember] = {}
        self._reviews: list[PeerReview] = []
        self._distilled_rules: list[DistilledRule] = []
        self._pending_reviews: dict[str, list[PeerReview]] = defaultdict(list)
        self._broadcast_count: int = 0

    def join(self, agent_id: str, specializations: list[str] | None = None) -> None:
        if agent_id in self._members:
            return
        member = CommunityMember(
            agent_id=agent_id,
            specializations=specializations or [],
        )
        self._members[agent_id] = member
        self._mesh.register_agent(agent_id, reputation=1.0)

    def leave(self, agent_id: str) -> None:
        self._members.pop(agent_id, None)

    def record_outcome(self, agent_id: str, success: bool) -> None:
        member = self._members.get(agent_id)
        if member is None:
            return
        member.contributions += 1
        if success:
            member.successful_fixes += 1
            member.reputation = min(5.0, member.reputation + self._rep_boost)
        else:
            member.failed_fixes += 1
            member.reputation = max(0.1, member.reputation - self._rep_boost * 0.5)
        self._mesh.update_reputation(agent_id, min(1.0, member.reputation / 5.0))

    def broadcast_experience(
        self,
        author_id: str,
        pattern_name: str,
        content: str,
        topic: str = "fix_pattern",
        tags: list[str] | None = None,
    ) -> str:
        if author_id not in self._members:
            self.join(author_id)

        all_tags = (tags or []) + [pattern_name]
        fid = self._mesh.publish(
            author_id=author_id,
            title=pattern_name,
            content=content,
            topic=topic,
            tags=all_tags,
        )
        self._broadcast_count += 1
        return fid

    def query_community_knowledge(
        self,
        topic: str = "",
        tags: list[str] | None = None,
        max_results: int = 10,
    ) -> list[Any]:
        query = KnowledgeQuery(
            topic=topic,
            tags=tags or [],
            max_results=max_results,
            min_quality=0.3,
        )
        return self._mesh.query(query)

    def submit_review(
        self,
        reviewer_id: str,
        target_agent_id: str,
        modification_id: str,
        verdict: ReviewVerdict,
        comments: str = "",
    ) -> PeerReview:
        review = PeerReview(
            reviewer_id=reviewer_id,
            target_agent_id=target_agent_id,
            modification_id=modification_id,
            verdict=verdict,
            comments=comments,
        )
        self._reviews.append(review)
        self._pending_reviews[modification_id].append(review)
        return review

    def check_approval(self, modification_id: str) -> bool:
        reviews = self._pending_reviews.get(modification_id, [])
        approvals = sum(1 for r in reviews if r.verdict == ReviewVerdict.APPROVE)
        rejections = sum(1 for r in reviews if r.verdict == ReviewVerdict.REJECT)
        if rejections > approvals:
            return False
        return approvals >= self._min_reviews

    def distill_knowledge(self, min_samples: int = 3, min_success_rate: float = 0.6) -> list[DistilledRule]:
        new_rules = []

        all_fragments = self._mesh.query(KnowledgeQuery(max_results=100, min_quality=0.3))
        pattern_groups: dict[str, list[Any]] = defaultdict(list)
        for frag in all_fragments:
            for tag in frag.tags:
                pattern_groups[tag].append(frag)

        for pattern_name, fragments in pattern_groups.items():
            total = len(fragments)
            if total < min_samples:
                continue

            success_sum = sum(f.quality_score for f in fragments)
            avg_success = success_sum / total

            if avg_success >= min_success_rate:
                existing = next(
                    (r for r in self._distilled_rules if r.pattern == pattern_name),
                    None,
                )
                if existing:
                    existing.success_rate = avg_success
                    existing.sample_count = total
                    existing.source_agents = list(set(f.author_id for f in fragments))
                    continue

                rule = DistilledRule(
                    pattern=pattern_name,
                    success_rate=avg_success,
                    sample_count=total,
                    source_agents=list(set(f.author_id for f in fragments)),
                    conditions={"min_quality": min_success_rate},
                )
                new_rules.append(rule)
                self._distilled_rules.append(rule)

        if new_rules:
            logger.info(f"[EvolutionCommunity] Distilled {len(new_rules)} new rules from community knowledge")

        return new_rules

    def get_top_contributors(self, limit: int = 10) -> list[CommunityMember]:
        members = sorted(
            self._members.values(),
            key=lambda m: m.reputation * m.success_rate,
            reverse=True,
        )
        return members[:limit]

    def apply_reputation_decay(self) -> None:
        for member in self._members.values():
            member.reputation = max(0.1, member.reputation * self._rep_decay)

    @property
    def member_count(self) -> int:
        return len(self._members)

    @property
    def distilled_rule_count(self) -> int:
        return len(self._distilled_rules)

    def get_status(self) -> dict[str, Any]:
        return {
            "members": len(self._members),
            "total_reviews": len(self._reviews),
            "distilled_rules": len(self._distilled_rules),
            "broadcasts": self._broadcast_count,
            "top_contributors": [
                {"id": m.agent_id, "rep": round(m.reputation, 2), "success_rate": round(m.success_rate, 2)}
                for m in self.get_top_contributors(5)
            ],
        }


__all__ = [
    "EvolutionCommunity",
    "CommunityMember",
    "PeerReview",
    "ReviewVerdict",
    "DistilledRule",
]
