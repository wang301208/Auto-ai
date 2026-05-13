"""Distributed execution base types and abstract interface."""

from __future__ import annotations

import abc
import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Coroutine


class WorkerStatus(enum.Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class WorkerInfo:
    worker_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    address: str = "local"
    status: WorkerStatus = WorkerStatus.IDLE
    capabilities: set[str] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)
    current_task_id: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    cpu_count: int = 1
    memory_gb: float = 4.0
    last_heartbeat: str = ""

    @property
    def is_available(self) -> bool:
        return self.status == WorkerStatus.IDLE

    @property
    def reliability(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total


@dataclass
class DispatchFuture:
    future_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    task_id: str = ""
    worker_id: str = ""
    _result: Any = None
    _done: bool = False
    _error: str | None = None

    def set_result(self, result: Any) -> None:
        self._result = result
        self._done = True

    def set_error(self, error: str) -> None:
        self._error = error
        self._done = True

    @property
    def done(self) -> bool:
        return self._done

    @property
    def result(self) -> Any:
        return self._result

    @property
    def error(self) -> str | None:
        return self._error


@dataclass
class AgentSpec:
    agent_type: str = "async_agent"
    name: str = ""
    role: str = ""
    config: dict[str, Any] = field(default_factory=dict)


class DistributedBackend(abc.ABC):
    """Abstract distributed execution backend."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerInfo] = {}
        self._running = False

    @abc.abstractmethod
    async def start(self) -> None:
        ...

    @abc.abstractmethod
    async def stop(self) -> None:
        ...

    @abc.abstractmethod
    async def dispatch(
        self,
        task: Any,
        agent_spec: AgentSpec | None = None,
        preferred_worker: str | None = None,
    ) -> DispatchFuture:
        ...

    @abc.abstractmethod
    async def get_result(self, future: DispatchFuture, timeout: float = 300.0) -> Any:
        ...

    def register_worker(self, info: WorkerInfo) -> None:
        self._workers[info.worker_id] = info

    def unregister_worker(self, worker_id: str) -> None:
        self._workers.pop(worker_id, None)

    def get_available_workers(self, required_roles: set[str] | None = None) -> list[WorkerInfo]:
        available = [w for w in self._workers.values() if w.is_available]
        if required_roles:
            available = [w for w in available if required_roles.intersection(w.roles)]
        return available

    def select_worker(self, required_roles: set[str] | None = None) -> WorkerInfo | None:
        workers = self.get_available_workers(required_roles)
        if not workers:
            return None
        workers.sort(key=lambda w: -w.reliability)
        return workers[0]

    @property
    def workers(self) -> dict[str, WorkerInfo]:
        return self._workers

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def total_workers(self) -> int:
        return len(self._workers)

    @property
    def available_count(self) -> int:
        return len(self.get_available_workers())

    def summary(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "total_workers": self.total_workers,
            "available": self.available_count,
            "workers": {
                w.worker_id: {
                    "status": w.status.value,
                    "tasks_completed": w.tasks_completed,
                    "reliability": f"{w.reliability:.2f}",
                }
                for w in self._workers.values()
            },
        }


__all__ = [
    "WorkerStatus",
    "WorkerInfo",
    "DispatchFuture",
    "AgentSpec",
    "DistributedBackend",
]
