"""Approval workflow (DEPRECATED: retained for backward compatibility).

In the autonomous boundary management model, approval workflows are replaced
by break logs. ApprovalStore is kept for data migration and existing audit
log queries, but no new approval decisions should be created at runtime.

Use governance.break_log.BreakLog and governance.boundary_manager.BoundaryManager
instead.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """A governance approval request."""

    request_id: str
    request_type: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    requested_by: str = ""
    risk_level: str = "medium"
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = ""
    expires_at: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None
    comments: str | None = None
    execution_status: str | None = None
    execution_error: str | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.status, str):
            self.status = ApprovalStatus(self.status)

    def is_decided(self) -> bool:
        return self.status not in {
            ApprovalStatus.PENDING,
            ApprovalStatus.CANCELLED,
        }

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc).isoformat() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        d = {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "title": self.title,
            "payload": self.payload,
            "requested_by": self.requested_by,
            "risk_level": self.risk_level,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "comments": self.comments,
            "execution_status": self.execution_status,
            "execution_error": self.execution_error,
        }
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRequest:
        return cls(
            request_id=data["request_id"],
            request_type=data["request_type"],
            title=data["title"],
            payload=data.get("payload", {}),
            requested_by=data.get("requested_by", ""),
            risk_level=data.get("risk_level", "medium"),
            status=data.get("status", "pending"),
            expires_at=data.get("expires_at"),
            decided_at=data.get("decided_at"),
            decided_by=data.get("decided_by"),
            comments=data.get("comments"),
            execution_status=data.get("execution_status"),
            execution_error=data.get("execution_error"),
        )


class ApprovalStore:
    """Persistent approval queue backed by JSON files.

    Thread-safe via file-based locking and atomic writes.
    """

    def __init__(self, store_dir: str | Path = "governance/requests") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def create_request(
        self,
        request_type: str,
        title: str,
        payload: dict[str, Any] | None = None,
        requested_by: str = "",
        risk_level: str = "medium",
        ttl_seconds: float | None = None,
    ) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        request_id = f"approval_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond}"
        expires_at = None
        if ttl_seconds is not None:
            from datetime import timedelta
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()

        req = ApprovalRequest(
            request_id=request_id,
            request_type=request_type,
            title=title,
            payload=payload or {},
            requested_by=requested_by,
            risk_level=risk_level,
            expires_at=expires_at,
        )
        self._save(req)
        return req

    def decide(
        self,
        request_id: str,
        decision: ApprovalStatus,
        decided_by: str = "",
        comments: str | None = None,
    ) -> ApprovalRequest:
        if decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError(f"Invalid decision: {decision}")
        req = self.get_request(request_id)
        if req is None:
            raise FileNotFoundError(f"Request not found: {request_id}")
        if req.is_decided():
            raise RuntimeError(f"Request already decided: {req.status.value}")
        req.status = decision
        req.decided_at = datetime.now(timezone.utc).isoformat()
        req.decided_by = decided_by
        req.comments = comments
        self._save(req)
        return req

    def mark_execution(
        self,
        request_id: str,
        success: bool,
        error: str | None = None,
    ) -> ApprovalRequest:
        req = self.get_request(request_id)
        if req is None:
            raise FileNotFoundError(f"Request not found: {request_id}")
        req.execution_status = "executed" if success else "failed"
        if error:
            req.execution_error = error
        self._save(req)
        return req

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        path = self.store_dir / f"{request_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ApprovalRequest.from_dict(data)
        except Exception:
            return None

    def list_requests(
        self,
        status: ApprovalStatus | None = None,
        request_type: str | None = None,
    ) -> list[ApprovalRequest]:
        results: list[ApprovalRequest] = []
        for path in sorted(self.store_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                req = ApprovalRequest.from_dict(data)
            except Exception:
                continue
            if status is not None and req.status != status:
                continue
            if request_type is not None and req.request_type != request_type:
                continue
            results.append(req)
        return results

    def expire_pending(self) -> list[str]:
        expired_ids: list[str] = []
        for req in self.list_requests(status=ApprovalStatus.PENDING):
            if req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                self._save(req)
                expired_ids.append(req.request_id)
        return expired_ids

    def _save(self, req: ApprovalRequest) -> None:
        with self._lock:
            path = self.store_dir / f"{req.request_id}.json"
            data = json.dumps(req.to_dict(), indent=2, ensure_ascii=False)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.store_dir), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(data)
                os.replace(tmp_path, str(path))
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
