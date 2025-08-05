from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict


@dataclass
class EventMessage:
    """Event message passed through the event bus and message queue.

    ``source_agent`` records the component that emitted the event and is
    stored alongside the payload for later auditing or coordination.
    """

    event_type: str
    payload: dict[str, Any] | str | None = None
    source_agent: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


DIAGNOSIS_COMPLETE = "DIAGNOSIS_COMPLETE"
"""Event type emitted when diagnostic analysis finishes."""

CODE_FIX_PROPOSED = "CODE_FIX_PROPOSED"
"""Event type emitted when a code fix has been proposed."""

HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
"""Event type emitted when human approval is needed for a fix."""

APPROVAL_GRANTED = "APPROVAL_GRANTED"
"""Event type emitted once a human reviewer approves a proposed fix."""

ISSUE_RESOLVED = "ISSUE_RESOLVED"
"""Event type emitted after a fix has been merged and deployed."""

TICKET_RECEIVED = "TICKET_RECEIVED"
"""Event type emitted when a ticket describing an issue is received."""

ISSUE_DETECTED = "ISSUE_DETECTED"
"""Event type emitted when a plugin issue is detected."""

TESTS_FAILED = "TESTS_FAILED"
"""Event type emitted when verification tests fail."""

DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
"""Event type emitted when deployment fails."""


@dataclass(kw_only=True)
class IssueDetected(EventMessage):
    """Schema for :data:`ISSUE_DETECTED` events.

    Expected payload fields:
        issue_type: Categorisation such as ``"bug"`` or ``"dependency_update"``.
        plugin: Identifier of the emitting component.
        description: Human-readable summary of the issue.
        error_log: Optional log snippet or message describing the problem.
        metadata: Additional context like ``file``, ``line`` or ``commit``.
    """

    issue_type: str
    plugin: str | None = None
    description: str | None = None
    error_log: str | None = None
    metadata: dict[str, Any] | None = None
    event_type: str = field(init=False, default=ISSUE_DETECTED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "issue_type": self.issue_type,
            "plugin": self.plugin,
            "description": self.description,
            "error_log": self.error_log,
        }
        if self.metadata:
            self.payload.update(self.metadata)
        self.payload = {k: v for k, v in self.payload.items() if v is not None}


@dataclass(kw_only=True)
class TicketReceived(IssueDetected):
    """Schema for :data:`TICKET_RECEIVED` events.

    Identical to :class:`IssueDetected` but used for generic issue tickets.
    """

    event_type: str = field(init=False, default=TICKET_RECEIVED)


class RecommendedSkill(TypedDict):
    """Metadata describing a skill suggestion."""

    name: str
    version: str
    parameters: dict[str, Any]


class DiagnosisDetails(TypedDict, total=False):
    """Extra information included with :class:`DiagnosisComplete`."""

    recommended_skill: RecommendedSkill | None
    # other optional fields such as ``skill_search`` or ``metadata`` may appear


@dataclass(kw_only=True)
class DiagnosisComplete(EventMessage):
    """Schema for :data:`DIAGNOSIS_COMPLETE` events."""

    summary: str
    actionable_recommendations: str
    details: DiagnosisDetails | None = None
    event_type: str = field(init=False, default=DIAGNOSIS_COMPLETE)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = {"recommended_skill": None}
        else:
            self.details.setdefault("recommended_skill", None)

        self.payload = {
            "summary": self.summary,
            "actionable_recommendations": self.actionable_recommendations,
            "details": self.details,
        }


@dataclass(kw_only=True)
class CodeFixProposed(EventMessage):
    """Schema for :data:`CODE_FIX_PROPOSED` events.

    Expected payload fields:
        branch_name: Branch containing the proposed fix.
        commit_hash: Hash of the commit with the fix.
        summary: Short description of the proposed fix.
    """

    branch_name: str
    commit_hash: str
    summary: str
    event_type: str = field(init=False, default=CODE_FIX_PROPOSED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "commit_hash": self.commit_hash,
            "summary": self.summary,
        }


@dataclass(kw_only=True)
class HumanApprovalRequired(EventMessage):
    """Schema for :data:`HUMAN_APPROVAL_REQUIRED` events.

    Expected payload fields:
        branch_name: Branch containing the proposed fix.
        test_output: Output from the verification test run.
        summary: Short description of the proposed fix.
        diff: Diff between ``main`` and the proposed branch.
    """

    branch_name: str
    test_output: str
    summary: str
    diff: str
    event_type: str = field(init=False, default=HUMAN_APPROVAL_REQUIRED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "test_output": self.test_output,
            "summary": self.summary,
            "diff": self.diff,
        }


@dataclass(kw_only=True)
class TestsFailed(EventMessage):
    """Schema for :data:`TESTS_FAILED` events."""

    branch_name: str
    test_output: str
    summary: str
    event_type: str = field(init=False, default=TESTS_FAILED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "test_output": self.test_output,
            "summary": self.summary,
        }


@dataclass(kw_only=True)
class ApprovalGranted(EventMessage):
    """Schema for :data:`APPROVAL_GRANTED` events.

    Expected payload fields:
        branch_name: Branch containing the approved fix.
        commit_hash: Hash of the commit that was approved.
        summary: Short description of the approved fix.
    """

    branch_name: str
    commit_hash: str
    summary: str
    event_type: str = field(init=False, default=APPROVAL_GRANTED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "commit_hash": self.commit_hash,
            "summary": self.summary,
        }


@dataclass(kw_only=True)
class IssueResolved(EventMessage):
    """Schema for :data:`ISSUE_RESOLVED` events.

    Expected payload fields:
        branch_name: Branch that contained the fix.
        commit_hash: Hash of the commit that resolved the issue.
        summary: Short description of the resolution.
    """

    branch_name: str
    commit_hash: str
    summary: str
    event_type: str = field(init=False, default=ISSUE_RESOLVED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "commit_hash": self.commit_hash,
            "summary": self.summary,
        }


@dataclass(kw_only=True)
class DeploymentFailed(EventMessage):
    """Schema for :data:`DEPLOYMENT_FAILED` events."""

    branch_name: str
    commit_hash: str
    summary: str
    return_code: int
    event_type: str = field(init=False, default=DEPLOYMENT_FAILED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "commit_hash": self.commit_hash,
            "summary": self.summary,
            "return_code": self.return_code,
        }


__all__ = [
    "EventMessage",
    "IssueDetected",
    "DiagnosisComplete",
    "CodeFixProposed",
    "HumanApprovalRequired",
    "TestsFailed",
    "ApprovalGranted",
    "IssueResolved",
    "DeploymentFailed",
    "ISSUE_DETECTED",
    "DIAGNOSIS_COMPLETE",
    "CODE_FIX_PROPOSED",
    "HUMAN_APPROVAL_REQUIRED",
    "TESTS_FAILED",
    "APPROVAL_GRANTED",
    "ISSUE_RESOLVED",
    "DEPLOYMENT_FAILED",
]
