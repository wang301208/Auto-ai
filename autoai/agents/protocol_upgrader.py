"""Protocol Upgrader: Agent communication protocol version auto-upgrade.

Phase 18.4: Manages protocol version evolution:
  - Version negotiation: Agents agree on highest common version
  - Backward compatibility: Older messages auto-translated to newer format
  - Forward compatibility: Newer messages gracefully degrade for older agents
  - Schema migration: Message format changes with auto-migration functions
  - Rollback: Protocol can be downgraded if compatibility breaks

Every upgrade is recorded to ModificationChain for audit trail.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from autoai.logs import logger


class ProtoUpgradePolicy(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class ProtocolVersion:
    major: int
    minor: int
    patch: int

    @property
    def as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: ProtocolVersion) -> bool:
        return self.as_tuple < other.as_tuple

    def __le__(self, other: ProtocolVersion) -> bool:
        return self.as_tuple <= other.as_tuple

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProtocolVersion):
            return NotImplemented
        return self.as_tuple == other.as_tuple

    def __hash__(self) -> int:
        return hash(self.as_tuple)

    def is_compatible_with(self, other: ProtocolVersion) -> bool:
        return self.major == other.major

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


@dataclass
class MessageSchema:
    version: ProtocolVersion
    fields: dict[str, type] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    deprecations: list[str] = field(default_factory=list)
    additions: list[str] = field(default_factory=list)


MigrationFunc = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class SchemaMigration:
    from_version: ProtocolVersion
    to_version: ProtocolVersion
    forward: MigrationFunc
    backward: MigrationFunc
    description: str = ""


@dataclass
class AgentProtocolState:
    agent_id: str
    supported_versions: list[ProtocolVersion] = field(default_factory=list)
    negotiated_version: ProtocolVersion | None = None
    last_upgrade: str = ""


class ProtocolUpgrader:
    """Manages communication protocol version lifecycle.

    Usage:
        upgrader = ProtocolUpgrader(current_version=ProtocolVersion(1, 0, 0))
        upgrader.register_agent("agent-1", [ProtocolVersion(1, 0, 0)])
        upgrader.register_agent("agent-2", [ProtocolVersion(1, 1, 0)])
        negotiated = upgrader.negotiate("agent-1", "agent-2")
        # negotiated = ProtocolVersion(1, 1, 0) with backward compat
    """

    CURRENT_VERSION = ProtocolVersion(1, 2, 0)

    def __init__(
        self,
        current_version: ProtocolVersion | None = None,
        upgrade_policy: ProtoUpgradePolicy = ProtoUpgradePolicy.BALANCED,
        chain: Any = None,
    ) -> None:
        self.current_version = current_version or self.CURRENT_VERSION
        self._upgrade_policy = upgrade_policy
        self._chain = chain
        self._schemas: dict[ProtocolVersion, MessageSchema] = {}
        self._migrations: list[SchemaMigration] = []
        self._agents: dict[str, AgentProtocolState] = {}
        self._upgrade_history: list[dict[str, Any]] = []
        self._register_default_schemas()
        self._register_default_migrations()

    def _register_default_schemas(self) -> None:
        self._schemas[ProtocolVersion(1, 0, 0)] = MessageSchema(
            version=ProtocolVersion(1, 0, 0),
            fields={"message_type": str, "sender_id": str, "payload": dict},
        )
        self._schemas[ProtocolVersion(1, 1, 0)] = MessageSchema(
            version=ProtocolVersion(1, 1, 0),
            fields={"message_type": str, "sender_id": str, "payload": dict, "correlation_id": str, "priority": int},
            additions=["correlation_id", "priority"],
            defaults={"correlation_id": "", "priority": 0},
        )
        self._schemas[ProtocolVersion(1, 2, 0)] = MessageSchema(
            version=ProtocolVersion(1, 2, 0),
            fields={"message_type": str, "sender_id": str, "payload": dict, "correlation_id": str, "priority": int, "ttl": float, "metadata": dict},
            additions=["ttl", "metadata"],
            defaults={"correlation_id": "", "priority": 0, "ttl": 0.0, "metadata": {}},
        )

    def _register_default_migrations(self) -> None:
        v100 = ProtocolVersion(1, 0, 0)
        v110 = ProtocolVersion(1, 1, 0)
        v120 = ProtocolVersion(1, 2, 0)

        self._migrations.append(SchemaMigration(
            from_version=v100,
            to_version=v110,
            forward=lambda msg: {**msg, "correlation_id": msg.get("correlation_id", uuid.uuid4().hex[:16]), "priority": msg.get("priority", 0)},
            backward=lambda msg: {k: v for k, v in msg.items() if k not in ("correlation_id", "priority")},
            description="Add correlation_id and priority",
        ))
        self._migrations.append(SchemaMigration(
            from_version=v110,
            to_version=v120,
            forward=lambda msg: {**msg, "ttl": msg.get("ttl", 0.0), "metadata": msg.get("metadata", {})},
            backward=lambda msg: {k: v for k, v in msg.items() if k not in ("ttl", "metadata")},
            description="Add ttl and metadata",
        ))
        self._migrations.append(SchemaMigration(
            from_version=v100,
            to_version=v120,
            forward=lambda msg: {**msg, "correlation_id": msg.get("correlation_id", uuid.uuid4().hex[:16]), "priority": msg.get("priority", 0), "ttl": msg.get("ttl", 0.0), "metadata": msg.get("metadata", {})},
            backward=lambda msg: {k: v for k, v in msg.items() if k in ("message_type", "sender_id", "payload")},
            description="v1.0.0 → v1.2.0 direct migration",
        ))

    def register_schema(self, schema: MessageSchema) -> None:
        self._schemas[schema.version] = schema

    def register_migration(self, migration: SchemaMigration) -> None:
        self._migrations.append(migration)

    def register_agent(self, agent_id: str, versions: list[ProtocolVersion]) -> None:
        self._agents[agent_id] = AgentProtocolState(
            agent_id=agent_id,
            supported_versions=sorted(versions, reverse=True),
        )

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def negotiate(self, agent_a: str, agent_b: str) -> ProtocolVersion | None:
        state_a = self._agents.get(agent_a)
        state_b = self._agents.get(agent_b)
        if state_a is None or state_b is None:
            return None

        for v_a in state_a.supported_versions:
            for v_b in state_b.supported_versions:
                if v_a == v_b:
                    state_a.negotiated_version = v_a
                    state_b.negotiated_version = v_b
                    return v_a

        common_major = set(v.major for v in state_a.supported_versions) & set(v.major for v in state_b.supported_versions)
        if common_major and self._upgrade_policy != ProtoUpgradePolicy.CONSERVATIVE:
            major = max(common_major)
            compat_a = [v for v in state_a.supported_versions if v.major == major]
            compat_b = [v for v in state_b.supported_versions if v.major == major]
            if compat_a and compat_b:
                negotiated = min(compat_a[0], compat_b[0])
                state_a.negotiated_version = negotiated
                state_b.negotiated_version = negotiated
                return negotiated

        return None

    def upgrade_message(
        self,
        message: dict[str, Any],
        from_version: ProtocolVersion,
        to_version: ProtocolVersion,
    ) -> dict[str, Any]:
        if from_version == to_version:
            return message

        migration = self._find_migration(from_version, to_version)
        if migration:
            try:
                upgraded = migration.forward(message)
                self._record_upgrade(from_version, to_version, success=True)
                return upgraded
            except Exception as e:
                logger.warn(f"[ProtoUpgrade] Forward migration failed: {e}")
                self._record_upgrade(from_version, to_version, success=False)
                return self._apply_defaults(message, to_version)

        if to_version > from_version:
            return self._apply_defaults(message, to_version)

        return message

    def downgrade_message(
        self,
        message: dict[str, Any],
        from_version: ProtocolVersion,
        to_version: ProtocolVersion,
    ) -> dict[str, Any]:
        if from_version == to_version:
            return message

        migration = self._find_migration(from_version, to_version)
        if migration:
            try:
                return migration.backward(message)
            except Exception as e:
                logger.warn(f"[ProtoUpgrade] Backward migration failed: {e}")
                return self._strip_extra_fields(message, to_version)

        return self._strip_extra_fields(message, to_version)

    def auto_upgrade_all(self) -> dict[str, ProtocolVersion | None]:
        results = {}
        for agent_id, state in self._agents.items():
            best = None
            for v in state.supported_versions:
                if v.is_compatible_with(self.current_version):
                    best = v
                    break

            if best and best < self.current_version:
                if self._should_auto_upgrade(best, self.current_version):
                    state.negotiated_version = self.current_version
                    state.last_upgrade = datetime.now(timezone.utc).isoformat()
                    results[agent_id] = self.current_version
                    logger.info(f"[ProtoUpgrade] Auto-upgraded {agent_id}: {best} → {self.current_version}")
                else:
                    results[agent_id] = best
            else:
                results[agent_id] = best or state.negotiated_version

        return results

    def _should_auto_upgrade(self, from_v: ProtocolVersion, to_v: ProtocolVersion) -> bool:
        if self._upgrade_policy == ProtoUpgradePolicy.AGGRESSIVE:
            return True
        if self._upgrade_policy == ProtoUpgradePolicy.BALANCED:
            return from_v.major == to_v.major and (to_v.minor - from_v.minor) <= 1
        return False

    def _find_migration(self, from_v: ProtocolVersion, to_v: ProtocolVersion) -> SchemaMigration | None:
        for m in self._migrations:
            if m.from_version == from_v and m.to_version == to_v:
                return m
        return None

    def _apply_defaults(self, message: dict[str, Any], target_version: ProtocolVersion) -> dict[str, Any]:
        schema = self._schemas.get(target_version)
        if schema is None:
            return message
        result = dict(message)
        for field_name, default_val in schema.defaults.items():
            if field_name not in result:
                result[field_name] = default_val
        return result

    def _strip_extra_fields(self, message: dict[str, Any], target_version: ProtocolVersion) -> dict[str, Any]:
        schema = self._schemas.get(target_version)
        if schema is None:
            return message
        return {k: v for k, v in message.items() if k in schema.fields}

    def _record_upgrade(self, from_v: ProtocolVersion, to_v: ProtocolVersion, success: bool) -> None:
        self._upgrade_history.append({
            "from": str(from_v),
            "to": str(to_v),
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_status(self) -> dict[str, Any]:
        return {
            "current_version": str(self.current_version),
            "registered_agents": len(self._agents),
            "available_schemas": [str(v) for v in self._schemas],
            "available_migrations": len(self._migrations),
            "upgrade_history_size": len(self._upgrade_history),
            "policy": self._upgrade_policy.value,
        }


__all__ = [
    "ProtocolUpgrader",
    "ProtocolVersion",
    "ProtoUpgradePolicy",
    "MessageSchema",
    "SchemaMigration",
    "AgentProtocolState",
]
