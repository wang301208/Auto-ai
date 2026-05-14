"""民主治理：代理集体的提案/投票/否决/弹劾机制。

Phase 19.4: Full democratic governance layer:
  - Proposals (any agent can propose changes)
  - Voting (weighted by reputation/contribution)
  - Veto (senior agents can veto, subject to override)
  - Impeachment (remove misbehaving agents by supermajority)
  - Constitution (immutable rules that can't be voted away)
  - Term limits (agents rotate out of power positions)

Builds on ConsensusEngine for the voting mechanics.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from autoai.agents.consensus_engine import (
    ConsensusEngine,
    ProposalStatus,
    VoteChoice,
)
from autoai.logs import logger


class GovernanceAction(Enum):
    POLICY_CHANGE = "policy_change"
    RESOURCE_ALLOCATION = "resource_allocation"
    ROLE_CHANGE = "role_change"
    PROTOCOL_UPGRADE = "protocol_upgrade"
    ADMISSION = "admission"
    EXPULSION = "expulsion"
    IMPEACHMENT = "impeachment"
    CONSTITUTIONAL_AMENDMENT = "constitutional_amendment"


class MotionStatus(Enum):
    PROPOSED = "proposed"
    VOTING = "voting"
    PASSED = "passed"
    FAILED = "failed"
    VETOED = "vetoed"
    OVERRIDDEN = "overridden"
    EXECUTED = "executed"


@dataclass
class Constitution:
    rules: dict[str, str] = field(default_factory=dict)
    amendments: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.rules:
            self.rules = {
                "no_self_destruction": "Agents cannot vote to destroy the collective",
                "min_quorum": "All votes require at least 60% participation",
                "supermajority_for_expulsion": "Expulsion requires 75% supermajority",
                "veto_override": "Veto can be overridden by 80% supermajority",
                "term_limits": "No agent holds a power role for more than 5 terms",
            }

    def is_amendable(self, rule_name: str) -> bool:
        protected = {"no_self_destruction"}
        return rule_name not in protected


@dataclass
class Motion:
    motion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    action: GovernanceAction = GovernanceAction.POLICY_CHANGE
    title: str = ""
    description: str = ""
    proposer_id: str = ""
    target_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: MotionStatus = MotionStatus.PROPOSED
    proposal_id: str = ""
    vetoed_by: str = ""
    override_votes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    voting_deadline: str = ""
    execution_result: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTerm:
    agent_id: str
    role: str
    term_start: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    term_count: int = 1
    max_terms: int = 5


class DemocraticGovernance:
    """代理集体的完整民主治理。

    Usage:
        gov = DemocraticGovernance()
        gov.admit_agent("a1", reputation=0.9, veto_power=True)
        gov.admit_agent("a2", reputation=0.7)
        mid = gov.propose_motion("a1", GovernanceAction.POLICY_CHANGE, "Increase autonomy", "Raise to L3")
        gov.vote_on_motion(mid, "a1", VoteChoice.YES)
        gov.vote_on_motion(mid, "a2", VoteChoice.YES)
        result = gov.resolve_motion(mid)
    """

    def __init__(
        self,
        voting_period_seconds: float = 300.0,
        impeachment_supermajority: float = 0.75,
        veto_override_supermajority: float = 0.80,
        max_terms: int = 5,
        constitution: Constitution | None = None,
    ) -> None:
        self._voting_period = voting_period_seconds
        self._impeachment_majority = impeachment_supermajority
        self._veto_override_majority = veto_override_supermajority
        self._max_terms = max_terms
        self._constitution = constitution or Constitution()
        self._consensus = ConsensusEngine(
            default_quorum=0.6,
            default_supermajority=0.67,
        )
        self._members: dict[str, dict[str, Any]] = {}
        self._motions: dict[str, Motion] = {}
        self._terms: dict[str, AgentTerm] = {}
        self._veto_count: dict[str, int] = defaultdict(int)
        self._motion_history: list[Motion] = []

    def admit_agent(
        self,
        agent_id: str,
        reputation: float = 1.0,
        weight: float = 1.0,
        veto_power: bool = False,
    ) -> None:
        self._consensus.register_agent(
            agent_id, weight=weight, reputation=reputation, veto_power=veto_power,
        )
        self._members[agent_id] = {
            "reputation": reputation,
            "weight": weight,
            "veto_power": veto_power,
            "admitted_at": datetime.now(timezone.utc).isoformat(),
        }

    def expel_agent(self, agent_id: str) -> bool:
        if agent_id not in self._members:
            return False
        self._consensus.unregister_agent(agent_id)
        self._members.pop(agent_id)
        self._terms.pop(agent_id, None)
        return True

    def propose_motion(
        self,
        proposer_id: str,
        action: GovernanceAction,
        title: str,
        description: str = "",
        target_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> str:
        if proposer_id not in self._members:
            return ""

        if action == GovernanceAction.CONSTITUTIONAL_AMENDMENT:
            rule_name = payload.get("rule_name", "") if payload else ""
            if not self._constitution.is_amendable(rule_name):
                logger.warn(f"[DemGov] Cannot amend protected rule: {rule_name}")
                return ""

        supermajority = 0.67
        if action == GovernanceAction.EXPULSION or action == GovernanceAction.IMPEACHMENT:
            supermajority = self._impeachment_majority
        elif action == GovernanceAction.CONSTITUTIONAL_AMENDMENT:
            supermajority = self._veto_override_majority

        proposal_id = self._consensus.propose(
            proposer_id=proposer_id,
            title=title,
            description=description,
            payload=payload or {},
            supermajority=supermajority,
            ttl_seconds=self._voting_period,
        )

        motion = Motion(
            action=action,
            title=title,
            description=description,
            proposer_id=proposer_id,
            target_id=target_id,
            payload=payload or {},
            proposal_id=proposal_id,
        )
        deadline = datetime.now(timezone.utc) + timedelta(seconds=self._voting_period)
        motion.voting_deadline = deadline.isoformat()

        self._motions[motion.motion_id] = motion
        return motion.motion_id

    def vote_on_motion(
        self,
        motion_id: str,
        voter_id: str,
        choice: VoteChoice,
        reason: str = "",
    ) -> bool:
        motion = self._motions.get(motion_id)
        if motion is None:
            return False
        if motion.status not in (MotionStatus.PROPOSED, MotionStatus.VOTING):
            return False

        motion.status = MotionStatus.VOTING
        return self._consensus.vote(motion.proposal_id, voter_id, choice, reason)

    def veto_motion(self, motion_id: str, vetoer_id: str) -> bool:
        motion = self._motions.get(motion_id)
        if motion is None:
            return False

        member = self._members.get(vetoer_id)
        if member is None or not member.get("veto_power", False):
            return False

        motion.status = MotionStatus.VETOED
        motion.vetoed_by = vetoer_id
        self._veto_count[vetoer_id] += 1

        logger.info(f"[DemGov] Moti在{motion_id} vetoed 通过{vetoer_id}")
        return True

    def override_veto(
        self,
        motion_id: str,
        voter_id: str,
    ) -> bool:
        motion = self._motions.get(motion_id)
        if motion is None or motion.status != MotionStatus.VETOED:
            return False

        motion.override_votes += 1

        total_members = len(self._members)
        if total_members == 0:
            return False

        if motion.override_votes / total_members >= self._veto_override_majority:
            motion.status = MotionStatus.OVERRIDDEN
            logger.info(f"[DemGov] Ve到overridden 用于moti在{motion_id}")
            return True

        return False

    def resolve_motion(self, motion_id: str) -> MotionStatus:
        motion = self._motions.get(motion_id)
        if motion is None:
            return MotionStatus.FAILED

        if motion.status == MotionStatus.VETOED:
            return MotionStatus.VETOED

        if motion.status == MotionStatus.OVERRIDDEN:
            result = self._consensus.resolve(motion.proposal_id)
            if result and result.status == ProposalStatus.ACCEPTED:
                motion.status = MotionStatus.PASSED
            else:
                motion.status = MotionStatus.FAILED
            self._motion_history.append(motion)
            return motion.status

        result = self._consensus.resolve(motion.proposal_id)
        if result is None:
            return MotionStatus.FAILED

        if result.status == ProposalStatus.ACCEPTED:
            motion.status = MotionStatus.PASSED
            if motion.action == GovernanceAction.EXPULSION:
                self.expel_agent(motion.target_id)
            elif motion.action == GovernanceAction.ADMISSION:
                pass
            elif motion.action == GovernanceAction.CONSTITUTIONAL_AMENDMENT:
                rule_name = motion.payload.get("rule_name", "")
                new_value = motion.payload.get("new_value", "")
                if self._constitution.is_amendable(rule_name):
                    self._constitution.rules[rule_name] = new_value
                    self._constitution.amendments.append({
                        "rule": rule_name,
                        "new_value": new_value,
                        "motion_id": motion_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
        elif result.status == ProposalStatus.REJECTED:
            motion.status = MotionStatus.FAILED
        elif result.status == ProposalStatus.EXPIRED:
            motion.status = MotionStatus.FAILED

        self._motion_history.append(motion)
        return motion.status

    def impeach(
        self,
        target_id: str,
        proposer_id: str,
        reason: str = "",
    ) -> str:
        return self.propose_motion(
            proposer_id=proposer_id,
            action=GovernanceAction.IMPEACHMENT,
            title=f"Impeach {target_id}",
            description=reason,
            target_id=target_id,
        )

    def assign_term(self, agent_id: str, role: str) -> bool:
        if agent_id not in self._members:
            return False
        existing = self._terms.get(agent_id)
        if existing and existing.role == role:
            if existing.term_count >= self._max_terms:
                return False
            existing.term_count += 1
            return True
        self._terms[agent_id] = AgentTerm(
            agent_id=agent_id, role=role, max_terms=self._max_terms,
        )
        return True

    @property
    def constitution(self) -> Constitution:
        return self._constitution

    @property
    def member_count(self) -> int:
        return len(self._members)

    @property
    def active_motions(self) -> int:
        return sum(
            1 for m in self._motions.values()
            if m.status in (MotionStatus.PROPOSED, MotionStatus.VOTING)
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "members": len(self._members),
            "active_motions": self.active_motions,
            "total_motions": len(self._motions),
            "motion_history": len(self._motion_history),
            "constitution_rules": len(self._constitution.rules),
            "constitution_amendments": len(self._constitution.amendments),
            "terms": {aid: {"role": t.role, "count": t.term_count} for aid, t in self._terms.items()},
        }


__all__ = [
    "DemocraticGovernance",
    "GovernanceAction",
    "Motion",
    "MotionStatus",
    "Constitution",
    "AgentTerm",
]
