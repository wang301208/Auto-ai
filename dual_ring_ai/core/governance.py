"""Local governance and permission gates for autonomous changes."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .skill_lifecycle import SandboxPolicy


@dataclass
class ApprovalRequest:
    request_id: str
    request_type: str
    title: str
    payload: dict[str, Any]
    requested_by: str
    risk_level: str
    status: str
    created_at: str
    decided_at: str | None = None
    decided_by: str | None = None
    comments: str | None = None
    execution_status: str | None = None
    executed_at: str | None = None
    execution_error: str | None = None


@dataclass
class PermissionDecision:
    allowed: bool
    operation: str
    reason: str


class GovernanceStore:
    """Filesystem-backed approval queue."""

    def __init__(self, root_path: str | Path = "governance") -> None:
        self.root_path = Path(root_path)
        self.requests_path = self.root_path / "requests"
        self.requests_path.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.requests_path / ".write.lock"

    def create_request(
        self,
        request_type: str,
        title: str,
        payload: dict[str, Any],
        requested_by: str,
        risk_level: str,
    ) -> ApprovalRequest:
        created_at = datetime.now(UTC).isoformat()
        request_id = f"approval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"
        request = ApprovalRequest(
            request_id=request_id,
            request_type=request_type,
            title=title,
            payload=payload,
            requested_by=requested_by,
            risk_level=risk_level,
            status="pending",
            created_at=created_at,
        )
        self._save(request)
        return request

    def decide(
        self,
        request_id: str,
        decision: str,
        decided_by: str,
        comments: str = "",
    ) -> ApprovalRequest:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be 'approved' or 'rejected'")
        request = self.get_request(request_id)
        if request.status != "pending":
            raise ValueError(f"approval request is already decided: {request_id}")
        request.status = decision
        request.decided_by = decided_by
        request.comments = comments
        request.decided_at = datetime.now(UTC).isoformat()
        self._save(request)
        return request

    def get_request(self, request_id: str) -> ApprovalRequest:
        path = self.requests_path / f"{request_id}.json"
        if not path.exists():
            raise ValueError(f"approval request not found: {request_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ApprovalRequest(**data)

    def list_requests(self, status: str | None = None) -> list[ApprovalRequest]:
        requests: list[ApprovalRequest] = []
        for path in sorted(self.requests_path.glob("*.json")):
            try:
                request = ApprovalRequest(**json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, TypeError, ValueError):
                corrupt_path = path.with_suffix(".json.corrupt")
                if corrupt_path.exists():
                    corrupt_path = path.with_name(
                        f"{path.stem}.{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}.json.corrupt"
                    )
                path.replace(corrupt_path)
                continue
            if status is None or request.status == status:
                requests.append(request)
        return requests

    def mark_execution(
        self,
        request_id: str,
        status: str,
        error: str | None = None,
    ) -> ApprovalRequest:
        if status not in {"executed", "failed"}:
            raise ValueError("execution status must be 'executed' or 'failed'")
        request = self.get_request(request_id)
        if request.execution_status == "executed":
            raise ValueError(f"approval request is already executed: {request_id}")
        request.execution_status = status
        request.executed_at = datetime.now(UTC).isoformat()
        request.execution_error = error
        self._save(request)
        return request

    def _save(self, request: ApprovalRequest) -> None:
        path = self.requests_path / f"{request.request_id}.json"
        payload = json.dumps(asdict(request), ensure_ascii=False, indent=2)
        temp_path = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        self._acquire_write_lock()
        try:
            temp_path.write_text(payload, encoding="utf-8")
            temp_path.replace(path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
            self._release_write_lock()

    def _acquire_write_lock(self, timeout_seconds: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"governance write lock timed out: {self.lock_path}")
                time.sleep(0.02)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(f"{os.getpid()} {datetime.now(UTC).isoformat()}\n")
            return

    def _release_write_lock(self) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass


class PermissionGate:
    """Evaluate requested operations against a sandbox policy."""

    def evaluate(
        self, policy: SandboxPolicy, operation: str, context: dict[str, Any]
    ) -> PermissionDecision:
        if operation == "network" and not policy.network:
            return PermissionDecision(False, operation, "network access denied")
        if operation == "shell" and not policy.shell:
            return PermissionDecision(False, operation, "shell access denied")
        if operation == "filesystem.write":
            path = str(context.get("path", ""))
            if not self._path_allowed(policy.filesystem.get("write", []), path):
                return PermissionDecision(False, operation, "filesystem write denied")
        if operation == "filesystem.read":
            path = str(context.get("path", ""))
            if not self._path_allowed(policy.filesystem.get("read", []), path):
                return PermissionDecision(False, operation, "filesystem read denied")
        if operation == "environment.read":
            name = str(context.get("name", ""))
            allowed_env = policy.environment.get("allow", [])
            if "*" not in allowed_env and name not in allowed_env:
                return PermissionDecision(False, operation, "environment access denied")
        return PermissionDecision(True, operation, "allowed")

    def _path_allowed(self, allowed_roots: list[str], path: str) -> bool:
        normalized = path.replace("\\", "/").strip()
        if normalized in {"", ".", "./"}:
            return False
        for allowed_root in allowed_roots:
            allowed = allowed_root.replace("\\", "/").strip().rstrip("/")
            if allowed == "*":
                return True
            if allowed in {"workspace", "./workspace"} and (
                normalized == "workspace" or normalized.startswith("workspace/")
            ):
                return True
            if allowed in {".", "./"}:
                return True
            if normalized == allowed or normalized.startswith(f"{allowed}/"):
                return True
        return False
