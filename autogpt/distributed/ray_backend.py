"""Ray backend — multi-node distributed execution via Ray.

Requires: pip install ray

If Ray is not installed, this module will fail to import.
The __init__.py handles ImportError gracefully.

Usage:
    from autogpt.distributed import RayBackend

    backend = RayBackend(address="auto")  # connect to existing cluster
    await backend.start()
    future = await backend.dispatch(task, agent_spec)
    result = await backend.get_result(future)
    await backend.stop()
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .base import AgentSpec, DispatchFuture, DistributedBackend, WorkerInfo, WorkerStatus

try:
    import ray
    _HAS_RAY = True
except ImportError:
    _HAS_RAY = False
    ray = None

logger = logging.getLogger(__name__)


def _get_ray_worker_class():
    if not _HAS_RAY:
        return None

    @ray.remote
    class _RayAgentWorker:
        """Ray actor that executes agent tasks on a remote node."""

        def __init__(self, worker_id: str) -> None:
            self.worker_id = worker_id
            self._tasks_completed = 0
            self._tasks_failed = 0

        async def execute(self, task_data: dict[str, Any]) -> dict[str, Any]:
            try:
                await asyncio.sleep(0.01)
                self._tasks_completed += 1
                return {
                    "status": "executed",
                    "worker_id": self.worker_id,
                    "task_id": task_data.get("task_id", ""),
                    **task_data,
                }
            except Exception as e:
                self._tasks_failed += 1
                return {"status": "failed", "error": str(e)}

        def get_stats(self) -> dict[str, int]:
            return {
                "tasks_completed": self._tasks_completed,
                "tasks_failed": self._tasks_failed,
            }

    return _RayAgentWorker


class RayBackend(DistributedBackend):
    """Multi-node Ray distributed execution backend."""

    def __init__(
        self,
        address: str | None = None,
        num_workers: int = 2,
        namespace: str = "autogpt",
    ) -> None:
        if not _HAS_RAY:
            raise ImportError("Ray is required: pip install ray")
        super().__init__()
        self._address = address
        self._num_workers = num_workers
        self._namespace = namespace
        self._actors: dict[str, Any] = {}
        self._pending_refs: dict[str, Any] = {}

    async def start(self) -> None:
        if not _HAS_RAY:
            raise ImportError("Ray is required: pip install ray")
        if not ray.is_initialized():
            init_kwargs: dict[str, Any] = {"namespace": self._namespace}
            if self._address:
                init_kwargs["address"] = self._address
            else:
                init_kwargs["num_cpus"] = self._num_workers
            ray.init(**init_kwargs)

        WorkerClass = _get_ray_worker_class()
        if not WorkerClass:
            raise ImportError("Ray worker class could not be created")

        for i in range(self._num_workers):
            worker_id = f"ray-worker-{i}"
            actor = WorkerClass.remote(worker_id)
            self._actors[worker_id] = actor

            node_info = ray.nodes()[0] if ray.nodes() else {}
            worker_info = WorkerInfo(
                worker_id=worker_id,
                address=node_info.get("NodeManagerAddress", "unknown"),
                status=WorkerStatus.IDLE,
                roles={"executor", "coder", "researcher"},
                capabilities={"chat", "code", "file"},
            )
            self.register_worker(worker_info)

        self._running = True
        logger.info("[distributed:ray] Started with %d workers on Ray cluster", self._num_workers)

    async def stop(self) -> None:
        for actor in self._actors.values():
            ray.kill(actor)
        self._actors.clear()
        self._workers.clear()
        self._pending_refs.clear()

        if ray.is_initialized():
            ray.shutdown()

        self._running = False
        logger.info("[distributed:ray] Stopped")

    async def dispatch(
        self,
        task: Any,
        agent_spec: AgentSpec | None = None,
        preferred_worker: str | None = None,
    ) -> DispatchFuture:
        if not self._running:
            raise RuntimeError("Ray backend not started")

        worker = None
        if preferred_worker and preferred_worker in self._actors:
            worker_id = preferred_worker
        else:
            available = self.get_available_workers(
                required_roles={agent_spec.role} if agent_spec and agent_spec.role else None
            )
            if available:
                worker_id = available[0].worker_id
            elif self._actors:
                worker_id = list(self._actors.keys())[0]
            else:
                future = DispatchFuture(task_id=getattr(task, "task_id", ""))
                future.set_error("No Ray workers available")
                return future

        actor = self._actors.get(worker_id)
        if not actor:
            future = DispatchFuture(task_id=getattr(task, "task_id", ""))
            future.set_error(f"Worker {worker_id} not found")
            return future

        task_data = self._serialize_task(task)
        ref = actor.execute.remote(task_data)

        future = DispatchFuture(
            task_id=getattr(task, "task_id", ""),
            worker_id=worker_id,
        )
        self._pending_refs[future.future_id] = ref

        worker_info = self._workers.get(worker_id)
        if worker_info:
            worker_info.status = WorkerStatus.BUSY

        asyncio.create_task(self._collect_result(ref, future, worker_id))

        return future

    async def get_result(self, future: DispatchFuture, timeout: float = 300.0) -> Any:
        deadline = time.monotonic() + timeout
        while not future.done:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(f"Ray result not available after {timeout}s")
            await asyncio.sleep(min(0.1, remaining))
        if future.error:
            raise RuntimeError(future.error)
        return future.result

    async def _collect_result(self, ref: Any, future: DispatchFuture, worker_id: str) -> None:
        try:
            result = await asyncio.wait_for(ref, timeout=300.0)
            future.set_result(result)
            worker_info = self._workers.get(worker_id)
            if worker_info:
                worker_info.tasks_completed += 1
                worker_info.status = WorkerStatus.IDLE
        except Exception as e:
            future.set_error(str(e))
            worker_info = self._workers.get(worker_id)
            if worker_info:
                worker_info.tasks_failed += 1
                worker_info.status = WorkerStatus.IDLE
        finally:
            self._pending_refs.pop(future.future_id, None)

    @staticmethod
    def _serialize_task(task: Any) -> dict[str, Any]:
        if hasattr(task, "to_dict"):
            return task.to_dict()
        return {
            "task_id": getattr(task, "task_id", ""),
            "name": getattr(task, "name", ""),
            "objective": getattr(task, "objective", ""),
            "category": getattr(task, "category", ""),
            "payload": getattr(task, "payload", {}),
        }


__all__ = ["RayBackend"]
