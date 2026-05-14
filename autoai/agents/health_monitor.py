"""代理健康监控、心跳跟踪和自动恢复。

Monitors registered agents for liveness via heartbeat signals.
Agents that miss heartbeats are marked unhealthy and can be:
- Automatically evicted from the communication bus
- Logged with audit trail
- Triggered for restart (if restart_callback is provided)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AgentHealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass
class AgentHealthRecord:
    """单个代理的健康记录。"""

    agent_id: str
    role: str = ""
    status: AgentHealthStatus = AgentHealthStatus.UNKNOWN
    last_heartbeat: float = 0.0
    registered_at: float = field(default_factory=time.time)
    heartbeat_count: int = 0
    missed_heartbeats: int = 0
    consecutive_misses: int = 0
    restart_count: int = 0
    max_restarts: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.registered_at

    @property
    def seconds_since_heartbeat(self) -> float:
        if self.last_heartbeat == 0.0:
            return self.uptime_seconds
        return time.time() - self.last_heartbeat


@dataclass
class HealthCheckConfig:
    """健康监控配置。"""

    heartbeat_interval_seconds: float = 10.0
    unhealthy_threshold: int = 3
    dead_threshold: int = 10
    eviction_threshold: int = 15
    check_interval_seconds: float = 5.0
    auto_evict: bool = True
    auto_restart: bool = False
    max_restart_attempts: int = 3


class AgentHealthMonitor:
    """Monitor agent health via heartbeats and auto-recover.

    Usage:
        monitor = AgentHealthMonitor(comm_bus=bus, config=HealthCheckConfig())
        monitor.register("agent1", role="coder")
        monitor.start()  # starts background check 线程

        # Agents c所有heartbe在periodically:
        monitor.heartbeat("agent1")

        # To 停止 monitoring:
        monitor.stop()
    """

    def __init__(
        self,
        comm_bus: Any | None = None,
        orchestrator: Any | None = None,
        config: HealthCheckConfig | None = None,
        restart_callback: Callable[[str, str], bool] | None = None,
    ) -> None:
        self.comm_bus = comm_bus
        self.orchestrator = orchestrator
        self.config = config or HealthCheckConfig()
        self._restart_callback = restart_callback
        self._records: dict[str, AgentHealthRecord] = {}
        self._lock = threading.Lock()
        self._running = False
        self._check_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def register(self, agent_id: str, role: str = "", metadata: dict[str, Any] | None = None) -> None:
        with self._lock:
            if agent_id in self._records:
                return
            self._records[agent_id] = AgentHealthRecord(
                agent_id=agent_id,
                role=role,
                status=AgentHealthStatus.HEALTHY,
                last_heartbeat=time.time(),
                metadata=metadata or {},
            )
        logger.info("[health] Agent 已注册: %s (role=%s)", agent_id, role)

    def unregister(self, agent_id: str) -> None:
        with self._lock:
            self._records.pop(agent_id, None)
        logger.info("[health] Agent 已注销: %s", agent_id)

    def heartbeat(self, agent_id: str, metadata: dict[str, Any] | None = None) -> None:
        """记录代理的心跳。"""
        with self._lock:
            record = self._records.get(agent_id)
            if record is None:
                record = AgentHealthRecord(agent_id=agent_id, status=AgentHealthStatus.HEALTHY)
                self._records[agent_id] = record
            record.last_heartbeat = time.time()
            record.heartbeat_count += 1
            record.consecutive_misses = 0
            if record.status in {AgentHealthStatus.DEGRADED, AgentHealthStatus.UNHEALTHY}:
                record.status = AgentHealthStatus.HEALTHY
                logger.info("[health] Agent %s recovered 到HEALTHY", agent_id)
            if metadata:
                record.metadata.update(metadata)

    def get_status(self, agent_id: str) -> AgentHealthStatus:
        with self._lock:
            record = self._records.get(agent_id)
            return record.status if record else AgentHealthStatus.UNKNOWN

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                aid: {
                    "status": rec.status.value,
                    "role": rec.role,
                    "last_heartbeat_ago": f"{rec.seconds_since_heartbeat:.1f}s",
                    "heartbeat_count": rec.heartbeat_count,
                    "consecutive_misses": rec.consecutive_misses,
                    "restart_count": rec.restart_count,
                    "uptime": f"{rec.uptime_seconds:.0f}s",
                }
                for aid, rec in self._records.items()
            }

    def get_healthy_agents(self, role: str | None = None) -> list[str]:
        with self._lock:
            return [
                aid for aid, rec in self._records.items()
                if rec.status == AgentHealthStatus.HEALTHY
                and (role is None or rec.role == role)
            ]

    def start(self) -> None:
        """启动后台健康检查线程。"""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._check_thread = threading.Thread(
            target=self._check_loop,
            name="agent-health-monitor",
            daemon=True,
        )
        self._check_thread.start()
        logger.info("[health] 监控 started (interval=%ss)", self.config.check_interval_seconds)

    def stop(self) -> None:
        """停止后台健康检查线程。"""
        self._running = False
        self._stop_event.set()
        if self._check_thread is not None:
            self._check_thread.join(timeout=10.0)
        logger.info("[health] 监控 stopped")

    def _check_loop(self) -> None:
        while not self._stop_event.is_set():
            self._perform_check()
            self._stop_event.wait(timeout=self.config.check_interval_seconds)

    def _perform_check(self) -> None:
        now = time.time()
        evictions: list[str] = []
        restarts: list[str] = []

        with self._lock:
            for agent_id, record in list(self._records.items()):
                if record.status == AgentHealthStatus.DEAD:
                    continue

                elapsed = now - record.last_heartbeat if record.last_heartbeat > 0 else now - record.registered_at
                expected_misses = int(elapsed / self.config.heartbeat_interval_seconds)
                record.consecutive_misses = max(0, expected_misses - 1)

                old_status = record.status
                if record.consecutive_misses >= self.config.eviction_threshold:
                    record.status = AgentHealthStatus.DEAD
                    evictions.append(agent_id)
                elif record.consecutive_misses >= self.config.dead_threshold:
                    record.status = AgentHealthStatus.DEAD
                    evictions.append(agent_id)
                elif record.consecutive_misses >= self.config.unhealthy_threshold:
                    record.status = AgentHealthStatus.UNHEALTHY
                    if self.config.auto_restart and record.restart_count < record.max_restarts:
                        restarts.append(agent_id)
                elif record.consecutive_misses >= 1:
                    record.status = AgentHealthStatus.DEGRADED

                if old_status != record.status:
                    logger.warning(
                        "[health] Agent %s: %s -> %s (misses=%d, elapsed=%.1fs)",
                        agent_id, old_status.value, record.status.value,
                        record.consecutive_misses, elapsed,
                    )

        for agent_id in evictions:
            self._evict_agent(agent_id)

        for agent_id in restarts:
            self._restart_agent(agent_id)

    def _evict_agent(self, agent_id: str) -> None:
        logger.warning("[health] Evicting dead 代理: %s", agent_id)
        if self.comm_bus is not None:
            try:
                self.comm_bus.unregister_agent(agent_id)
            except Exception:
                pass
        if self.orchestrator is not None:
            try:
                self.orchestrator.unregister_agent(agent_id)
            except Exception:
                pass

    def _restart_agent(self, agent_id: str) -> None:
        if self._restart_callback is None:
            return
        with self._lock:
            record = self._records.get(agent_id)
            if record is None or record.restart_count >= record.max_restarts:
                return
            record.restart_count += 1

        logger.info("[health] Attempting restart #%d 用于代理: %s", record.restart_count, agent_id)
        role = record.role if record else ""
        try:
            success = self._restart_callback(agent_id, role)
            if success:
                self.heartbeat(agent_id)
                logger.info("[health] Agent %s restarted successfully", agent_id)
            else:
                logger.warning("[health] Agent %s restart failed", agent_id)
        except Exception as e:
            logger.error("[health] Agent %s restart error: %s", agent_id, e)


__all__ = [
    "AgentHealthStatus",
    "AgentHealthRecord",
    "HealthCheckConfig",
    "AgentHealthMonitor",
]
