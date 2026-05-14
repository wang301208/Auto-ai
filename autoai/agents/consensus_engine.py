"""Consensus Engine: Blockchain-inspired voting consensus for multi-agent decisions.

Phase 19.1: Enables agents to reach agreement through:
  - Weighted voting (agents vote with configurable weights)
  - Byzantine fault tolerance (supermajority + reputation weighting)
  - Proposal chain (immutable linked proposal history, like a blockchain)
  - Delegated voting (agents can delegate votes to trusted agents)
  - Automatic consensus detection (early termination when supermajority reached)

Every proposal and vote is immutably recorded for audit.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from autoai.logs import logger


class ProposalStatus(Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    VETOED = "vetoed"


class VoteChoice(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class Proposal:
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    title: str = ""
    description: str = ""
    proposer_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.OPEN
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""
    required_quorum: float = 0.6
    required_supermajority: float = 0.67
    prev_hash: str = "0" * 16
    hash: str = ""

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        content = f"{self.proposal_id}:{self.title}:{self.proposer_id}:{self.prev_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class Vote:
    proposal_id: str
    voter_id: str
    choice: VoteChoice
    weight: float = 1.0
    delegated_from: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str = ""


@dataclass
class ConsensusResult:
    proposal_id: str
    status: ProposalStatus
    yes_votes: float = 0.0
    no_votes: float = 0.0
    abstain_votes: float = 0.0
    total_weight: float = 0.0
    quorum_reached: bool = False
    supermajority_reached: bool = False
    voters: list[str] = field(default_factory=list)


class ConsensusEngine:
    """Blockchain-inspired 共识 for multi-代理 decisions.

    Usage:
        engine = ConsensusEngine()
        engine.register_agent("a1", weight=2.0, reputation=0.9)
        engine.register_agent("a2", weight=1.0, reputation=0.7)
        pid = engine.propose("a1", "Deploy v2", "Deploy new version")
        engine.vote(pid, "a1", VoteChoice.YES)
        engine.vote(pid, "a2", VoteChoice.YES)
        result = engine.resolve(pid)
    """

    def __init__(
        self,
        default_quorum: float = 0.6,
        default_supermajority: float = 0.67,
        max_byzantine_ratio: float = 1.0 / 3.0,
    ) -> None:
        self._default_quorum = default_quorum
        self._default_supermajority = default_supermajority
        self._max_byzantine_ratio = max_byzantine_ratio
        self._agents: dict[str, dict[str, Any]] = {}
        self._proposals: dict[str, Proposal] = {}
        self._votes: dict[str, list[Vote]] = {}
        self._delegations: dict[str, str] = {}
        self._chain_head: str = "0" * 16
        self._resolved: list[ConsensusResult] = []

    def register_agent(
        self,
        agent_id: str,
        weight: float = 1.0,
        reputation: float = 1.0,
        veto_power: bool = False,
    ) -> None:
        self._agents[agent_id] = {
            "weight": weight,
            "reputation": reputation,
            "veto_power": veto_power,
        }

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self._delegations.pop(agent_id, None)

    def delegate_vote(self, from_agent: str, to_agent: str) -> bool:
        if from_agent not in self._agents or to_agent not in self._agents:
            return False
        if from_agent == to_agent:
            return False
        visited = {from_agent}
        current = to_agent
        while current in self._delegations:
            if current in visited:
                return False
            visited.add(current)
            current = self._delegations[current]
        if current == from_agent:
            return False
        self._delegations[from_agent] = to_agent
        return True

    def propose(
        self,
        proposer_id: str,
        title: str,
        description: str = "",
        payload: dict[str, Any] | None = None,
        quorum: float | None = None,
        supermajority: float | None = None,
        ttl_seconds: float | None = None,
    ) -> str:
        if proposer_id not in self._agents:
            logger.warn(f"[Consensus] Unknown proposer: {proposer_id}")
            return ""

        proposal = Proposal(
            title=title,
            description=description,
            proposer_id=proposer_id,
            payload=payload or {},
            required_quorum=quorum or self._default_quorum,
            required_supermajority=supermajority or self._default_supermajority,
            prev_hash=self._chain_head,
        )

        if ttl_seconds is not None:
            from datetime import timedelta
            created = datetime.fromisoformat(proposal.created_at)
            proposal.expires_at = (created + timedelta(seconds=ttl_seconds)).isoformat()

        self._proposals[proposal.proposal_id] = proposal
        self._votes[proposal.proposal_id] = []
        self._chain_head = proposal.hash

        return proposal.proposal_id

    def vote(
        self,
        proposal_id: str,
        voter_id: str,
        choice: VoteChoice,
        reason: str = "",
    ) -> bool:
        if proposal_id not in self._proposals:
            return False
        proposal = self._proposals[proposal_id]
        if proposal.status != ProposalStatus.OPEN:
            return False
        if self._is_expired(proposal):
            proposal.status = ProposalStatus.EXPIRED
            return False

        actual_voter = voter_id
        delegated_from = ""
        if voter_id in self._delegations:
            actual_voter = self._resolve_delegation(voter_id)
            delegated_from = voter_id

        if actual_voter not in self._agents:
            return False

        existing_voters = {v.voter_id for v in self._votes[proposal_id]}
        if actual_voter in existing_voters:
            return False

        agent_info = self._agents[actual_voter]
        effective_weight = agent_info["weight"] * agent_info["reputation"]

        vote_obj = Vote(
            proposal_id=proposal_id,
            voter_id=actual_voter,
            choice=choice,
            weight=effective_weight,
            delegated_from=delegated_from,
            reason=reason,
        )

        self._votes[proposal_id].append(vote_obj)

        if self._check_early_consensus(proposal):
            self.resolve(proposal_id)

        return True

    def resolve(self, proposal_id: str) -> ConsensusResult | None:
        if proposal_id not in self._proposals:
            return None

        proposal = self._proposals[proposal_id]

        if proposal.status == ProposalStatus.VETOED:
            return self._make_result(proposal, ProposalStatus.VETOED)

        if self._is_expired(proposal):
            proposal.status = ProposalStatus.EXPIRED
            return self._make_result(proposal, ProposalStatus.EXPIRED)

        votes = self._votes.get(proposal_id, [])
        yes_weight = sum(v.weight for v in votes if v.choice == VoteChoice.YES)
        no_weight = sum(v.weight for v in votes if v.choice == VoteChoice.NO)
        abstain_weight = sum(v.weight for v in votes if v.choice == VoteChoice.ABSTAIN)
        total_voted = yes_weight + no_weight + abstain_weight

        total_possible = sum(
            info["weight"] * info["reputation"]
            for info in self._agents.values()
        )

        quorum_reached = (total_voted / total_possible) >= proposal.required_quorum if total_possible > 0 else False
        supermajority_reached = (yes_weight / total_voted) >= proposal.required_supermajority if total_voted > 0 else False

        byzantine_limit = len(self._agents) * self._max_byzantine_ratio
        byzantine_ok = no_weight <= (total_voted * self._max_byzantine_ratio)

        for v in votes:
            if v.choice == VoteChoice.NO:
                voter_info = self._agents.get(v.voter_id, {})
                if voter_info.get("veto_power", False):
                    proposal.status = ProposalStatus.VETOED
                    result = self._make_result(proposal, ProposalStatus.VETOED)
                    result.yes_votes = yes_weight
                    result.no_votes = no_weight
                    result.abstain_votes = abstain_weight
                    self._resolved.append(result)
                    return result

        if quorum_reached and supermajority_reached and byzantine_ok:
            proposal.status = ProposalStatus.ACCEPTED
            status = ProposalStatus.ACCEPTED
        elif quorum_reached and not supermajority_reached:
            proposal.status = ProposalStatus.REJECTED
            status = ProposalStatus.REJECTED
        else:
            status = proposal.status

        result = self._make_result(proposal, status)
        result.yes_votes = yes_weight
        result.no_votes = no_weight
        result.abstain_votes = abstain_weight
        result.quorum_reached = quorum_reached
        result.supermajority_reached = supermajority_reached
        result.total_weight = total_voted

        self._resolved.append(result)
        return result

    def _make_result(self, proposal: Proposal, status: ProposalStatus) -> ConsensusResult:
        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            status=status,
            voters=[v.voter_id for v in self._votes.get(proposal.proposal_id, [])],
        )

    def _check_early_consensus(self, proposal: Proposal) -> bool:
        votes = self._votes.get(proposal.proposal_id, [])
        yes_weight = sum(v.weight for v in votes if v.choice == VoteChoice.YES)
        total_possible = sum(
            info["weight"] * info["reputation"]
            for info in self._agents.values()
        )
        if total_possible == 0:
            return False
        remaining = total_possible - sum(v.weight for v in votes)
        max_possible_yes = yes_weight + remaining
        if max_possible_yes / total_possible < proposal.required_supermajority:
            return True
        if yes_weight / total_possible >= proposal.required_supermajority:
            quorum = sum(v.weight for v in votes) / total_possible
            if quorum >= proposal.required_quorum:
                return True
        return False

    def _is_expired(self, proposal: Proposal) -> bool:
        if not proposal.expires_at:
            return False
        try:
            return datetime.now(timezone.utc).isoformat() > proposal.expires_at
        except Exception:
            return False

    def _resolve_delegation(self, agent_id: str) -> str:
        current = agent_id
        visited = set()
        while current in self._delegations:
            if current in visited:
                break
            visited.add(current)
            current = self._delegations[current]
        return current

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)

    def get_votes(self, proposal_id: str) -> list[Vote]:
        return self._votes.get(proposal_id, [])

    @property
    def chain_head(self) -> str:
        return self._chain_head

    @property
    def proposal_count(self) -> int:
        return len(self._proposals)

    def get_status(self) -> dict[str, Any]:
        return {
            "registered_agents": len(self._agents),
            "total_proposals": len(self._proposals),
            "resolved": len(self._resolved),
            "chain_head": self._chain_head,
            "delegations": len(self._delegations),
        }


__all__ = [
    "ConsensusEngine",
    "ConsensusResult",
    "Proposal",
    "ProposalStatus",
    "Vote",
    "VoteChoice",
]
