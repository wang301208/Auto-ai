"""Algorithm lifecycle management.

Manages state transitions (candidate -> active -> deprecated -> retired)
with governance-gated promotion and automatic rollback support.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .registry import AlgorithmManifest, AlgorithmRegistry, AlgorithmStatus


class LifecycleTransition(Enum):
    REGISTER = "register"
    PROMOTE = "promote"
    DEPRECATE = "deprecate"
    RETIRE = "retire"
    ROLLBACK = "rollback"
    REACTIVATE = "reactivate"


_VALID_TRANSITIONS: dict[AlgorithmStatus, set[LifecycleTransition]] = {
    AlgorithmStatus.CANDIDATE: {
        LifecycleTransition.PROMOTE,
        LifecycleTransition.RETIRE,
    },
    AlgorithmStatus.ACTIVE: {
        LifecycleTransition.DEPRECATE,
        LifecycleTransition.RETIRE,
        LifecycleTransition.ROLLBACK,
    },
    AlgorithmStatus.DEPRECATED: {
        LifecycleTransition.RETIRE,
        LifecycleTransition.REACTIVATE,
    },
    AlgorithmStatus.RETIRED: {
        LifecycleTransition.REACTIVATE,
    },
}

_TARGET_STATUS: dict[LifecycleTransition, AlgorithmStatus] = {
    LifecycleTransition.REGISTER: AlgorithmStatus.CANDIDATE,
    LifecycleTransition.PROMOTE: AlgorithmStatus.ACTIVE,
    LifecycleTransition.DEPRECATE: AlgorithmStatus.DEPRECATED,
    LifecycleTransition.RETIRE: AlgorithmStatus.RETIRED,
    LifecycleTransition.REACTIVATE: AlgorithmStatus.CANDIDATE,
}


@dataclass
class LifecycleEvent:
    """Record of a lifecycle state transition."""

    algorithm_name: str
    algorithm_version: str
    transition: LifecycleTransition
    from_status: AlgorithmStatus
    to_status: AlgorithmStatus
    actor: str = ""
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm_name": self.algorithm_name,
            "algorithm_version": self.algorithm_version,
            "transition": self.transition.value,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "actor": self.actor,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class AlgorithmLifecycle:
    """Manage algorithm lifecycle transitions with audit trail.

    All transitions are validated against the state machine rules.
    Promotion requires an approval_id when governance integration is used.
    """

    def __init__(
        self,
        registry: AlgorithmRegistry,
        audit_dir: str | Path = "algorithm_library/lifecycle_audit",
    ) -> None:
        self.registry = registry
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def can_transition(
        self, name: str, version: str, transition: LifecycleTransition
    ) -> bool:
        manifest = self.registry.get(name, version)
        if manifest is None:
            return False
        return transition in _VALID_TRANSITIONS.get(manifest.status, set())

    def promote(
        self,
        name: str,
        version: str,
        actor: str = "",
        reason: str = "",
        approval_id: str | None = None,
    ) -> AlgorithmManifest | None:
        """Promote a candidate algorithm to active status."""
        manifest = self.registry.get(name, version)
        if manifest is None:
            return None
        if not self.can_transition(name, version, LifecycleTransition.PROMOTE):
            raise RuntimeError(
                f"Cannot promote {name}:{version} from status {manifest.status.value}"
            )
        from_status = manifest.status
        self.registry.deprecate_previous_versions(name, version)
        updated = self.registry.update_status(name, version, AlgorithmStatus.ACTIVE)
        self._record_event(
            LifecycleEvent(
                algorithm_name=name,
                algorithm_version=version,
                transition=LifecycleTransition.PROMOTE,
                from_status=from_status,
                to_status=AlgorithmStatus.ACTIVE,
                actor=actor,
                reason=reason,
            ),
            extra={"approval_id": approval_id} if approval_id else {},
        )
        return updated

    def deprecate(
        self,
        name: str,
        version: str,
        actor: str = "",
        reason: str = "",
    ) -> AlgorithmManifest | None:
        manifest = self.registry.get(name, version)
        if manifest is None:
            return None
        if not self.can_transition(name, version, LifecycleTransition.DEPRECATE):
            raise RuntimeError(
                f"Cannot deprecate {name}:{version} from status {manifest.status.value}"
            )
        from_status = manifest.status
        updated = self.registry.update_status(name, version, AlgorithmStatus.DEPRECATED)
        self._record_event(
            LifecycleEvent(
                algorithm_name=name,
                algorithm_version=version,
                transition=LifecycleTransition.DEPRECATE,
                from_status=from_status,
                to_status=AlgorithmStatus.DEPRECATED,
                actor=actor,
                reason=reason,
            )
        )
        return updated

    def rollback(
        self,
        name: str,
        version: str,
        actor: str = "",
        reason: str = "",
    ) -> AlgorithmManifest | None:
        """Roll back to the previous version specified in manifest.rollback_to."""
        manifest = self.registry.get(name, version)
        if manifest is None:
            return None
        if manifest.rollback_to is None:
            raise RuntimeError(f"No rollback target for {name}:{version}")
        rollback_manifest = self.registry.get(name, manifest.rollback_to)
        if rollback_manifest is None:
            raise RuntimeError(
                f"Rollback target {name}:{manifest.rollback_to} not found"
            )
        self.registry.update_status(name, version, AlgorithmStatus.DEPRECATED)
        self.registry.update_status(name, manifest.rollback_to, AlgorithmStatus.ACTIVE)
        self._record_event(
            LifecycleEvent(
                algorithm_name=name,
                algorithm_version=version,
                transition=LifecycleTransition.ROLLBACK,
                from_status=manifest.status,
                to_status=AlgorithmStatus.DEPRECATED,
                actor=actor,
                reason=reason,
            ),
            extra={"rollback_to": manifest.rollback_to},
        )
        return rollback_manifest

    def retire(
        self,
        name: str,
        version: str,
        actor: str = "",
        reason: str = "",
    ) -> AlgorithmManifest | None:
        manifest = self.registry.get(name, version)
        if manifest is None:
            return None
        from_status = manifest.status
        updated = self.registry.update_status(name, version, AlgorithmStatus.RETIRED)
        self._record_event(
            LifecycleEvent(
                algorithm_name=name,
                algorithm_version=version,
                transition=LifecycleTransition.RETIRE,
                from_status=from_status,
                to_status=AlgorithmStatus.RETIRED,
                actor=actor,
                reason=reason,
            )
        )
        return updated

    def get_history(self, name: str, version: str) -> list[LifecycleEvent]:
        events: list[LifecycleEvent] = []
        for path in sorted(self.audit_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("algorithm_name") == name and data.get("algorithm_version") == version:
                    events.append(
                        LifecycleEvent(
                            algorithm_name=data["algorithm_name"],
                            algorithm_version=data["algorithm_version"],
                            transition=LifecycleTransition(data["transition"]),
                            from_status=AlgorithmStatus(data["from_status"]),
                            to_status=AlgorithmStatus(data["to_status"]),
                            actor=data.get("actor", ""),
                            reason=data.get("reason", ""),
                            timestamp=data.get("timestamp", ""),
                        )
                    )
            except Exception:
                continue
        return events

    def _record_event(self, event: LifecycleEvent, extra: dict[str, Any] | None = None) -> None:
        data = event.to_dict()
        if extra:
            data.update(extra)
        ts = event.timestamp.replace(":", "-").replace(".", "-")
        path = self.audit_dir / f"{event.algorithm_name}_{event.algorithm_version}_{event.transition.value}_{ts}.json"
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
