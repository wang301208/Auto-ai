from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EventMessage:
    """Event message passed through the event bus and message queue."""

    event_type: str
    payload: dict[str, Any] | str | None = None
    source_agent: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


DIAGNOSIS_COMPLETE = "DIAGNOSIS_COMPLETE"
"""Event type emitted when diagnostic analysis finishes."""

CODE_FIX_PROPOSED = "CODE_FIX_PROPOSED"
"""Event type emitted when a code fix has been proposed."""


@dataclass(kw_only=True)
class DiagnosisComplete(EventMessage):
    """Schema for :data:`DIAGNOSIS_COMPLETE` events."""

    summary: str
    actionable_recommendations: str
    event_type: str = field(init=False, default=DIAGNOSIS_COMPLETE)
    payload: dict[str, Any] | str | None = field(init=False)

    def __post_init__(self) -> None:
        self.payload = {
            "summary": self.summary,
            "actionable_recommendations": self.actionable_recommendations,
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


__all__ = [
    "EventMessage",
    "DiagnosisComplete",
    "CodeFixProposed",
    "DIAGNOSIS_COMPLETE",
    "CODE_FIX_PROPOSED",
]
