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


__all__ = ["EventMessage", "DiagnosisComplete", "DIAGNOSIS_COMPLETE"]
