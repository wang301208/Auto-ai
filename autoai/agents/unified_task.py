"""Unified task model that bridges V2 Task and WorkflowTask into a single dispatch system.

Design:
  - UnifiedTask: single task type with 4 execution categories
  - TaskCategory: IMMEDIATE / STANDARD / LONG_RUN / DAEMON
  - TaskScheduler: unified dispatcher that routes tasks by category
  - Long-running tasks split into phases with checkpoints
  - Short tasks dispatched immediately with timeout circuit breaker
  - Seamless conversion from V2 Task and WorkflowTask
"""

from __future__ import annotations

import asyncio
import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class TaskCategory(enum.Enum):
    IMMEDIATE = "immediate"
    STANDARD = "standard"
    LONG_RUN = "long_run"
    DAEMON = "daemon"


class UnifiedTaskStatus(enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class TaskPhase:
    phase_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    status: UnifiedTaskStatus = UnifiedTaskStatus.PENDING
    checkpoint_data: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class UnifiedTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    objective: str = ""
    category: TaskCategory = TaskCategory.STANDARD
    status: UnifiedTaskStatus = UnifiedTaskStatus.PENDING
    priority: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    assigned_agent: str | None = None
    required_roles: set[str] = field(default_factory=set)
    required_capabilities: set[str] = field(default_factory=set)
    dependencies: set[str] = field(default_factory=set)

    timeout_seconds: float = 300.0
    max_retries: int = 2
    retry_count: int = 0

    phases: list[TaskPhase] = field(default_factory=list)
    current_phase_index: int = 0

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None

    source_type: str = "unified"
    source_id: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def mark_dispatched(self, agent_id: str) -> None:
        self.status = UnifiedTaskStatus.DISPATCHED
        self.assigned_agent = agent_id

    def mark_running(self) -> None:
        self.status = UnifiedTaskStatus.RUNNING
        if self.started_at is None:
            self.started_at = self._now()

    def mark_succeeded(self, result: dict[str, Any] | None = None) -> None:
        self.status = UnifiedTaskStatus.SUCCEEDED
        self.result = result or {}
        self.finished_at = self._now()

    def mark_failed(self, error: str) -> None:
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.status = UnifiedTaskStatus.PENDING
            self.error = error
        else:
            self.status = UnifiedTaskStatus.FAILED
            self.error = error
            self.finished_at = self._now()

    def mark_timed_out(self) -> None:
        self.status = UnifiedTaskStatus.TIMED_OUT
        self.error = f"Timeout after {self.timeout_seconds}s"
        self.finished_at = self._now()

    def mark_cancelled(self) -> None:
        self.status = UnifiedTaskStatus.CANCELLED
        self.finished_at = self._now()

    def pause(self) -> None:
        if self.status == UnifiedTaskStatus.RUNNING:
            self.status = UnifiedTaskStatus.PAUSED

    def resume(self) -> None:
        if self.status == UnifiedTaskStatus.PAUSED:
            self.status = UnifiedTaskStatus.RUNNING

    def add_phase(self, name: str, description: str = "") -> TaskPhase:
        phase = TaskPhase(name=name, description=description)
        self.phases.append(phase)
        return phase

    @property
    def current_phase(self) -> TaskPhase | None:
        if 0 <= self.current_phase_index < len(self.phases):
            return self.phases[self.current_phase_index]
        return None

    def advance_phase(self, checkpoint_data: dict[str, Any] | None = None) -> TaskPhase | None:
        if self.current_phase:
            self.current_phase.status = UnifiedTaskStatus.SUCCEEDED
            self.current_phase.finished_at = self._now()
            if checkpoint_data:
                self.current_phase.checkpoint_data = checkpoint_data
        self.current_phase_index += 1
        if self.current_phase:
            self.current_phase.status = UnifiedTaskStatus.RUNNING
            self.current_phase.started_at = self._now()
        return self.current_phase

    @property
    def effective_timeout(self) -> float:
        if self.category == TaskCategory.IMMEDIATE:
            return min(self.timeout_seconds, 30.0)
        elif self.category == TaskCategory.DAEMON:
            return 0.0
        return self.timeout_seconds

    @property
    def is_long_running(self) -> bool:
        return self.category in (TaskCategory.LONG_RUN, TaskCategory.DAEMON)

    @property
    def is_done(self) -> bool:
        return self.status in (
            UnifiedTaskStatus.SUCCEEDED,
            UnifiedTaskStatus.FAILED,
            UnifiedTaskStatus.CANCELLED,
            UnifiedTaskStatus.TIMED_OUT,
        )

    @classmethod
    def from_v2_task(cls, task: Any, **overrides: Any) -> UnifiedTask:
        category = cls._infer_category_from_v2(task)
        return cls(
            name=task.objective[:80],
            objective=task.objective,
            category=category,
            priority=task.priority,
            source_type="v2_task",
            source_id=str(id(task)),
            metadata={
                "task_type": str(task.type) if hasattr(task, "type") else None,
                "ready_criteria": getattr(task, "ready_criteria", []),
                "acceptance_criteria": getattr(task, "acceptance_criteria", []),
            },
            **overrides,
        )

    @classmethod
    def from_workflow_task(cls, wf_task: Any, **overrides: Any) -> UnifiedTask:
        category = cls._infer_category_from_workflow(wf_task)
        return cls(
            task_id=wf_task.task_id,
            name=wf_task.name,
            objective=wf_task.description or wf_task.name,
            category=category,
            priority=wf_task.priority,
            payload=wf_task.payload,
            required_roles=wf_task.required_roles,
            required_capabilities=wf_task.required_capabilities,
            dependencies=wf_task.dependencies,
            timeout_seconds=wf_task.timeout_seconds,
            max_retries=wf_task.max_retries,
            source_type="workflow_task",
            source_id=wf_task.task_id,
            **overrides,
        )

    @staticmethod
    def _infer_category_from_v2(task: Any) -> TaskCategory:
        task_type_str = str(getattr(task, "type", "")).lower()
        if task_type_str in ("code", "test"):
            return TaskCategory.LONG_RUN
        if task_type_str in ("research", "plan"):
            return TaskCategory.STANDARD
        if task_type_str in ("edit", "write"):
            return TaskCategory.STANDARD
        return TaskCategory.STANDARD

    @staticmethod
    def _infer_category_from_workflow(wf_task: Any) -> TaskCategory:
        timeout = getattr(wf_task, "timeout_seconds", 300)
        if timeout == 0 or timeout > 3600:
            return TaskCategory.DAEMON
        if timeout > 600:
            return TaskCategory.LONG_RUN
        if timeout <= 30:
            return TaskCategory.IMMEDIATE
        return TaskCategory.STANDARD


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: str = field(default="closed", init=False)

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc).timestamp()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            elapsed = datetime.now(timezone.utc).timestamp() - self._last_failure_time
            if elapsed >= self.recovery_timeout_seconds:
                self._state = "half_open"
                return False
            return True
        return False

    @property
    def state(self) -> str:
        return self._state


