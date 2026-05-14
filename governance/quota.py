"""Quota management for resource consumption limits.

Tracks and enforces usage quotas for API calls, token consumption,
file operations, and other measurable resources per principal/scope.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class QuotaScope(Enum):
    GLOBAL = "global"
    PRINCIPAL = "principal"
    OPERATION = "operation"
    PRINCIPAL_OPERATION = "principal_operation"


class QuotaExceededError(RuntimeError):
    """Raised when a quota would be exceeded."""

    def __init__(
        self,
        resource: str,
        current: float,
        limit: float,
        scope_key: str,
    ) -> None:
        self.resource = resource
        self.current = current
        self.limit = limit
        self.scope_key = scope_key
        super().__init__(
            f"Quota exceeded for '{resource}' in scope '{scope_key}': "
            f"current={current:.2f}, limit={limit:.2f}"
        )


@dataclass
class QuotaDefinition:
    """Definition of a resource quota.

    Attributes:
        resource: Name of the resource being limited (e.g. "api_calls", "tokens", "file_writes").
        limit: Maximum allowed usage within the period.
        period_seconds: Duration of the quota period; None for lifetime quotas.
        scope: Granularity of the quota scope.
        operation: Optional operation pattern for operation-scoped quotas.
        principal: Optional principal pattern for principal-scoped quotas.
    """

    resource: str
    limit: float
    period_seconds: float | None = None
    scope: QuotaScope = QuotaScope.PRINCIPAL
    operation: str | None = None
    principal: str | None = None


@dataclass
class QuotaUsage:
    """Current usage record for a quota bucket."""

    scope_key: str
    resource: str
    used: float = 0.0
    period_start: str = ""
    period_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.period_start:
            self.period_start = datetime.now(timezone.utc).isoformat()

    def is_period_expired(self) -> bool:
        if self.period_seconds is None:
            return False
        start = datetime.fromisoformat(self.period_start)
        now = datetime.now(timezone.utc)
        return (now - start).total_seconds() >= self.period_seconds

    def reset_period(self) -> None:
        self.used = 0.0
        self.period_start = datetime.now(timezone.utc).isoformat()


class QuotaManager:
    """Track and enforce resource quotas across scopes.

    Thread-safe. Usage is persisted to a JSON file for durability.
    """

    def __init__(
        self,
        store_path: str | Path = "governance/quotas.json",
    ) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._definitions: dict[str, QuotaDefinition] = {}
        self._usage: dict[str, QuotaUsage] = {}
        self._lock = threading.Lock()
        self._load()

    def define_quota(self, definition: QuotaDefinition) -> None:
        key = definition.resource
        self._definitions[key] = definition

    def _scope_key(
        self,
        definition: QuotaDefinition,
        principal: str = "",
        operation: str = "",
    ) -> str:
        parts = [definition.resource]
        if definition.scope in {
            QuotaScope.PRINCIPAL,
            QuotaScope.PRINCIPAL_OPERATION,
        }:
            parts.append(principal or definition.principal or "*")
        if definition.scope in {
            QuotaScope.OPERATION,
            QuotaScope.PRINCIPAL_OPERATION,
        }:
            parts.append(operation or definition.operation or "*")
        return ":".join(parts)

    def check(
        self,
        resource: str,
        amount: float = 1.0,
        principal: str = "",
        operation: str = "",
    ) -> bool:
        definition = self._definitions.get(resource)
        if definition is None:
            return True
        with self._lock:
            key = self._scope_key(definition, principal, operation)
            usage = self._usage.get(key)
            if usage is None or usage.is_period_expired():
                usage = QuotaUsage(
                    scope_key=key,
                    resource=resource,
                    period_seconds=definition.period_seconds,
                )
                self._usage[key] = usage
            return usage.used + amount <= definition.limit

    def consume(
        self,
        resource: str,
        amount: float = 1.0,
        principal: str = "",
        operation: str = "",
    ) -> float:
        definition = self._definitions.get(resource)
        if definition is None:
            return float("inf")
        with self._lock:
            key = self._scope_key(definition, principal, operation)
            usage = self._usage.get(key)
            if usage is None or usage.is_period_expired():
                usage = QuotaUsage(
                    scope_key=key,
                    resource=resource,
                    period_seconds=definition.period_seconds,
                )
                self._usage[key] = usage
            remaining = definition.limit - usage.used
            if remaining < amount:
                raise QuotaExceededError(
                    resource=resource,
                    current=usage.used,
                    limit=definition.limit,
                    scope_key=key,
                )
            usage.used += amount
            self._save()
            return definition.limit - usage.used

    def get_usage(
        self,
        resource: str,
        principal: str = "",
        operation: str = "",
    ) -> tuple[float, float]:
        definition = self._definitions.get(resource)
        if definition is None:
            return 0.0, float("inf")
        key = self._scope_key(definition, principal, operation)
        usage = self._usage.get(key)
        if usage is None:
            return 0.0, definition.limit
        return usage.used, definition.limit

    def _save(self) -> None:
        data = {
            key: {
                "scope_key": u.scope_key,
                "resource": u.resource,
                "used": u.used,
                "period_start": u.period_start,
                "period_seconds": u.period_seconds,
            }
            for key, u in self._usage.items()
        }
        self.store_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            for key, val in data.items():
                self._usage[key] = QuotaUsage(
                    scope_key=val["scope_key"],
                    resource=val["resource"],
                    used=val.get("used", 0.0),
                    period_start=val.get("period_start", ""),
                    period_seconds=val.get("period_seconds"),
                )
        except Exception:
            pass
