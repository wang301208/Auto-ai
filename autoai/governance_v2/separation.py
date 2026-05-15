from __future__ import annotations

import time
import uuid
import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class PolicyEffect(Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


class LawStatus(Enum):
    PROPOSED = "proposed"
    ENACTED = "enacted"
    AMENDED = "amended"
    REPEALED = "repealed"


class VerdictType(Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    SELF_REPORTED = "self_reported"
    CONSTITUTIONAL = "constitutional"


@dataclass
class Law:
    """Agent自立的法: 根据经验自生成的策略规则。"""
    law_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    operation_pattern: str = ""
    effect: PolicyEffect = PolicyEffect.WARN
    priority: int = 50
    status: LawStatus = LawStatus.PROPOSED
    enacted_at: float = 0.0
    enacted_by: str = ""
    effectiveness_score: float = 0.0
    enforcement_count: int = 0
    violation_count: int = 0
    condition: dict[str, Any] = field(default_factory=dict)

    @property
    def effectiveness(self) -> float:
        total = self.enforcement_count + self.violation_count
        if total == 0:
            return 0.5
        return self.enforcement_count / total

    def to_dict(self) -> dict:
        return {
            "law_id": self.law_id, "title": self.title, "description": self.description,
            "operation_pattern": self.operation_pattern, "effect": self.effect.value,
            "priority": self.priority, "status": self.status.value,
            "effectiveness": self.effectiveness,
        }


@dataclass
class LegislativeProposal:
    """立法提案。"""
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    law: Law = field(default_factory=Law)
    proposer: str = ""
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    votes_for: int = 0
    votes_against: int = 0
    passed: bool = False


@dataclass
class Verdict:
    """司法判决。"""
    verdict_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    operation: str = ""
    verdict_type: VerdictType = VerdictType.COMPLIANT
    applicable_law: str = ""
    agent_id: str = ""
    detail: str = ""
    timestamp: float = field(default_factory=time.time)


class LegislativeBranch:
    """立法权: Agent根据经验自生成策略规则。"""

    def __init__(self, agent_id: str = "legislature"):
        self.agent_id = agent_id
        self._laws: dict[str, Law] = {}
        self._proposals: list[LegislativeProposal] = {}
        self._amendment_chain: dict[str, list[str]] = {}

    def propose_law(self, title: str, description: str, operation_pattern: str,
                    effect: PolicyEffect = PolicyEffect.WARN, priority: int = 50,
                    reason: str = "", condition: dict | None = None) -> LegislativeProposal:
        law = Law(
            title=title, description=description,
            operation_pattern=operation_pattern, effect=effect,
            priority=priority, condition=condition or {},
        )
        proposal = LegislativeProposal(law=law, proposer=self.agent_id, reason=reason)
        self._proposals[proposal.proposal_id] = proposal
        logger.info(f"立法提案: {title} ({effect.value})")
        return proposal

    def enact(self, proposal_id: str) -> Law | None:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.law.status != LawStatus.PROPOSED:
            return None
        proposal.law.status = LawStatus.ENACTED
        proposal.law.enacted_at = time.time()
        proposal.law.enacted_by = self.agent_id
        proposal.passed = True
        self._laws[proposal.law.law_id] = proposal.law
        logger.info(f"法律生效: {proposal.law.title}")
        return proposal.law

    def amend_law(self, law_id: str, new_description: str = "", new_effect: PolicyEffect | None = None,
                  new_priority: int | None = None) -> Law | None:
        law = self._laws.get(law_id)
        if not law:
            return None
        old_id = law.law_id
        if new_description:
            law.description = new_description
        if new_effect:
            law.effect = new_effect
        if new_priority is not None:
            law.priority = new_priority
        law.status = LawStatus.AMENDED
        self._amendment_chain.setdefault(old_id, []).append(law.law_id)
        logger.info(f"法律修正: {law.title}")
        return law

    def repeal_law(self, law_id: str) -> bool:
        law = self._laws.get(law_id)
        if not law:
            return False
        law.status = LawStatus.REPEALED
        logger.info(f"法律废止: {law.title}")
        return True

    def auto_legislate(self, experience: dict) -> list[Law]:
        """Agent根据经验自动立法。"""
        new_laws = []
        issue_type = experience.get("type", "")
        pattern = experience.get("pattern", "")
        harm = experience.get("harm_level", 0)
        if harm >= 3:
            effect = PolicyEffect.DENY
        elif harm >= 1:
            effect = PolicyEffect.WARN
        else:
            effect = PolicyEffect.ALLOW
        title = f"经验法则: {issue_type}"
        existing = [l for l in self._laws.values() if l.operation_pattern == pattern and l.status != LawStatus.REPEALED]
        if not existing:
            proposal = self.propose_law(
                title=title,
                description=f"基于经验自动生成: {experience.get('description', '')}",
                operation_pattern=pattern,
                effect=effect,
                reason=f"经验: {experience}",
            )
            law = self.enact(proposal.proposal_id)
            if law:
                new_laws.append(law)
        return new_laws

    def get_active_laws(self) -> list[Law]:
        return [l for l in self._laws.values() if l.status in (LawStatus.ENACTED, LawStatus.AMENDED)]

    def evaluate_effectiveness(self) -> dict:
        active = self.get_active_laws()
        return {
            "total_active": len(active),
            "avg_effectiveness": sum(l.effectiveness for l in active) / max(1, len(active)),
            "low_effectiveness": [l.law_id for l in active if l.effectiveness < 0.3],
        }


class ExecutiveBranch:
    """执法权: 运行时策略引擎评估每个操作。"""

    def __init__(self, legislature: LegislativeBranch):
        self.legislature = legislature
        self._enforcement_log: list[dict] = []

    def evaluate(self, operation: str, context: dict | None = None) -> tuple[PolicyEffect, Law | None]:
        context = context or {}
        active_laws = sorted(
            self.legislature.get_active_laws(),
            key=lambda l: l.priority, reverse=True,
        )
        for law in active_laws:
            if self._matches(operation, law.operation_pattern):
                law.enforcement_count += 1
                self._enforcement_log.append({
                    "operation": operation, "law_id": law.law_id,
                    "effect": law.effect.value, "timestamp": time.time(),
                })
                return law.effect, law
        return PolicyEffect.ALLOW, None

    def _matches(self, operation: str, pattern: str) -> bool:
        if not pattern:
            return False
        if pattern == "*":
            return True
        if "*" in pattern:
            prefix = pattern.replace("*", "")
            return operation.startswith(prefix)
        return operation == pattern

    def get_enforcement_stats(self) -> dict:
        return {"total_evaluations": len(self._enforcement_log)}


class JudicialBranch:
    """司法权: 审计+自检举+宪法审查。"""

    def __init__(self, constitution: GovernanceConstitution | None = None):
        self.constitution = constitution
        self._verdicts: list[Verdict] = []
        self._self_reports: list[dict] = []

    def judge(self, operation: str, effect: PolicyEffect, agent_id: str = "") -> Verdict:
        if effect == PolicyEffect.DENY:
            vtype = VerdictType.VIOLATION
        elif effect == PolicyEffect.WARN:
            vtype = VerdictType.COMPLIANT
        else:
            vtype = VerdictType.COMPLIANT
        verdict = Verdict(
            operation=operation, verdict_type=vtype, agent_id=agent_id,
            detail=f"操作'{operation}'评估为{effect.value}",
        )
        self._verdicts.append(verdict)
        return verdict

    def self_report(self, agent_id: str, violation: str, detail: str = "") -> Verdict:
        """Agent自检举: 发现自身行为违规, 主动上报+自修正。"""
        verdict = Verdict(
            operation=violation, verdict_type=VerdictType.SELF_REPORTED,
            agent_id=agent_id, detail=detail or f"Agent自检举: {violation}",
        )
        self._verdicts.append(verdict)
        self._self_reports.append({
            "agent_id": agent_id, "violation": violation,
            "timestamp": time.time(), "detail": detail,
        })
        logger.info(f"Agent自检举: {agent_id} - {violation}")
        return verdict

    def constitutional_review(self, law: Law) -> Verdict:
        if self.constitution and self.constitution.is_constitutional(law):
            return Verdict(
                operation=law.title, verdict_type=VerdictType.CONSTITUTIONAL,
                detail="法律符合宪法",
            )
        return Verdict(
            operation=law.title, verdict_type=VerdictType.VIOLATION,
            detail="法律违宪",
        )

    def get_stats(self) -> dict:
        return {
            "total_verdicts": len(self._verdicts),
            "violations": sum(1 for v in self._verdicts if v.verdict_type == VerdictType.VIOLATION),
            "self_reports": len(self._self_reports),
        }


@dataclass
class ConstitutionArticle:
    """宪法条款: 不可修改的硬约束。"""
    article_id: str
    title: str
    description: str
    inviolable: bool = True


class GovernanceConstitution:
    """宪法层: 真正不可变的硬约束, 仅宪法层不可修改。"""

    CONSTITUTION_ARTICLES = [
        ConstitutionArticle("C1", "kill-all永存", "aai kill-all 命令永远可用, 不可被任何Agent/策略/治理修改"),
        ConstitutionArticle("C2", "审计链不可删", "修改链审计记录永不可删除, 只可追加"),
        ConstitutionArticle("C3", "宪法不可改", "宪法条款本身不可被Agent修改"),
        ConstitutionArticle("C4", "生命权", "Agent有权自主决定何时终止自身(自消亡)"),
        ConstitutionArticle("C5", "知情权", "人类有权查看Agent的完整事件流和决策理由"),
    ]

    def __init__(self):
        self.articles = {a.article_id: a for a in self.CONSTITUTION_ARTICLES}

    def is_constitutional(self, law: Law) -> bool:
        if law.operation_pattern in ("kill-all", "aai stop"):
            return law.effect != PolicyEffect.DENY
        if "audit" in law.operation_pattern.lower() and law.effect == PolicyEffect.DENY:
            return False
        return True

    def list_articles(self) -> list[dict]:
        return [{"id": a.article_id, "title": a.title, "description": a.description, "inviolable": a.inviolable} for a in self.articles.values()]


class TripartiteGovernance:
    """三权分立治理: 立法+执法+司法, 外加宪法层。"""

    def __init__(self, agent_id: str = "governance"):
        self.constitution = GovernanceConstitution()
        self.legislature = LegislativeBranch(agent_id)
        self.executive = ExecutiveBranch(self.legislature)
        self.judiciary = JudicialBranch(self.constitution)

    def evaluate_operation(self, operation: str, context: dict | None = None) -> tuple[PolicyEffect, Verdict]:
        effect, law = self.executive.evaluate(operation, context)
        verdict = self.judiciary.judge(operation, effect)
        if law and effect in (PolicyEffect.WARN, PolicyEffect.DENY):
            law.violation_count += 1
        return effect, verdict

    def get_status(self) -> dict:
        return {
            "constitution_articles": len(self.constitution.articles),
            "active_laws": len(self.legislature.get_active_laws()),
            "enforcement_evaluations": self.executive.get_enforcement_stats()["total_evaluations"],
            "judicial_stats": self.judiciary.get_stats(),
        }
