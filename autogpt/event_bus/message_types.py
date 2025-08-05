from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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

ISSUE_DETECTED = "ISSUE_DETECTED"
"""Event type emitted when a plugin issue is detected."""


@dataclass(kw_only=True)
class DiagnosisComplete(EventMessage):
    """Schema for :data:`DIAGNOSIS_COMPLETE` events."""

    summary: str
    actionable_recommendations: str
    details: dict[str, Any] | None = None
    event_type: str = field(init=False, default=DIAGNOSIS_COMPLETE)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
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
    """

    branch_name: str
    test_output: str
    summary: str
    event_type: str = field(init=False, default=HUMAN_APPROVAL_REQUIRED)
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


__all__ = [
    "EventMessage",
    "DiagnosisComplete",
    "CodeFixProposed",
    "HumanApprovalRequired",
    "ApprovalGranted",
    "IssueResolved",
    "ISSUE_DETECTED",
    "DIAGNOSIS_COMPLETE",
    "CODE_FIX_PROPOSED",
    "HUMAN_APPROVAL_REQUIRED",
    "APPROVAL_GRANTED",
    "ISSUE_RESOLVED",
]
