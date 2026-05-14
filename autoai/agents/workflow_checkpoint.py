"""Workflow checkpoint and recovery.

Enables DAG workflow persistence to disk so that:
- Long-running workflows can survive process restarts
- Failed workflows can be resumed from the last successful task
- Workflow state can be inspected offline

Checkpoint format: JSON with all task states and results.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkflowCheckpoint:
    """工作流执行状态的快照。"""

    workflow_id: str
    workflow_name: str = ""
    created_at: str = ""
    saved_at: str = ""
    task_states: dict[str, str] = field(default_factory=dict)
    task_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_assignments: dict[str, str] = field(default_factory=dict)
    task_errors: dict[str, str] = field(default_factory=dict)
    task_retry_counts: dict[str, int] = field(default_factory=dict)
    task_dependencies: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "created_at": self.created_at,
            "saved_at": self.saved_at,
            "task_states": self.task_states,
            "task_results": self.task_results,
            "task_assignments": self.task_assignments,
            "task_errors": self.task_errors,
            "task_retry_counts": self.task_retry_counts,
            "task_dependencies": self.task_dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowCheckpoint:
        return cls(
            workflow_id=data["workflow_id"],
            workflow_name=data.get("workflow_name", ""),
            created_at=data.get("created_at", ""),
            saved_at=data.get("saved_at", ""),
            task_states=data.get("task_states", {}),
            task_results=data.get("task_results", {}),
            task_assignments=data.get("task_assignments", {}),
            task_errors=data.get("task_errors", {}),
            task_retry_counts=data.get("task_retry_counts", {}),
            task_dependencies=data.get("task_dependencies", {}),
        )


class CheckpointManager:
    """Save and load workflow checkpoints to/from JSON files.

    Thread-safe. Checkpoints are stored in a configurable directory.
    """

    def __init__(self, checkpoint_dir: str | Path = "governance/checkpoints") -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def save(self, checkpoint: WorkflowCheckpoint) -> Path:
        checkpoint.saved_at = datetime.now(timezone.utc).isoformat()
        path = self.checkpoint_dir / f"{checkpoint.workflow_id}.json"
        data = json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=False)
        with self._lock:
            path.write_text(data, encoding="utf-8")
        logger.info("[checkpoint] 保存d 工作流 %s 到%s", checkpoint.workflow_id, path)
        return path

    def load(self, workflow_id: str) -> WorkflowCheckpoint | None:
        path = self.checkpoint_dir / f"{workflow_id}.json"
        if not path.exists():
            return None
        with self._lock:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return WorkflowCheckpoint.from_dict(data)
            except Exception as e:
                logger.error("[checkpoint] Failed 到load %s: %s", workflow_id, e)
                return None

    def delete(self, workflow_id: str) -> bool:
        path = self.checkpoint_dir / f"{workflow_id}.json"
        with self._lock:
            if path.exists():
                path.unlink()
                return True
            return False

    def list_checkpoints(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self._lock:
            for path in sorted(self.checkpoint_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    results.append({
                        "workflow_id": data.get("workflow_id", ""),
                        "workflow_name": data.get("workflow_name", ""),
                        "saved_at": data.get("saved_at", ""),
                        "tasks_total": len(data.get("task_states", {})),
                        "tasks_completed": sum(
                            1 for s in data.get("task_states", {}).values()
                            if s == "success"
                        ),
                    })
                except Exception:
                    pass
        return results

    def snapshot_workflow(self, workflow: Any) -> WorkflowCheckpoint:
        """Create a checkpoint from a WorkflowDAG 实例."""
        checkpoint = WorkflowCheckpoint(
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
        )
        for task in workflow.tasks:
            checkpoint.task_states[task.task_id] = task.state.value
            checkpoint.task_results[task.task_id] = task.result
            checkpoint.task_assignments[task.task_id] = task.assigned_agent or ""
            checkpoint.task_errors[task.task_id] = task.error or ""
            checkpoint.task_retry_counts[task.task_id] = task.retry_count
            checkpoint.task_dependencies[task.task_id] = list(task.dependencies)
        return checkpoint

    def restore_workflow(self, workflow: Any, checkpoint: WorkflowCheckpoint) -> int:
        """从检查点恢复WorkflowDAG。返回恢复的任务数。"""
        from autoai.agents.workflow_orchestrator import TaskState

        restored = 0
        for task in workflow.tasks:
            state_str = checkpoint.task_states.get(task.task_id)
            if state_str is None:
                continue
            try:
                task.state = TaskState(state_str)
            except ValueError:
                continue
            task.result = checkpoint.task_results.get(task.task_id, {})
            task.assigned_agent = checkpoint.task_assignments.get(task.task_id) or None
            task.error = checkpoint.task_errors.get(task.task_id) or None
            task.retry_count = checkpoint.task_retry_counts.get(task.task_id, 0)
            restored += 1
        logger.info(
            "[checkpoint] Restored %d/%d tasks for workflow %s",
            restored, len(workflow.tasks), workflow.workflow_id,
        )
        return restored

    def auto_save(self, workflow: Any, interval_seconds: float = 30.0) -> threading.Thread:
        """启动定期保存检查点的后台线程。"""
        stop_event = threading.Event()

        def _loop():
            while not stop_event.is_set():
                checkpoint = self.snapshot_workflow(workflow)
                self.save(checkpoint)
                stop_event.wait(timeout=interval_seconds)

        thread = threading.Thread(target=_loop, name="checkpoint-auto-save", daemon=True)
        thread.start()
        return thread


__all__ = [
    "WorkflowCheckpoint",
    "CheckpointManager",
]
