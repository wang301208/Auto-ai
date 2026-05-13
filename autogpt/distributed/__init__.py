"""Distributed execution layer for AutoGPT.

Enables cross-machine Agent scheduling via pluggable backends:
  - LocalBackend: single-process, for development/testing
  - RayBackend: multi-node via Ray, for production scaling

Design:
  - DistributedBackend: abstract interface
  - AgentWorker: a stateless worker that runs one agent step
  - TaskDispatcher: distributes UnifiedTask to available workers
  - Results aggregated via async futures

Usage:
    from autogpt.distributed import LocalBackend

    backend = LocalBackend()
    await backend.start()
    future = await backend.dispatch(task, agent_spec)
    result = await future
    await backend.stop()
"""

from .base import DistributedBackend, WorkerInfo, DispatchFuture, AgentSpec
from .local_backend import LocalBackend

RayBackend = None
try:
    from .ray_backend import RayBackend
except (ImportError, Exception):
    pass

__all__ = [
    "DistributedBackend",
    "WorkerInfo",
    "DispatchFuture",
    "LocalBackend",
    "RayBackend",
]