@dataclass
class SchedulerStats:
    total_dispatched: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    total_timed_out: int = 0
    by_category: dict[str, int] = field(default_factory=lambda: {
        TaskCategory.IMMEDIATE.value: 0,
        TaskCategory.STANDARD.value: 0,
        TaskCategory.LONG_RUN.value: 0,
        TaskCategory.DAEMON.value: 0,
    })


class TaskScheduler:
    """Unified task scheduler that dispatches by category.

    IMMEDIATE: direct dispatch, short timeout, circuit breaker
    STANDARD: queued dispatch, normal timeout, retry
    LONG_RUN: phase-based dispatch, checkpoint on each phase, pause/resume
    DAEMON: persistent dispatch, no timeout, auto-restart on failure
    """

    def __init__(
        self,
        executor: Callable[[UnifiedTask], Coroutine[Any, Any, dict[str, Any]]] | None = None,
        max_concurrent: int = 10,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._executor = executor or self._default_executor
        self._max_concurrent = max_concurrent
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._queue: list[UnifiedTask] = []
        self._running: dict[str, asyncio.Task[None]] = {}
        self._completed: dict[str, UnifiedTask] = {}
        self._daemons: dict[str, asyncio.Task[None]] = {}
        self._stats = SchedulerStats()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._checkpoints: dict[str, dict[str, Any]] = {}

    def submit(self, task: UnifiedTask) -> str:
        self._queue.append(task)
        self._queue.sort(key=lambda t: -t.priority)
        return task.task_id

    def submit_many(self, tasks: list[UnifiedTask]) -> list[str]:
        ids = []
        for t in tasks:
            self._queue.append(t)
            ids.append(t.task_id)
        self._queue.sort(key=lambda t: -t.priority)
        return ids

    async def dispatch_all(self) -> None:
        while self._queue:
            async with self._lock:
                batch = self._drain_queue()
            if not batch:
                break
            coros = [self._dispatch_one(task) for task in batch]
            await asyncio.gather(*coros, return_exceptions=True)

    async def dispatch_one(self, task: UnifiedTask) -> dict[str, Any]:
        return await self._dispatch_one(task)

    def _drain_queue(self) -> list[UnifiedTask]:
        batch = []
        remaining = []
        for task in self._queue:
            if task.category == TaskCategory.IMMEDIATE and not self._circuit_breaker.is_open:
                batch.append(task)
            elif task.category != TaskCategory.IMMEDIATE:
                batch.append(task)
            else:
                remaining.append(task)
        self._queue = remaining
        return batch

    async def _dispatch_one(self, task: UnifiedTask) -> dict[str, Any]:
        if task.category == TaskCategory.IMMEDIATE:
            return await self._dispatch_immediate(task)
        elif task.category == TaskCategory.STANDARD:
            return await self._dispatch_standard(task)
        elif task.category == TaskCategory.LONG_RUN:
            return await self._dispatch_long_run(task)
        elif task.category == TaskCategory.DAEMON:
            asyncio.create_task(self._dispatch_daemon(task))
            return {"task_id": task.task_id, "status": "daemon_started"}
        return {"task_id": task.task_id, "status": "unknown_category"}

    async def _dispatch_immediate(self, task: UnifiedTask) -> dict[str, Any]:
        if self._circuit_breaker.is_open:
            task.mark_failed("Circuit breaker is open")
            return self._finalize(task)
        self._stats.by_category[TaskCategory.IMMEDIATE.value] += 1
        async with self._semaphore:
            task.mark_running()
            try:
                result = await asyncio.wait_for(
                    self._executor(task),
                    timeout=task.effective_timeout,
                )
                task.mark_succeeded(result)
                self._circuit_breaker.record_success()
            except asyncio.TimeoutError:
                task.mark_timed_out()
                self._circuit_breaker.record_failure()
            except Exception as e:
                task.mark_failed(str(e))
                self._circuit_breaker.record_failure()
        return self._finalize(task)

    async def _dispatch_standard(self, task: UnifiedTask) -> dict[str, Any]:
        self._stats.by_category[TaskCategory.STANDARD.value] += 1
        async with self._semaphore:
            for attempt in range(task.max_retries + 1):
                task.mark_running()
                try:
                    result = await asyncio.wait_for(
                        self._executor(task),
                        timeout=task.effective_timeout,
                    )
                    task.mark_succeeded(result)
                    break
                except asyncio.TimeoutError:
                    task.mark_timed_out()
                    break
                except Exception as e:
                    task.mark_failed(str(e))
                    if task.status == UnifiedTaskStatus.FAILED:
                        break
        return self._finalize(task)

    async def _dispatch_long_run(self, task: UnifiedTask) -> dict[str, Any]:
        self._stats.by_category[TaskCategory.LONG_RUN.value] += 1
        async with self._semaphore:
            task.mark_running()
            if not task.phases:
                task.add_phase("main", task.objective)
            task.current_phase_index = 0
            first_phase = task.phases[0]
            first_phase.status = UnifiedTaskStatus.RUNNING
            first_phase.started_at = datetime.now(timezone.utc).isoformat()

            while task.current_phase is not None:
                phase = task.current_phase
                try:
                    phase_result = await asyncio.wait_for(
                        self._executor(task),
                        timeout=task.effective_timeout or 600,
                    )
                    checkpoint = phase_result.get("_checkpoint", {})
                    next_phase = task.advance_phase(checkpoint)
                    self._save_checkpoint(task, phase, phase_result)
                    if next_phase is None:
                        task.mark_succeeded(phase_result)
                except asyncio.TimeoutError:
                    phase.status = UnifiedTaskStatus.FAILED
                    phase.error = "Phase timed out"
                    phase.finished_at = datetime.now(timezone.utc).isoformat()
                    self._save_checkpoint(task, phase, {})
                    task.mark_failed(f"Phase '{phase.name}' timed out")
                    break
                except Exception as e:
                    phase.status = UnifiedTaskStatus.FAILED
                    phase.error = str(e)
                    phase.finished_at = datetime.now(timezone.utc).isoformat()
                    self._save_checkpoint(task, phase, {})
                    task.mark_failed(str(e))
                    break
        return self._finalize(task)

    async def _dispatch_daemon(self, task: UnifiedTask) -> None:
        self._stats.by_category[TaskCategory.DAEMON.value] += 1
        while True:
            task.mark_running()
            try:
                result = await self._executor(task)
                task.result.update(result)
            except asyncio.CancelledError:
                task.mark_cancelled()
                break
            except Exception as e:
                logger.warning("Daemon task %s error (auto-restart): %s", task.task_id, e)
                task.error = str(e)
                await asyncio.sleep(5.0)
                continue
            await asyncio.sleep(1.0)

    def _save_checkpoint(self, task: UnifiedTask, phase: TaskPhase, result: dict[str, Any]) -> None:
        self._checkpoints[f"{task.task_id}:{phase.phase_id}"] = {
            "task_id": task.task_id,
            "phase_id": phase.phase_id,
            "phase_name": phase.name,
            "status": phase.status.value,
            "checkpoint_data": phase.checkpoint_data,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_checkpoint(self, task_id: str, phase_id: str | None = None) -> dict[str, Any] | None:
        if phase_id:
            return self._checkpoints.get(f"{task_id}:{phase_id}")
        for key, val in self._checkpoints.items():
            if key.startswith(f"{task_id}:"):
                return val
        return None

    def _finalize(self, task: UnifiedTask) -> dict[str, Any]:
        self._stats.total_dispatched += 1
        if task.status == UnifiedTaskStatus.SUCCEEDED:
            self._stats.total_succeeded += 1
        elif task.status == UnifiedTaskStatus.FAILED:
            self._stats.total_failed += 1
        elif task.status == UnifiedTaskStatus.TIMED_OUT:
            self._stats.total_timed_out += 1
        self._completed[task.task_id] = task
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
        }

    async def _default_executor(self, task: UnifiedTask) -> dict[str, Any]:
        return {"status": "executed", "task": task.task_id}

    def get_task(self, task_id: str) -> UnifiedTask | None:
        for t in self._queue:
            if t.task_id == task_id:
                return t
        return self._completed.get(task_id)

    def cancel(self, task_id: str) -> bool:
        for t in self._queue:
            if t.task_id == task_id:
                t.mark_cancelled()
                self._queue.remove(t)
                self._completed[task_id] = t
                return True
        running_at = self._running.get(task_id)
        if running_at and not running_at.done():
            running_at.cancel()
            return True
        return False

    def pause_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task and task.status == UnifiedTaskStatus.RUNNING:
            task.pause()
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task and task.status == UnifiedTaskStatus.PAUSED:
            task.resume()
            return True
        return False

    @property
    def stats(self) -> SchedulerStats:
        return self._stats

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    @property
    def completed_tasks(self) -> dict[str, UnifiedTask]:
        return dict(self._completed)


__all__ = [
    "TaskCategory",
    "UnifiedTaskStatus",
    "TaskPhase",
    "UnifiedTask",
    "CircuitBreaker",
    "SchedulerStats",
    "TaskScheduler",
]
