"""信念修正系统: 基于AGM公理的信念修正与认知逻辑。

核心能力:
- 信念集一致性维护 (AGM理论)
- 信念收缩 (contraction): 移除信念时保持最大一致子集
- 信念修订 (revision): 纳入新信念时解决冲突
- 认知逻辑 (doxastic): B(p) = Agent相信p
- 条件信念: B(p|q) = 在q条件下相信p
- 信念强度与来源追踪
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class BeliefSource(Enum):
    PERCEPTION = "perception"
    INFERENCE = "inference"
    COMMUNICATION = "communication"
    INTROSPECTION = "introspection"
    AXIOM = "axiom"
    DEFAULT = "default"


class RevisionStrategy(Enum):
    CONSERVATIVE = "conservative"
    RADICAL = "radical"
    PRIORITIZED = "prioritized"
    LEVI = "levi"


@dataclass
class Belief:
    """信念: Agent对某命题的置信。"""
    belief_id: str
    proposition: str
    confidence: float = 1.0
    source: BeliefSource = BeliefSource.DEFAULT
    dependencies: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    revision_count: int = 0
    evidence_for: int = 0
    evidence_against: int = 0
    priority: float = 0.5

    @property
    def net_evidence(self) -> int:
        return self.evidence_for - self.evidence_against

    @property
    def is_strong(self) -> bool:
        return self.confidence >= 0.8

    @property
    def is_weak(self) -> bool:
        return self.confidence <= 0.2

    @property
    def is_axiom(self) -> bool:
        return self.source == BeliefSource.AXIOM

    def add_evidence(self, supports: bool, weight: int = 1) -> None:
        if supports:
            self.evidence_for += weight
        else:
            self.evidence_against += weight
        total = self.evidence_for + self.evidence_against
        if total > 0:
            self.confidence = self.evidence_for / total
        self.updated_at = time.time()


@dataclass
class BeliefRevision:
    """信念修订记录。"""
    revision_id: str
    old_belief: Belief | None
    new_belief: Belief
    trigger: str
    strategy: RevisionStrategy = RevisionStrategy.CONSERVATIVE
    consistency_preserved: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConditionalBelief:
    """条件信念: B(proposition | condition)。"""
    proposition: str
    condition: str
    confidence: float = 0.5
    belief_id: str = ""

    @property
    def full_proposition(self) -> str:
        return f"B({self.proposition} | {self.condition})"


class BeliefSystem:
    """信念系统: 维护Agent的信念集，支持AGM式修正。"""

    def __init__(self, agent_id: str = "default"):
        self._agent_id = agent_id
        self._beliefs: dict[str, Belief] = {}
        self._conditional_beliefs: list[ConditionalBelief] = []
        self._revisions: list[BeliefRevision] = []
        self._entailment_rules: list[tuple[str, str]] = []
        self._revision_strategy: RevisionStrategy = RevisionStrategy.PRIORITIZED
        self._consistency_checks: int = 0
        self._inconsistencies_found: int = 0

    def add_axiom(self, proposition: str) -> Belief:
        """添加公理(不可修订的信念)。"""
        return self._add_belief(proposition, BeliefSource.AXIOM, confidence=1.0, priority=1.0)

    def _add_belief(
        self,
        proposition: str,
        source: BeliefSource = BeliefSource.DEFAULT,
        confidence: float = 1.0,
        dependencies: list[str] | None = None,
        priority: float = 0.5,
        force_confidence: bool = False,
    ) -> Belief:
        belief_id = f"b_{abs(hash(proposition)) % 100000}"
        if belief_id in self._beliefs:
            existing = self._beliefs[belief_id]
            if existing.source == BeliefSource.AXIOM and not force_confidence:
                return existing
            if force_confidence or confidence > existing.confidence:
                existing.confidence = confidence
                existing.source = source
                existing.updated_at = time.time()
                existing.revision_count += 1
            return existing
        belief = Belief(
            belief_id=belief_id,
            proposition=proposition,
            confidence=confidence,
            source=source,
            dependencies=dependencies or [],
            priority=priority,
        )
        self._beliefs[belief_id] = belief
        return belief

    def believe(
        self,
        proposition: str,
        source: BeliefSource = BeliefSource.PERCEPTION,
        confidence: float = 1.0,
    ) -> Belief:
        """相信一个命题(带一致性检查)。"""
        negation = self._negation(proposition)
        neg_belief = self._find_by_proposition(negation)
        if neg_belief and neg_belief.is_axiom:
            logger.warning(f"信念系统: 无法相信'{proposition}'，否定是公理")
            return neg_belief
        if neg_belief and confidence > neg_belief.confidence:
            self._remove_belief(neg_belief.belief_id)
        return self._add_belief(proposition, source, confidence)

    def _remove_belief(self, belief_id: str) -> None:
        """直接移除信念(不经过contract的修订记录)。"""
        if belief_id in self._beliefs:
            del self._beliefs[belief_id]

    def _negation(self, proposition: str) -> str:
        if proposition.startswith("not_"):
            return proposition[4:]
        return f"not_{proposition}"

    def _find_by_proposition(self, proposition: str) -> Belief | None:
        for b in self._beliefs.values():
            if b.proposition == proposition:
                return b
        return None

    def contract(self, proposition: str) -> bool:
        """收缩: 从信念集中移除一个命题。"""
        belief = self._find_by_proposition(proposition)
        if not belief:
            return False
        if belief.is_axiom:
            logger.warning(f"信念系统: 无法收缩公理 '{proposition}'")
            return False
        revision = BeliefRevision(
            revision_id=f"rev_{len(self._revisions)}",
            old_belief=belief,
            new_belief=Belief(
                belief_id=belief.belief_id,
                proposition=proposition,
                confidence=0.0,
                source=belief.source,
            ),
            trigger="contraction",
            strategy=self._revision_strategy,
        )
        self._revisions.append(revision)
        del self._beliefs[belief.belief_id]
        deps_to_check = [
            b for b in self._beliefs.values()
            if belief.belief_id in b.dependencies
        ]
        for dep in deps_to_check:
            dep.dependencies.remove(belief.belief_id)
            dep.confidence *= 0.7
        return True

    def revise(self, proposition: str, confidence: float, source: BeliefSource = BeliefSource.INFERENCE) -> Belief:
        """修订: 纳入新信念(AGM revision)。"""
        negation = self._negation(proposition)
        neg_belief = self._find_by_proposition(negation)
        old_belief = self._find_by_proposition(proposition)
        if neg_belief:
            self.contract(negation)
        strategy = self._revision_strategy
        if strategy == RevisionStrategy.RADICAL:
            final_confidence = confidence
        elif strategy == RevisionStrategy.CONSERVATIVE:
            if old_belief:
                final_confidence = (old_belief.confidence + confidence) / 2
            else:
                final_confidence = confidence * 0.8
        elif strategy == RevisionStrategy.PRIORITIZED:
            if old_belief:
                if source == BeliefSource.AXIOM:
                    final_confidence = confidence
                elif old_belief.source == BeliefSource.AXIOM:
                    final_confidence = old_belief.confidence
                else:
                    w_old = old_belief.priority
                    w_new = 1.0 - old_belief.priority
                    final_confidence = (w_old * old_belief.confidence + w_new * confidence) / (w_old + w_new)
            else:
                final_confidence = confidence
        else:
            final_confidence = confidence
        new_belief = self._add_belief(proposition, source, final_confidence, force_confidence=True)
        revision = BeliefRevision(
            revision_id=f"rev_{len(self._revisions)}",
            old_belief=old_belief,
            new_belief=new_belief,
            trigger="revision",
            strategy=strategy,
        )
        self._revisions.append(revision)
        return new_belief

    def check_consistency(self) -> list[tuple[Belief, Belief]]:
        """检查信念一致性。"""
        self._consistency_checks += 1
        inconsistencies = []
        beliefs = list(self._beliefs.values())
        for i, b1 in enumerate(beliefs):
            for b2 in beliefs[i + 1:]:
                if self._are_contradictory(b1, b2):
                    inconsistencies.append((b1, b2))
                    self._inconsistencies_found += 1
        return inconsistencies

    def _are_contradictory(self, b1: Belief, b2: Belief) -> bool:
        neg = self._negation(b1.proposition)
        if b2.proposition == neg:
            return b1.confidence > 0.5 and b2.confidence > 0.5
        return False

    def resolve_inconsistency(self, b1: Belief, b2: Belief) -> Belief | None:
        """解决不一致: 保留优先级高的信念。"""
        if b1.is_axiom and not b2.is_axiom:
            self.contract(b2.proposition)
            return b1
        if b2.is_axiom and not b1.is_axiom:
            self.contract(b1.proposition)
            return b2
        if b1.confidence * b1.priority >= b2.confidence * b2.priority:
            self.revise(b2.proposition, b2.confidence * 0.3, b2.source)
            return b1
        else:
            self.revise(b1.proposition, b1.confidence * 0.3, b1.source)
            return b2

    def add_entailment(self, antecedent: str, consequent: str) -> None:
        """添加推导规则: antecedent => consequent。"""
        self._entailment_rules.append((antecedent, consequent))

    def deduce(self) -> list[Belief]:
        """基于推导规则推导新信念。"""
        deduced = []
        for ant, con in self._entailment_rules:
            ant_belief = self._find_by_proposition(ant)
            if ant_belief and ant_belief.confidence > 0.5:
                con_belief = self._find_by_proposition(con)
                if not con_belief or con_belief.confidence < ant_belief.confidence * 0.9:
                    new_b = self.revise(
                        con,
                        ant_belief.confidence * 0.9,
                        BeliefSource.INFERENCE,
                    )
                    new_b.dependencies.append(ant_belief.belief_id)
                    deduced.append(new_b)
        return deduced

    def add_conditional(self, proposition: str, condition: str, confidence: float = 0.5) -> ConditionalBelief:
        """添加条件信念。"""
        cb = ConditionalBelief(
            proposition=proposition,
            condition=condition,
            confidence=confidence,
            belief_id=f"cb_{len(self._conditional_beliefs)}",
        )
        self._conditional_beliefs.append(cb)
        return cb

    def query_conditional(self, condition: str) -> list[ConditionalBelief]:
        """查询在给定条件下成立的信念。"""
        return [cb for cb in self._conditional_beliefs if cb.condition == condition]

    def does_believe(self, proposition: str, threshold: float = 0.5) -> bool:
        """B(p): Agent是否相信p?"""
        belief = self._find_by_proposition(proposition)
        return belief is not None and belief.confidence >= threshold

    def get_belief(self, proposition: str) -> Belief | None:
        return self._find_by_proposition(proposition)

    @property
    def stats(self) -> dict[str, Any]:
        by_source = {}
        for b in self._beliefs.values():
            by_source[b.source.value] = by_source.get(b.source.value, 0) + 1
        return {
            "agent_id": self._agent_id,
            "total_beliefs": len(self._beliefs),
            "axioms": sum(1 for b in self._beliefs.values() if b.is_axiom),
            "strong_beliefs": sum(1 for b in self._beliefs.values() if b.is_strong),
            "weak_beliefs": sum(1 for b in self._beliefs.values() if b.is_weak),
            "conditional_beliefs": len(self._conditional_beliefs),
            "revisions": len(self._revisions),
            "consistency_checks": self._consistency_checks,
            "inconsistencies_found": self._inconsistencies_found,
            "entailment_rules": len(self._entailment_rules),
            "by_source": by_source,
            "strategy": self._revision_strategy.value,
        }
