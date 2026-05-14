"""Autonomous workflow orchestration with DAG scheduling and role-based agent assignment.

Design:
  - Workflows are DAGs (Directed Acyclic Graphs) of tasks
  - Each task declares required capabilities/roles
  - The orchestrator auto-assigns tasks to capable agents
  - Tasks run in parallel when their dependencies are satisfied
  - Failed tasks can be retried or escalated
  - The orchestrator itself runs autonomously within governance bounds
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from .agent_comm import AgentCommunicationBus, AgentMessage, AgentMessageType

logger = logging.getLogger(__name__)


class TaskState(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class WorkflowTask:
    """工作流DAG中的单个任务。"""

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    required_roles: set[str] = field(default_factory=set)
    required_capabilities: set[str] = field(default_factory=set)
    dependencies: set[str] = field(default_factory=set)
    payload: dict[str, Any] = field(default_factory=dict)
    state: TaskState = TaskState.PENDING
    assigned_agent: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 2
    priority: int = 0
    timeout_seconds: float = 300.0
    started_at: str | None = None
    finished_at: str | None = None

    def is_ready(self, completed: set[str]) -> bool:
        return self.state == TaskState.PENDING and self.dependencies.issubset(completed)

    def mark_running(self, agent_id: str) -> None:
        self.state = TaskState.RUNNING
        self.assigned_agent = agent_id
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_success(self, result: dict[str, Any] | None = None) -> None:
        self.state = TaskState.SUCCESS
        self.result = result or {}
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        if self.retry_count < self.max_retries:
            self.state = TaskState.RETRYING
            self.retry_count += 1
        else:
            self.state = TaskState.FAILED
        self.error = error

    def mark_retry_ready(self) -> None:
        if self.state == TaskState.RETRYING:
            self.state = TaskState.PENDING
            self.started_at = None
            self.finished_at = None


@dataclass
class AgentProfile:
    """可用于任务分配的代理配置。"""

    agent_id: str
    roles: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    current_tasks: int = 0
    reliability_score: float = 1.0

    @property
    def is_available(self) -> bool:
        return self.current_tasks < self.max_concurrent_tasks

    def can_handle(self, task: WorkflowTask) -> bool:
        if not self.is_available:
            return False
        if task.required_roles and not task.required_roles.intersection(self.roles):
            return False
        if task.required_capabilities and not task.required_capabilities.intersection(self.capabilities):
            return False
        return True

    def suitability_score(self, task: WorkflowTask) -> float:
        if not self.can_handle(task):
            return 0.0
        role_match = len(task.required_roles.intersection(self.roles)) / max(len(task.required_roles), 1)
        cap_match = len(task.required_capabilities.intersection(self.capabilities)) / max(len(task.required_capabilities), 1)
        load_factor = 1.0 - (self.current_tasks / self.max_concurrent_tasks)
        return (role_match * 0.4 + cap_match * 0.3 + load_factor * 0.2 + self.reliability_score * 0.1)


@dataclass
class WorkflowResult:
    """工作流执行的最终结果。"""

    workflow_id: str
    success: bool
    task_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed_tasks: list[str] = field(default_factory=list)
    skipped_tasks: list[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    agent_assignments: dict[str, str] = field(default_factory=dict)


class WorkflowDAG:
    """定义为任务DAG的工作流。"""

    def __init__(self, name: str, workflow_id: str | None = None) -> None:
        self.name = name
        self.workflow_id = workflow_id or uuid.uuid4().hex[:12]
        self._tasks: dict[str, WorkflowTask] = {}
        self._created_at = datetime.now(timezone.utc).isoformat()

    def add_task(self, task: WorkflowTask) -> None:
        self._tasks[task.task_id] = task

    def remove_task(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
        for t in self._tasks.values():
            t.dependencies.discard(task_id)

    def get_task(self, task_id: str) -> WorkflowTask | None:
        return self._tasks.get(task_id)

    @property
    def tasks(self) -> list[WorkflowTask]:
        return list(self._tasks.values())

    def validate(self) -> list[str]:
        """验证DAG结构。返回错误消息列表。"""
        errors: list[str] = []
        all_ids = set(self._tasks.keys())
        for task in self._tasks.values():
            missing = task.dependencies - all_ids
            if missing:
                errors.append(f"Task '{task.task_id}' has missing dependencies: {missing}")

        visited: set[str] = set()
        path: set[str] = set()

        def _check_cycle(tid: str) -> None:
            if tid in path:
                errors.append(f"Cycle detected involving task '{tid}'")
                return
            if tid in visited:
                return
            path.add(tid)
            task = self._tasks.get(tid)
            if task:
                for dep in task.dependencies:
                    _check_cycle(dep)
            path.discard(tid)
            visited.add(tid)

        for tid in self._tasks:
            _check_cycle(tid)

        return errors

    def get_ready_tasks(self) -> list[WorkflowTask]:
        completed = {
            tid for tid, t in self._tasks.items()
            if t.state == TaskState.SUCCESS
        }
        ready = [t for t in self._tasks.values() if t.is_ready(completed)]
        ready.sort(key=lambda t: -t.priority)
        return ready

    def get_retry_ready_tasks(self) -> list[WorkflowTask]:
        retrying = [t for t in self._tasks.values() if t.state == TaskState.RETRYING]
        for t in retrying:
            t.mark_retry_ready()
        return retrying

    @property
    def is_complete(self) -> bool:
        return all(
            t.state in {TaskState.SUCCESS, TaskState.FAILED, TaskState.SKIPPED}
            for t in self._tasks.values()
        )

    @property
    def has_failures(self) -> bool:
        return any(t.state == TaskState.FAILED for t in self._tasks.values())

    def skip_dependents_of_failed(self) -> list[str]:
        failed_ids = {tid for tid, t in self._tasks.items() if t.state == TaskState.FAILED}
        skipped: list[str] = []
        changed = True
        while changed:
            changed = False
            for tid, task in self._tasks.items():
                if task.state != TaskState.PENDING:
                    continue
                if task.dependencies.intersection(failed_ids):
                    task.state = TaskState.SKIPPED
                    failed_ids.add(tid)
                    skipped.append(tid)
                    changed = True
        return skipped


class WorkflowOrchestrator:
    """Orchestrates workflow execution with automatic agent assignment.

        Features:
          - DAG validation before execution
          - Automatic agent assignment based on role/capability 匹配
          - Parallel execution of independent tasks
          - Retry with configurable max retries
          - Cascading skip of tasks dependent on failed tasks
          - Integration with AgentCommunicationBus for coordination
