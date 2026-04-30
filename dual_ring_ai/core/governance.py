"""Local governance and permission gates for autonomous changes."""

from __future__ import annotations

import json
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
        request.status = decision
        request.decided_by = decided_by
        request.comments = comments
        request.decided_at = datetime.now(UTC).isoformat()
        self._save(request)
        return request

    def get_request(self, request_id: str) -> ApprovalRequest:
        path = self.requests_path / f"{request_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return ApprovalRequest(**data)

    def list_requests(self, status: str | None = None) -> list[ApprovalRequest]:
        requests: list[ApprovalRequest] = []
        for path in sorted(self.requests_path.glob("*.json")):
            request = ApprovalRequest(**json.loads(path.read_text(encoding="utf-8")))
            if status is None or request.status == status:
                requests.append(request)
        return requests

    def _save(self, request: ApprovalRequest) -> None:
        path = self.requests_path / f"{request.request_id}.json"
        path.write_text(
            json.dumps(asdict(request), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


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
            if not self._write_allowed(policy, path):
                return PermissionDecision(False, operation, "filesystem write denied")
        return PermissionDecision(True, operation, "allowed")

    def _write_allowed(self, policy: SandboxPolicy, path: str) -> bool:
        normalized = path.replace("\\", "/").strip()
        if normalized in {"", ".", "./"}:
            return False
        for allowed_root in policy.filesystem.get("write", []):
            allowed = allowed_root.replace("\\", "/").strip().rstrip("/")
            if allowed in {"workspace", "./workspace"} and (
                normalized == "workspace" or normalized.startswith("workspace/")
            ):
                return True
            if normalized == allowed or normalized.startswith(f"{allowed}/"):
                return True
        return False
