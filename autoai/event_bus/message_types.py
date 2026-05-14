from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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

TESTS_FAILED = "TESTS_FAILED"
"""Event type emitted when verification tests fail."""

DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
"""Event type emitted when deployment fails."""

HUMAN_ARCHITECT_APPROVAL_REQUIRED = "HUMAN_ARCHITECT_APPROVAL_REQUIRED"
"""Event type emitted when an organizational change proposal requires human architect approval."""

SKILL_CREATED = "SKILL_CREATED"
"""Event type emitted when a new skill is registered."""

SKILL_REQUESTED = "SKILL_REQUESTED"
"""Event type emitted when an agent requests execution of a skill."""


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
class RecommendedSkill(TypedDict):
    """描述技能的元数据 suggestion."""

    name: str
    version: str
    parameters: dict[str, Any]


class DiagnosisDetails(TypedDict, total=False):
    """随:class:`DiagnosisComplete`包含的额外信息。"""

    recommended_skill: RecommendedSkill | None
    plugin: str | None
    # other 可选 fields such 作为``skill_search`` 或``metadata`` may appear


@dataclass(kw_only=True)
class DiagnosisComplete(EventMessage):
    """:data:`DIAGNOSIS_COMPLETE`事件的模式。"""

    summary: str
    actionable_recommendations: str
    details: DiagnosisDetails | None = None
    event_type: str = field(init=False, default=DIAGNOSIS_COMPLETE)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = {"recommended_skill": None, "plugin": None}
        else:
            self.details.setdefault("recommended_skill", None)
            self.details.setdefault("plugin", None)

        rec = self.details.get("recommended_skill")
        if isinstance(rec, dict):
            rec.setdefault("parameters", {})

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
class HumanArchitectApprovalRequired(EventMessage):
    """Schema for :data:`HUMAN_ARCHITECT_APPROVAL_REQUIRED` events.

    Expected payload fields:
        proposal_branch_name: Branch containing the organization change proposal.
        proposal_branch_url: Optional URL to view the branch/PR diff.
        rationale: Diagnosis and reasons produced by LLM.
        changes_summary: Short summary of proposed blueprint file changes.
    """

    proposal_branch_name: str
    proposal_branch_url: str | None = None
    rationale: str | None = None
    changes_summary: str | None = None
    event_type: str = field(init=False, default=HUMAN_ARCHITECT_APPROVAL_REQUIRED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "proposal_branch_name": self.proposal_branch_name,
            "proposal_branch_url": self.proposal_branch_url,
            "rationale": self.rationale,
            "changes_summary": self.changes_summary,
        }
        self.payload = {k: v for k, v in self.payload.items() if v is not None}


@dataclass(kw_only=True)
class TestsFailed(EventMessage):
    """:data:`TESTS_FAILED`事件的模式。"""

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
        approved_by: Identity of the approver.
        approval_timestamp: Timestamp when approval was granted.
    """

    branch_name: str
    commit_hash: str
    summary: str
    approved_by: str | None = None
    approval_timestamp: str | None = None
    event_type: str = field(init=False, default=APPROVAL_GRANTED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "branch_name": self.branch_name,
            "commit_hash": self.commit_hash,
            "summary": self.summary,
        }
        if self.approved_by is not None:
            self.payload["approved_by"] = self.approved_by
        if self.approval_timestamp is not None:
            self.payload["approval_timestamp"] = self.approval_timestamp


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
    """:data:`DEPLOYMENT_FAILED`事件的模式。"""

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


@dataclass(kw_only=True)
class SkillCreated(EventMessage):
    """Schema for :data:`SKILL_CREATED` events.

    Expected payload fields:
        skill_name: Name of the created skill.
        version: Version string of the skill.
        description: Short summary of what the skill does.
        tags: Optional list of categorisation tags.
        parameters: Optional parameter schema for the skill.
    """

    skill_name: str
    version: str
    description: str | None = None
    tags: list[str] | None = None
    parameters: dict[str, Any] | None = None
    event_type: str = field(init=False, default=SKILL_CREATED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "skill_name": self.skill_name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
        }
        self.payload = {k: v for k, v in self.payload.items() if v is not None}


@dataclass(kw_only=True)
class SkillRequested(EventMessage):
    """Schema for :data:`SKILL_REQUESTED` events.

    Expected payload fields:
        skill_name: Name of the requested skill.
        request_id: Optional identifier for the request.
        parameters: Parameters provided with the request.
        requester: Identifier of the requesting agent.
        context: Optional additional context for the request.
    """

    skill_name: str
    request_id: str | None = None
    parameters: dict[str, Any] | None = None
    requester: str | None = None
    context: dict[str, Any] | None = None
    event_type: str = field(init=False, default=SKILL_REQUESTED)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "skill_name": self.skill_name,
            "request_id": self.request_id,
            "parameters": self.parameters,
            "requester": self.requester,
            "context": self.context,
        }
        self.payload = {k: v for k, v in self.payload.items() if v is not None}


__all__ = [
    "EventMessage",
    "IssueDetected",
    "DiagnosisComplete",
    "CodeFixProposed",
    "HumanApprovalRequired",
    "HumanArchitectApprovalRequired",
    "TestsFailed",
    "ApprovalGranted",
    "IssueResolved",
    "DeploymentFailed",
    "SkillCreated",
    "SkillRequested",
    "ISSUE_DETECTED",
    "DIAGNOSIS_COMPLETE",
    "CODE_FIX_PROPOSED",
    "HUMAN_APPROVAL_REQUIRED",
    "HUMAN_ARCHITECT_APPROVAL_REQUIRED",
    "TESTS_FAILED",
    "APPROVAL_GRANTED",
    "ISSUE_RESOLVED",
    "DEPLOYMENT_FAILED",
    "SKILL_CREATED",
    "SKILL_REQUESTED",
]
