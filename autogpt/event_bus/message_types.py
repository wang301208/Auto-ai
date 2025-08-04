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
