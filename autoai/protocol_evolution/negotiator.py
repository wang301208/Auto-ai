from __future__ import annotations

import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class VoteType(Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class ProtocolVersion:
    protocol_id: str
    version: int
    spec: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    failure_rate: float = 0.0
    adoption_rate: float = 0.0
    parent_version: int | None = None

    @property
    def is_stable(self) -> bool:
        return self.failure_rate < 0.1 and self.adoption_rate > 0.5

    @property
    def version_tag(self) -> str:
        return f"{self.protocol_id}@v{self.version}"


@dataclass
class ProtocolVote:
    voter_id: str
    proposal_id: str
    vote: VoteType
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class NegotiationRound:
    round_id: str
    proposal: dict[str, Any]
    votes: list[ProtocolVote] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    concluded: bool = False
    result: str = ""

    @property
    def accept_count(self) -> int:
        return sum(1 for v in self.votes if v.vote == VoteType.ACCEPT)

    @property
    def reject_count(self) -> int:
        return sum(1 for v in self.votes if v.vote == VoteType.REJECT)

    @property
    def is_accepted(self) -> bool:
        total = len(self.votes)
        if total == 0:
            return False
        return self.accept_count > self.reject_count


class ProtocolEvolver:
    """协议进化器: 协商/适配/版本管理。"""

    def __init__(self, protocol_id: str = "agent-comm"):
        self.protocol_id = protocol_id
        self._versions: list[ProtocolVersion] = []
        self._active_version: ProtocolVersion | None = None
        self._negotiation_rounds: list[NegotiationRound] = []
        self._failure_records: list[tuple[str, float]] = []
        v0 = ProtocolVersion(protocol_id=protocol_id, version=0, spec={"format": "json", "encoding": "utf-8"})
        self._versions.append(v0)
        self._active_version = v0

    def propose_change(self, change_spec: dict[str, Any], proposer: str = "system") -> NegotiationRound:
        """提出协议变更提案。"""
        proposal_id = hashlib.sha256(f"{proposer}:{time.time()}:{change_spec}".encode()).hexdigest()[:12]
        nr = NegotiationRound(round_id=proposal_id, proposal=change_spec)
        self._negotiation_rounds.append(nr)
        logger.info(f"协议变更提案: {proposal_id} by {proposer}")
        return nr

    def vote(self, round_id: str, voter_id: str, vote_type: VoteType, reason: str = "") -> bool:
        """对提案投票。"""
        nr = next((r for r in self._negotiation_rounds if r.round_id == round_id), None)
        if nr is None or nr.concluded:
            return False
        pv = ProtocolVote(voter_id=voter_id, proposal_id=round_id, vote=vote_type, reason=reason)
        nr.votes.append(pv)
        return True

    def conclude_negotiation(self, round_id: str, quorum: int = 2) -> ProtocolVersion | None:
        """结束协商，如果通过则创建新版本。"""
        nr = next((r for r in self._negotiation_rounds if r.round_id == round_id), None)
        if nr is None or nr.concluded:
            return None
        if len(nr.votes) < quorum:
            nr.result = "quorum_not_met"
            nr.concluded = True
            return None
        if nr.is_accepted:
            new_version = ProtocolVersion(
                protocol_id=self.protocol_id,
                version=len(self._versions),
                spec={**self._active_version.spec, **nr.proposal},
                parent_version=self._active_version.version,
            )
            self._versions.append(new_version)
            self._active_version = new_version
            nr.result = "accepted"
            nr.concluded = True
            logger.info(f"协议进化: {new_version.version_tag}")
            return new_version
        nr.result = "rejected"
        nr.concluded = True
        return None

    def record_failure(self, error_type: str) -> None:
        self._failure_records.append((error_type, time.time()))
        if self._active_version:
            recent = [t for _, t in self._failure_records if time.time() - t < 3600]
            self._active_version.failure_rate = min(1.0, len(recent) / 100.0)

    def auto_adapt(self) -> ProtocolVersion | None:
        """根据失败率自动适配协议。"""
        if self._active_version and self._active_version.failure_rate > 0.3:
            nr = self.propose_change({"encoding": "msgpack", "compression": "lz4"}, proposer="auto-adapt")
            self.vote(nr.round_id, "auto-adapt", VoteType.ACCEPT, "high_failure_rate")
            return self.conclude_negotiation(nr.round_id, quorum=1)
        return None

    @property
    def active_version(self) -> ProtocolVersion | None:
        return self._active_version

    @property
    def version_history(self) -> list[ProtocolVersion]:
        return list(self._versions)

    @property
    def stats(self) -> dict[str, Any]:
        av = self._active_version
        return {
            "protocol_id": self.protocol_id,
            "active_version": av.version_tag if av else "none",
            "total_versions": len(self._versions),
            "is_stable": av.is_stable if av else False,
            "failure_rate": av.failure_rate if av else 0.0,
            "negotiations": len(self._negotiation_rounds),
        }
