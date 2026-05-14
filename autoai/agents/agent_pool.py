"""基于工作负载需求弹性伸缩的代理池.

Manages a pool of agent profiles and automatically scales the number
of available agents up or down based on:
- Pending task count in the workflow orchestrator
- Current agent utilization (load factor)
- Configurable min/max pool size per role

Scaling up: creates new agent profiles (real agent instantiation is
delegated to a factory callback).
Scaling down: removes idle agents (longest idle first).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .workflow_orchestrator import AgentProfile, WorkflowOrchestrator
from .agent_comm import AgentCommunicationBus
from .health_monitor import AgentHealthMonitor

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """配置 for 代理 pool scaling."""

    min_agents: dict[str, int] = field(default_factory=lambda: {"coder": 1, "reviewer": 0})
    max_agents: dict[str, int] = field(default_factory=lambda: {"coder": 5, "reviewer": 3})
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.2
    scale_up_cooldown: float = 30.0
    scale_down_cooldown: float = 120.0
    idle_timeout_seconds: float = 300.0
    check_interval_seconds: float = 15.0


@dataclass
class PoolEntry:
    """An 代理 条目 in the pool."""

    profile: AgentProfile
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    is_permanent: bool = False

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_active_at

    @property
    def utilization(self) -> float:
        if self.profile.max_concurrent_tasks == 0:
            return 0.0
        return self.profile.current_tasks / self.profile.max_concurrent_tasks


class AgentPool:
    """Elastic 代理 pool with 自动扩缩容.

    Usage:
        pool = AgentPool(
            orchestrator=orch,
            comm_bus=bus,
            health_monitor=monitor,
            agent_factory=my_factory,
        )
        pool.start()
    """

    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        comm_bus: AgentCommunicationBus,
        health_monitor: AgentHealthMonitor | None = None,
        agent_factory: Callable[[str, str], str] | None = None,
        config: PoolConfig | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.comm_bus = comm_bus
        self.health = health_monitor
        self._factory = agent_factory
        self.config = config or PoolConfig()
        self._pool: dict[str, PoolEntry] = {}
        self._role_counts: dict[str, int] = {}
        self._last_scale_up: float = 0.0
        self._last_scale_down: float = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def add_agent(
        self,
        agent_id: str,
        roles: set[str],
        capabilities: set[str] | None = None,
        permanent: bool = False,
    ) -> None:
        """Manually 添加 an 代理 to the pool."""
        profile = AgentProfile(
            agent_id=agent_id,
            roles=roles,
            capabilities=capabilities or set(),
        )
        entry = PoolEntry(profile=profile, is_permanent=permanent)
        with self._lock:
            self._pool[agent_id] = entry
            for role in roles:
                self._role_counts[role] = self._role_counts.get(role, 0) + 1
        self.orchestrator.register_agent(profile)
        self.comm_bus.register_agent(agent_id)
        if self.health:
            self.health.register(agent_id, role=next(iter(roles), ""))
        logger.info("[池] Agent added: %s (roles=%s, 永久=%s)", agent_id, roles, permanent)

    def remove_agent(self, agent_id: str) -> bool:
        """移除 an 代理 from the pool."""
        with self._lock:
            entry = self._pool.pop(agent_id, None)
            if entry is None:
                return False
            if entry.is_permanent:
                self._pool[agent_id] = entry
                return False
            for role in entry.profile.roles:
                self._role_counts[role] = max(0, self._role_counts.get(role, 0) - 1)
        self.orchestrator.unregister_agent(agent_id)
        self.comm_bus.unregister_agent(agent_id)
        if self.health:
            self.health.unregister(agent_id)
        logger.info("[池] Agent removed: %s", agent_id)
        return True

    def get_pool_status(self) -> dict[str, Any]:
        with self._lock:
            entries = {
                aid: {
                    "roles": list(e.profile.roles),
                    "tasks": f"{e.profile.current_tasks}/{e.profile.max_concurrent_tasks}",
                    "utilization": f"{e.utilization:.0%}",
                    "idle": f"{e.idle_seconds:.0f}s",
                    "permanent": e.is_permanent,
                }
                for aid, e in self._pool.items()
            }
            role_info = dict(self._role_counts)
        return {
            "total_agents": len(entries),
            "by_role": role_info,
            "agents": entries,
        }

    def _scale_check(self) -> None:
        """检查 if scaling is needed and perform it."""
        now = time.time()
        with self._lock:
            role_utilization: dict[str, list[float]] = {}
            for entry in self._pool.values():
                for role in entry.profile.roles:
                    role_utilization.setdefault(role, []).append(entry.utilization)

            role_idle: dict[str, list[tuple[str, float]]] = {}
            for aid, entry in self._pool.items():
                if entry.is_permanent:
                    continue
                for role in entry.profile.roles:
                    role_idle.setdefault(role, []).append((aid, entry.idle_seconds))

        for role, min_count in self.config.min_agents.items():
            current = self._role_counts.get(role, 0)
            if current < min_count:
                deficit = min_count - current
                for _ in range(deficit):
                    self._spawn_agent(role)

        for role, utils in role_utilization.items():
            if not utils:
                continue
            avg_util = sum(utils) / len(utils)
            current_count = len(utils)
            max_count = self.config.max_agents.get(role, current_count)

            if avg_util > self.config.scale_up_threshold and current_count < max_count:
                if now - self._last_scale_up >= self.config.scale_up_cooldown:
                    self._spawn_agent(role)
                    self._last_scale_up = now

            elif avg_util < self.config.scale_down_threshold and current_count > self.config.min_agents.get(role, 0):
                if now - self._last_scale_down >= self.config.scale_down_cooldown:
                    idle_agents = role_idle.get(role, [])
                    idle_agents.sort(key=lambda x: -x[1])
                    for aid, idle in idle_agents:
                        if idle > self.config.idle_timeout_seconds:
                            if self.remove_agent(aid):
                                self._last_scale_down = now
                                break

    def _spawn_agent(self, role: str) -> str:
        """创建 a new 代理 for the given 角色."""
        agent_id = f"{role}_{uuid_hex(8)}"
        capabilities = self._default_capabilities(role)

        if self._factory is not None:
            try:
                real_id = self._factory(agent_id, role)
                if real_id:
                    agent_id = real_id
            except Exception as e:
                logger.error("[池] Factory err或用于%s: %s", agent_id, e)

        self.add_agent(agent_id, roles={role}, capabilities=capabilities)
        return agent_id

    @staticmethod
    def _default_capabilities(role: str) -> set[str]:
        role_caps = {
            "coder": {"plan", "execute", "debug", "write_code"},
            "reviewer": {"review", "approve", "test"},
            "architect": {"design", "refactor", "plan"},
            "tester": {"test", "debug", "verify"},
            "deployer": {"deploy", "monitor", "rollback"},
        }
        return role_caps.get(role, {"execute"})

    def start(self) -> None:
        if self._running:
            回报
        self._running = True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="agent-pool-monitor",
            daemon=True,
        )
        self._thread.start()
        logger.info("[池] Agent 池 monit或started")

    def stop(self) -> None:
        self._running = False
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10.0)

    def _monitor_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._scale_check()
            except Exception as e:
                logger.error("[池] 缩放 check error: %s", e)
            self._stop.wait(timeout=self.config.check_interval_seconds)


def uuid_hex(length: int = 8) -> str:
    import uuid
    return uuid.uuid4().hex[:length]


__all__ = [
    "PoolConfig",
    "PoolEntry",
    "AgentPool",
]
