"""Autonomous Spawner: Agent decides when and how to create/destroy sub-agents.

The radical evolution of agent_factory: instead of humans writing
agents_fleet.json, the main agent autonomously decides:
    - "I have too many tasks" → spawn a specialist sub-agent
    - "This sub-agent is done" → reclaim its resources
    - "I need a role I don't have" → recruit (create) that role

This is L4 (SELF_SPAWN) autonomy. Below L4, spawning is blocked.

Spawn decisions are based on:
    - Task queue length vs capacity
    - Task type distribution (need specialists for unrepresented types)
    - Current agent load (CPU/memory estimate)
    - Historical spawn effectiveness
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from governance.autonomy_level import AutonomyLevel, AutonomyManager


class SpawnReason(Enum):
    OVERLOADED = "overloaded"
    MISSING_ROLE = "missing_role"
    SPECIALIST_NEEDED = "specialist_needed"
    PEAK_LOAD = "peak_load"


class DestroyReason(Enum):
    IDLE = "idle"
    TASK_COMPLETE = "task_complete"
    RESOURCE_PRESSURE = "resource_pressure"
    CONSOLIDATION = "consolidation"


@dataclass
class SpawnRecord:
    child_id: str
    role: str
    reason: SpawnReason
    timestamp: str
    task_count_at_spawn: int = 0
    tasks_assigned: int = 0
    tasks_completed: int = 0


@dataclass
class RoleTemplate:
    role: str
    capabilities: set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    typical_task_types: set[str] = field(default_factory=set)


BUILTIN_ROLE_TEMPLATES: dict[str, RoleTemplate] = {
    "reviewer": RoleTemplate(
        role="reviewer",
        capabilities={"review", "approve", "lint"},
        typical_task_types={"lint", "review"},
    ),
    "tester": RoleTemplate(
        role="tester",
        capabilities={"test", "debug", "verify"},
        typical_task_types={"test", "verify"},
    ),
    "fixer": RoleTemplate(
        role="fixer",
        capabilities={"fix", "patch", "refactor"},
        typical_task_types={"bug", "fix", "refactor"},
    ),
    "security": RoleTemplate(
        role="security",
        capabilities={"security_audit", "vulnerability_scan", "compliance"},
        typical_task_types={"security", "compliance"},
    ),
    "perf": RoleTemplate(
        role="perf",
        capabilities={"profile", "optimize", "benchmark"},
        typical_task_types={"perf", "optimize"},
    ),
    "deployer": RoleTemplate(
        role="deployer",
        capabilities={"deploy", "ci_cd", "monitor"},
        typical_task_types={"deploy", "ci_cd"},
    ),
}


class AutonomousSpawner:
    """Agent-autonomous sub-agent creation and destruction.

    Gated by AutonomyLevel >= SELF_SPAWN (L4).
    Below L4, spawn requests return None with a reason.

    Usage:
        spawner = AutonomousSpawner(
            autonomy=autonomy_mgr,
            factory=agent_factory,
        )
        child_id = spawner.evaluate_and_spawn(task_queue, current_roles)
        # If overloaded and L4+, automatically creates a sub-代理
    """

    def __init__(
        self,
        autonomy: AutonomyManager,
        factory: Any | None = None,
        max_children: int = 10,
        overload_threshold: int = 15,
        idle_timeout_seconds: float = 300.0,
        role_templates: dict[str, RoleTemplate] | None = None,
    ) -> None:
        self._autonomy = autonomy
        self._factory = factory
        self._max_children = max_children
        self._overload_threshold = overload_threshold
        self._idle_timeout = idle_timeout_seconds
        self._role_templates = role_templates or BUILTIN_ROLE_TEMPLATES
        self._children: dict[str, SpawnRecord] = {}
        self._spawn_count: int = 0
        self._destroy_count: int = 0
        self._next_id: int = 1

    @property
    def can_spawn(self) -> bool:
        return self._autonomy.level >= AutonomyLevel.SELF_SPAWN

    @property
    def children(self) -> dict[str, SpawnRecord]:
        return dict(self._children)

    @property
    def child_count(self) -> int:
        return len(self._children)

    def evaluate_and_spawn(
        self,
        task_queue: list[Any],
        current_roles: set[str],
        current_load: float = 0.0,
    ) -> str | None:
        """Evaluate whether to spawn a sub-agent, and spawn if needed.

        Returns child agent_id if spawned, None otherwise.
        """
        if not self.can_spawn:
            return None
        if self.child_count >= self._max_children:
            return None

        reason, role = self._evaluate_need(task_queue, current_roles, current_load)
        if reason is None:
            return None

        return self._spawn(role, reason, len(task_queue))

    def _evaluate_need(
        self,
        task_queue: list[Any],
        current_roles: set[str],
        current_load: float,
    ) -> tuple[SpawnReason | None, str]:
        if len(task_queue) > self._overload_threshold:
            needed_role = self._find_needed_role(task_queue, current_roles)
            if needed_role:
                return SpawnReason.MISSING_ROLE, needed_role
            busiest_role = self._find_busiest_role(task_queue)
            return SpawnReason.OVERLOADED, busiest_role

        if current_load > 0.8:
            return SpawnReason.PEAK_LOAD, "fixer"

        task_types = self._extract_task_types(task_queue)
        for ttype in task_types:
            for rname, tmpl in self._role_templates.items():
                if ttype in tmpl.typical_task_types and rname not in current_roles:
                    return SpawnReason.SPECIALIST_NEEDED, rname

        return None, ""

    def _spawn(self, role: str, reason: SpawnReason, task_count: int) -> str:
        child_id = f"child_{self._next_id}"
        self._next_id += 1
        self._spawn_count += 1

        record = SpawnRecord(
            child_id=child_id,
            role=role,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_count_at_spawn=task_count,
        )
        self._children[child_id] = record

        if self._factory is not None:
            try:
                from .agent_factory import AgentSpec
                tmpl = self._role_templates.get(role, RoleTemplate(role=role))
                spec = AgentSpec(
                    agent_id=child_id,
                    name=f"Auto-{role.title()}",
                    role=role,
                    roles={role},
                    capabilities=tmpl.capabilities,
                    max_concurrent_tasks=tmpl.max_concurrent_tasks,
                    permanent=False,
                )
                self._factory._create_one(spec)
                self._factory._created.append(child_id)
            except Exception:
                pass

        return child_id

    def evaluate_and_destroy(
        self,
        child_id: str,
        child_idle_seconds: float = 0.0,
        child_tasks_remaining: int = 0,
    ) -> bool:
        """Evaluate whether to destroy a child agent, and destroy if appropriate."""
        if child_id not in self._children:
            return False
        if not self.can_spawn:
            return False

        record = self._children[child_id]

        if child_tasks_remaining == 0:
            return self._destroy(child_id, DestroyReason.TASK_COMPLETE)

        if child_idle_seconds > self._idle_timeout:
            return self._destroy(child_id, DestroyReason.IDLE)

        total_children = self.child_count
        if total_children > self._max_children * 0.8 and child_idle_seconds > self._idle_timeout / 2:
            return self._destroy(child_id, DestroyReason.RESOURCE_PRESSURE)

        return False

    def _destroy(self, child_id: str, reason: DestroyReason) -> bool:
        if child_id not in self._children:
            return False

        self._destroy_count += 1

        if self._factory is not None:
            try:
                self._factory.orchestrator.unregister_agent(child_id)
                self._factory.comm_bus.unregister_agent(child_id)
                if self._factory.health:
                    self._factory.health.unregister(child_id)
                if self._factory.pool:
                    self._factory.pool.remove_agent(child_id)
                if child_id in self._factory._created:
                    self._factory._created.remove(child_id)
            except Exception:
                pass

        del self._children[child_id]
        return True

    def consolidate(self) -> int:
        """Destroy all idle children. Returns count destroyed."""
        destroyed = 0
        for cid in list(self._children.keys()):
            if self._destroy(cid, DestroyReason.CONSOLIDATION):
                destroyed += 1
        return destroyed

    def record_child_progress(self, child_id: str, tasks_completed: int = 0, tasks_assigned: int = 0) -> None:
        if child_id in self._children:
            r = self._children[child_id]
            r.tasks_completed += tasks_completed
            r.tasks_assigned += tasks_assigned

    def _find_needed_role(self, task_queue: list[Any], current_roles: set[str]) -> str | None:
        task_types = self._extract_task_types(task_queue)
        type_counts: dict[str, int] = {}
        for tt in task_types:
            type_counts[tt] = type_counts.get(tt, 0) + 1
        for tt, _ in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            for rname, tmpl in self._role_templates.items():
                if tt in tmpl.typical_task_types and rname not in current_roles:
                    return rname
        return None

    def _find_busiest_role(self, task_queue: list[Any]) -> str:
        type_counts: dict[str, int] = {}
        for tt in self._extract_task_types(task_queue):
            type_counts[tt] = type_counts.get(tt, 0) + 1
        if not type_counts:
            return "fixer"
        busiest_type = max(type_counts, key=type_counts.get)
        for rname, tmpl in self._role_templates.items():
            if busiest_type in tmpl.typical_task_types:
                return rname
        return "fixer"

    def _extract_task_types(self, task_queue: list[Any]) -> list[str]:
        types = []
        for t in task_queue:
            if hasattr(t, "type"):
                types.append(str(t.type))
            elif isinstance(t, dict):
                types.append(str(t.get("type", "code")))
            else:
                types.append("code")
        return types

    def stats(self) -> dict[str, Any]:
        return {
            "child_count": self.child_count,
            "max_children": self._max_children,
            "total_spawns": self._spawn_count,
            "total_destroys": self._destroy_count,
            "can_spawn": self.can_spawn,
            "children_roles": {cid: r.role for cid, r in self._children.items()},
        }


__all__ = [
    "AutonomousSpawner", "SpawnReason", "DestroyReason",
    "SpawnRecord", "RoleTemplate", "BUILTIN_ROLE_TEMPLATES",
]