"""

    def __init__(
        self,
        comm_bus: AgentCommunicationBus | None = None,
        task_executor: Callable[[WorkflowTask, str], Any] | None = None,
    ) -> None:
        self.comm_bus = comm_bus
        self._executor = task_executor or self._default_executor
        self._agents: dict[str, AgentProfile] = {}
        self._active_workflows: dict[str, WorkflowDAG] = {}
        self._lock = asyncio.Lock()

    def register_agent(self, profile: AgentProfile) -> None:
        self._agents[profile.agent_id] = profile

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def _assign_agent(self, task: WorkflowTask) -> str | None:
        candidates = [
            (profile.agent_id, profile.suitability_score(task))
            for profile in self._agents.values()
        ]
        candidates = [(aid, score) for aid, score in candidates if score > 0]
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[1])
        best_id = candidates[0][0]
        self._agents[best_id].current_tasks += 1
        return best_id

    def _release_agent(self, agent_id: str) -> None:
        profile = self._agents.get(agent_id)
        if profile and profile.current_tasks > 0:
            profile.current_tasks -= 1

    async def execute(self, workflow: WorkflowDAG) -> WorkflowResult:
        """执行工作流DAG。所有任务完成或失败时返回。"""
        errors = workflow.validate()
        if errors:
            logger.error("Workflow validati在failed: %s", errors)
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                success=False,
                failed_tasks=["validation"],
            )

        self._active_workflows[workflow.workflow_id] = workflow
        start_time = datetime.now(timezone.utc)

        try:
            while not workflow.is_complete:
                ready = workflow.get_ready_tasks()
                retry_ready = workflow.get_retry_ready_tasks()
                all_ready = ready + retry_ready

                if not all_ready and not workflow.is_complete:
                    skipped = workflow.skip_dependents_of_failed()
                    if skipped:
                        continue
                    if workflow.has_failures:
                        break
                    await asyncio.sleep(0.5)
                    continue

                tasks_to_run: list[asyncio.Task[None]] = []
                for task in all_ready:
                    agent_id = self._assign_agent(task)
                    if agent_id is None:
                        logger.warning(
                            "No available agent for task '%s' (roles=%s, caps=%s)",
                            task.name,
                            task.required_roles,
                            task.required_capabilities,
                        )
                        continue
                    task.mark_running(agent_id)
                    coro = self._run_task(workflow, task, agent_id)
                    tasks_to_run.append(asyncio.create_task(coro))

                if tasks_to_run:
                    await asyncio.gather(*tasks_to_run, return_exceptions=True)

            skipped_ids = workflow.skip_dependents_of_failed()
        finally:
            self._active_workflows.pop(workflow.workflow_id, None)

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        task_results = {tid: t.result for tid, t in workflow._tasks.items()}
        failed = [tid for tid, t in workflow._tasks.items() if t.state == TaskState.FAILED]
        skipped = [tid for tid, t in workflow._tasks.items() if t.state == TaskState.SKIPPED]
        assignments = {tid: t.assigned_agent for tid, t in workflow._tasks.items() if t.assigned_agent}

        return WorkflowResult(
            workflow_id=workflow.workflow_id,
            success=len(failed) == 0,
            task_results=task_results,
            failed_tasks=failed,
            skipped_tasks=skipped,
            total_duration_seconds=duration,
            agent_assignments=assignments,
        )

    async def _run_task(self, workflow: WorkflowDAG, task: WorkflowTask, agent_id: str) -> None:
        """执行带有超时和错误处理的单个任务。"""
        try:
            result = await asyncio.wait_for(
                self._execute_with_comm(workflow, task, agent_id),
                timeout=task.timeout_seconds,
            )
            task.mark_success(result)
            if self.comm_bus:
                self.comm_bus.broadcast(
                    sender_id="orchestrator",
                    payload={
                        "event": "task_completed",
                        "workflow_id": workflow.workflow_id,
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "agent_id": agent_id,
                    },
                    target_role="orchestrator",
                )
        except asyncio.TimeoutError:
            task.mark_failed(f"Timeout after {task.timeout_seconds}s")
        except Exception as e:
            task.mark_failed(str(e))
        finally:
            self._release_agent(agent_id)

    async def _execute_with_comm(
        self,
        workflow: WorkflowDAG,
        task: WorkflowTask,
        agent_id: str,
    ) -> dict[str, Any]:
        if self.comm_bus:
            try:
                response = await self.comm_bus.request(
                    sender_id="orchestrator",
                    target_id=agent_id,
                    payload={
                        "workflow_id": workflow.workflow_id,
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "task_payload": task.payload,
                    },
                    timeout_seconds=task.timeout_seconds,
                )
                return response.payload
            except asyncio.TimeoutError:
                pass

        result = self._executor(task, agent_id)
        if asyncio.iscoroutine(result):
            result = await result
        return result if isinstance(result, dict) else {"result": result}

    def _default_executor(self, task: WorkflowTask, agent_id: str) -> dict[str, Any]:
        return {"status": "executed", "agent": agent_id}

    @property
    def active_workflow_count(self) -> int:
        return len(self._active_workflows)

    def get_agent_utilization(self) -> dict[str, dict[str, Any]]:
        return {
            aid: {
                "roles": list(p.roles),
                "current_tasks": p.current_tasks,
                "max_tasks": p.max_concurrent_tasks,
                "utilization": p.current_tasks / p.max_concurrent_tasks if p.max_concurrent_tasks > 0 else 0,
                "reliability": p.reliability_score,
            }
            for aid, p in self._agents.items()
        }


__all__ = [
    "TaskState",
    "WorkflowTask",
    "AgentProfile",
    "WorkflowResult",
    "WorkflowDAG",
    "WorkflowOrchestrator",
]
