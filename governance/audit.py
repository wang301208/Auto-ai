"""Audit logging for governance events.

Records policy decisions, approval actions, rate limit events,
and quota changes with structured JSON logging.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class AuditEventType(Enum):
    POLICY_EVAL = "policy_eval"
    RATE_LIMITED = "rate_limited"
    QUOTA_CHECKED = "quota_checked"
    QUOTA_EXCEEDED = "quota_exceeded"
    OPERATION_EXECUTED = "operation_executed"
    OPERATION_BLOCKED = "operation_blocked"
    AUTONOMOUS_OVERRIDE = "autonomous_override"
    POLICY_AUTO_ADJUSTED = "policy_auto_adjusted"
    BOUNDARY_SET = "boundary_set"
    BOUNDARY_ADJUST = "boundary_adjust"
    BOUNDARY_BREAK = "boundary_break"
    APPROVAL_CREATED = "approval_created"
    APPROVAL_DECIDED = "approval_decided"


@dataclass
class AuditEntry:
    """A single audit log entry."""

    timestamp: str = ""
    event_type: AuditEventType | str = AuditEventType.OPERATION_EXECUTED
    principal: str = ""
    operation: str = ""
    resource: str = ""
    decision: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.event_type, AuditEventType):
            self.event_type = self.event_type.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type if isinstance(self.event_type, str) else self.event_type.value,
            "principal": self.principal,
            "operation": self.operation,
            "resource": self.resource,
            "decision": self.decision,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEntry:
        return cls(
            timestamp=data.get("timestamp", ""),
            event_type=data.get("event_type", "operation_executed"),
            principal=data.get("principal", ""),
            operation=data.get("operation", ""),
            resource=data.get("resource", ""),
            decision=data.get("decision", ""),
            details=data.get("details", {}),
        )


class AuditLog:
    """Append-only structured audit log backed by a JSONL file.

    Thread-safe for concurrent writes.
    """

    def __init__(self, log_path: str | Path = "governance/audit.jsonl") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        event_type: AuditEventType,
        principal: str = "",
        operation: str = "",
        resource: str = "",
        decision: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            event_type=event_type,
            principal=principal,
            operation=operation,
            resource=resource,
            decision=decision,
            details=details or {},
        )
        self._append(entry)
        return entry

    def query(
        self,
        event_type: AuditEventType | None = None,
        principal: str | None = None,
        operation: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results: list[AuditEntry] = []
        if not self.log_path.exists():
            return results
        with self._lock:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                entry = AuditEntry.from_dict(data)
            except Exception:
                continue
            if event_type is not None:
                expected = event_type.value if isinstance(event_type, AuditEventType) else event_type
                if entry.event_type != expected:
                    continue
            if principal is not None and entry.principal != principal:
                continue
            if operation is not None and entry.operation != operation:
                continue
            if since is not None and entry.timestamp < since:
                continue
            if until is not None and entry.timestamp > until:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return list(reversed(results))

    def _append(self, entry: AuditEntry) -> None:
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
