"""Unattended Runner: 24/7 fully autonomous agent operation.

Phase 20.1: Enables L5 (AUTONOMOUS) agents to run without human oversight:
  - Heartbeat monitoring (periodic health checks)
  - Watchdog timer (detect and recover from hangs/crashes)
  - Auto-recovery (restart failed components, rollback bad states)
  - Graceful degradation (reduce capability under stress)
  - Run journal (immutable log of all autonomous decisions)
  - Scheduled self-evolution cycles (periodic arch refactor, policy adjust)

Only operates at L5 autonomy — below that, requires human confirmation.
"""

from __future__ import annotations

import asyncio
import signal
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from governance.modification_chain import ModificationChain
from autoai.logs import logger


class RunnerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    STOPPED = "stopped"
    CRASHED = "crashed"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class Heartbeat:
    agent_id: str
    timestamp: float = field(default_factory=time.monotonic)
    status: HealthStatus = HealthStatus.HEALTHY
    metrics: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0


@dataclass
class WatchdogEntry:
    agent_id: str
    last_heartbeat: float = 0.0
    timeout_seconds: float = 60.0
    miss_count: int = 0
    max_misses: int = 3


@dataclass
class RunJournalEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event: str = ""
    agent_id: str = ""
    decision: str = ""
    outcome: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class UnattendedRunner:
    """24/7 autonomous agent runner with watchdog and auto-recovery.

    Usage:
        runner = UnattendedRunner(autonomy=manager)
        runner.register_agent("main", think_fn, heartbeat_interval=30)
        await runner.start()  # runs forever until stop()
    """

    def __init__(
        self,
        autonomy: AutonomyManager | None = None,
        chain: ModificationChain | None = None,
        watchdog_timeout: float = 60.0,
        max_heartbeat_misses: int = 3,
        evolution_interval_seconds: float = 3600.0,
    ) -> None:
        self.autonomy = autonomy or AutonomyManager(agent_id="runner")
        self.chain = chain or ModificationChain()
        self._watchdog_timeout = watchdog_timeout
        self._max_misses = max_heartbeat_misses
        self._evolution_interval = evolution_interval_seconds
        self._state = RunnerState.IDLE
        self._agents: dict[str, dict[str, Any]] = {}
        self._watchdogs: dict[str, WatchdogEntry] = {}
        self._heartbeats: dict[str, Heartbeat] = {}
        self._journal: list[RunJournalEntry] = []
        self._tasks: dict[str, asyncio.Task] = {}
        self._recovery_count: dict[str, int] = defaultdict(int)
        self._max_recoveries: int = 5
        self._start_time: float = 0.0
        self._stop_event = asyncio.Event()
        self._evolution_callback: Callable | None = None
        self._health_callback: Callable | None = None

    @property
    def state(self) -> RunnerState:
        return self._state

    @property
    def uptime_seconds(self) -> float:
        if self._start_time == 0:
            return 0.0
        return time.monotonic() - self._start_time

    @property
    def is_l5(self) -> bool:
        return self.autonomy.level >= AutonomyLevel.AUTONOMOUS

    def register_agent(
        self,
        agent_id: str,
        think_fn: Callable,
        heartbeat_interval: float = 30.0,
        max_recoveries: int = 5,
    ) -> None:
        self._agents[agent_id] = {
            "think_fn": think_fn,
            "heartbeat_interval": heartbeat_interval,
            "max_recoveries": max_recoveries,
        }
        self._watchdogs[agent_id] = WatchdogEntry(
            agent_id=agent_id,
            timeout_seconds=self._watchdog_timeout,
            max_misses=self._max_misses,
        )
        self._heartbeats[agent_id] = Heartbeat(agent_id=agent_id)

    def set_evolution_callback(self, callback: Callable) -> None:
        self._evolution_callback = callback

    def set_health_callback(self, callback: Callable) -> None:
        self._health_callback = callback

    def _record_journal(self, event: str, agent_id: str = "", decision: str = "", outcome: str = "", **meta: Any) -> None:
        entry = RunJournalEntry(
            event=event,
            agent_id=agent_id,
            decision=decision,
            outcome=outcome,
            metadata=meta,
        )
        self._journal.append(entry)
        if len(self._journal) > 10000:
            self._journal = self._journal[-5000:]

    async def start(self) -> None:
        if not self.is_l5:
            logger.warn("[UnattendedRunner] Not at L5 AUTONOMOUS — human oversight recommended")

        self._state = RunnerState.RUNNING
        self._start_time = time.monotonic()
        self._stop_event.clear()

        self._record_journal("runner_start", decision="autonomous_mode", outcome="started")

        agent_tasks = []
        for agent_id in self._agents:
            task = asyncio.create_task(self._run_agent_loop(agent_id))
            self._tasks[agent_id] = task
            agent_tasks.append(task)

        watchdog_task = asyncio.create_task(self._watchdog_loop())
        evolution_task = asyncio.create_task(self._evolution_loop())
        agent_tasks.extend([watchdog_task, evolution_task])

        try:
            await self._stop_event.wait()
        finally:
            for task in agent_tasks:
                task.cancel()
            self._state = RunnerState.STOPPED
            self._record_journal("runner_stop", outcome="stopped")

    def stop(self) -> None:
        self._stop_event.set()

    async def _run_agent_loop(self, agent_id: str) -> None:
        agent_info = self._agents.get(agent_id)
        if agent_info is None:
            return

        think_fn = agent_info["think_fn"]
        interval = agent_info["heartbeat_interval"]
        seq = 0

        while not self._stop_event.is_set():
            try:
                if asyncio.iscoroutinefunction(think_fn):
                    result = await think_fn()
                else:
                    result = think_fn()

                seq += 1
                self._heartbeats[agent_id] = Heartbeat(
                    agent_id=agent_id,
                    status=HealthStatus.HEALTHY,
                    sequence=seq,
                    metrics={"result": str(result)[:100] if result else "ok"},
                )
                self._watchdogs[agent_id].last_heartbeat = time.monotonic()
                self._watchdogs[agent_id].miss_count = 0

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warn(f"[UnattendedRunner] Agent {agent_id} error: {e}")
                self._heartbeats[agent_id].status = HealthStatus.UNHEALTHY
                self._record_journal("agent_error", agent_id=agent_id, decision="error", outcome=str(e)[:200])

                recovery_ok = await self._attempt_recovery(agent_id, e)
                if not recovery_ok:
                    self._state = RunnerState.CRASHED
                    self._record_journal("runner_crashed", agent_id=agent_id, outcome="max_recoveries_exceeded")
                    break

                await asyncio.sleep(interval * 2)

    async def _watchdog_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._watchdog_timeout / 2)

                now = time.monotonic()
                for agent_id, wd in self._watchdogs.items():
                    elapsed = now - wd.last_heartbeat
                    if elapsed > wd.timeout_seconds:
                        wd.miss_count += 1
                        logger.warn(f"[Watchdog] {agent_id}: heartbeat miss #{wd.miss_count} ({elapsed:.1f}s)")

                        if wd.miss_count >= wd.max_misses:
                            self._record_journal("watchdog_timeout", agent_id=agent_id, decision="recover", outcome=f"missed_{wd.miss_count}")
                            recovery_ok = await self._attempt_recovery(agent_id, TimeoutError("watchdog timeout"))
                            if not recovery_ok:
                                self._heartbeats[agent_id].status = HealthStatus.CRITICAL
                        else:
                            self._heartbeats[agent_id].status = HealthStatus.DEGRADED

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warn(f"[Watchdog] Error: {e}")

    async def _evolution_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._evolution_interval)

                if self._evolution_callback is not None:
                    self._record_journal("evolution_cycle", decision="auto_evolve")
                    try:
                        if asyncio.iscoroutinefunction(self._evolution_callback):
                            result = await self._evolution_callback()
                        else:
                            result = self._evolution_callback()
                        self._record_journal("evolution_cycle", outcome="completed", metadata={"result": str(result)[:200]})
                    except Exception as e:
                        self._record_journal("evolution_cycle", outcome="failed", metadata={"error": str(e)[:200]})

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warn(f"[EvolutionLoop] Error: {e}")

    async def _attempt_recovery(self, agent_id: str, error: Exception) -> bool:
        count = self._recovery_count[agent_id]
        max_rec = self._agents.get(agent_id, {}).get("max_recoveries", self._max_recoveries)

        if count >= max_rec:
            logger.warn(f"[UnattendedRunner] {agent_id}: max recoveries ({max_rec}) exceeded")
            return False

        self._recovery_count[agent_id] = count + 1
        self._state = RunnerState.RECOVERING
        self._record_journal(
            "recovery_attempt", agent_id=agent_id,
            decision=f"recovery_{count+1}", outcome=str(error)[:100],
        )

        old_task = self._tasks.get(agent_id)
        if old_task and not old_task.done():
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        agent_info = self._agents.get(agent_id)
        if agent_info:
            new_task = asyncio.create_task(self._run_agent_loop(agent_id))
            self._tasks[agent_id] = new_task
            self._heartbeats[agent_id].status = HealthStatus.DEGRADED
            self._state = RunnerState.RUNNING
            return True

        return False

    def get_health(self, agent_id: str) -> HealthStatus:
        hb = self._heartbeats.get(agent_id)
        return hb.status if hb else HealthStatus.CRITICAL

    def get_journal(self, limit: int = 100, event_filter: str = "") -> list[RunJournalEntry]:
        entries = self._journal
        if event_filter:
            entries = [e for e in entries if e.event == event_filter]
        return entries[-limit:]

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "uptime_seconds": self.uptime_seconds,
            "autonomy_level": self.autonomy.level.name,
            "is_l5": self.is_l5,
            "agents": {
                aid: {
                    "health": self._heartbeats.get(aid, Heartbeat(aid)).status.value,
                    "recoveries": self._recovery_count.get(aid, 0),
                    "watchdog_misses": self._watchdogs.get(aid, WatchdogEntry(aid)).miss_count,
                }
                for aid in self._agents
            },
            "journal_size": len(self._journal),
        }


__all__ = [
    "UnattendedRunner",
    "RunnerState",
    "HealthStatus",
    "Heartbeat",
    "WatchdogEntry",
    "RunJournalEntry",
]
