"""Local backend — single-process, for development and testing.

All tasks run in the current process via asyncio. No external dependencies.
Simulates the distributed interface for seamless local→distributed upgrade.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .base import AgentSpec, DispatchFuture, DistributedBackend, WorkerInfo, WorkerStatus

logger = logging.getLogger(__name__)


class LocalBackend(DistributedBackend):
    """Single-process local execution backend.

    Tasks are executed via asyncio in the current process.
    Simulates worker assignment for interface compatibility.
    """

    def __init__(self, max_concurrent: int = 4) -> None:
        super().__init__()
        self._max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
        self._executor: Any = None
        self._pending: dict[str, DispatchFuture] = {}

    def set_executor(self, executor: Any) -> None:
        self._executor = executor

    async def start(self) -> None:
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        local_worker = WorkerInfo(
            worker_id="local-0",
            address="localhost",
            status=WorkerStatus.IDLE,
            roles={"coordinator", "executor", "researcher", "coder"},
            capabilities={"chat", "code", "file", "web"},
        )
        self.register_worker(local_worker)
        self._running = True
        logger.info("[distributed:local] Started with %d concurrent slots", self._max_concurrent)

    async def stop(self) -> None:
        self._running = False
        self._workers.clear()
        logger.info("[distributed:local] Stopped")

    async def dispatch(
        self,
        task: Any,
        agent_spec: AgentSpec | None = None,
        preferred_worker: str | None = None,
    ) -> DispatchFuture:
        if not self._running:
            raise RuntimeError("Backend not started")

        worker = self.select_worker(
            required_roles=agent_spec.role if agent_spec else None,
        ) if not preferred_worker else self._workers.get(preferred_worker)

        if not worker:
            worker = self._workers.get("local-0")

        if not worker:
            future = DispatchFuture(task_id=getattr(task, "task_id", ""))
            future.set_error("No available worker")
            return future

        future = DispatchFuture(
            task_id=getattr(task, "task_id", ""),
            worker_id=worker.worker_id,
        )
        self._pending[future.future_id] = future

        worker.status = WorkerStatus.BUSY
        worker.current_task_id = getattr(task, "task_id", "")

        asyncio.create_task(self._execute_task(task, future, worker))

        return future

    async def get_result(self, future: DispatchFuture, timeout: float = 300.0) -> Any:
        deadline = time.monotonic() + timeout
        while not future.done:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(f"Result not available after {timeout}s")
            await asyncio.sleep(min(0.1, remaining))
        if future.error:
            raise RuntimeError(future.error)
        return future.result

    async def _execute_task(self, task: Any, future: DispatchFuture, worker: WorkerInfo) -> None:
        if self._semaphore:
            async with self._semaphore:
                await self._run(task, future, worker)
        else:
            await self._run(task, future, worker)

    async def _run(self, task: Any, future: DispatchFuture, worker: WorkerInfo) -> None:
        try:
            if self._executor:
                if asyncio.iscoroutinefunction(self._executor):
                    result = await self._executor(task)
                else:
                    result = self._executor(task)
            else:
                result = await self._default_execute(task)

            future.set_result(result)
            worker.tasks_completed += 1

        except Exception as e:
            future.set_error(str(e))
            worker.tasks_failed += 1
            logger.error("[distributed:local] Task %s failed: %s", future.task_id, e)

        finally:
            worker.status = WorkerStatus.IDLE
            worker.current_task_id = None
            self._pending.pop(future.future_id, None)

    async def _default_execute(self, task: Any) -> dict[str, Any]:
        await asyncio.sleep(0.01)
        return {
            "status": "executed",
            "task_id": getattr(task, "task_id", ""),
            "task_name": getattr(task, "name", ""),
        }


__all__ = ["LocalBackend"]
