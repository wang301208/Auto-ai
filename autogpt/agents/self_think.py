"""Self-Think: Agent autonomously reviews and improves itself.

When no external tasks are pending, the agent enters a self-review loop:
1. Scan codebase for improvement opportunities (coverage, lint, perf, TODOs)
2. Generate Task objects for each opportunity
3. Inject them into the task queue with appropriate priority
4. Continue the normal think() cycle

This makes the agent self-driven rather than waiting for human input.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from autogpt.core.planning.schema import Task, TaskStatus, TaskType
from autogpt.event_bus import EventMessage
from autogpt.logs import logger
from autogpt.self_improve import DatabaseManager, PluginTodoQueue


class SelfReviewSource:
    """Base class for self-review sources that discover improvement opportunities."""

    name: str = "base"

    def discover(self, workspace: Path) -> list[dict]:
        """Return list of improvement dicts: {objective, type, priority, context}."""
        return []


class CoverageSource(SelfReviewSource):
    """Discover files with low test coverage."""

    name = "coverage"
    threshold: float = 80.0

    def __init__(self, threshold: float = 80.0):
        self.threshold = threshold

    def discover(self, workspace: Path) -> list[dict]:
        items = []
        coverage_file = workspace / "coverage.json"
        if not coverage_file.exists():
            return items
        try:
            data = json.loads(coverage_file.read_text(encoding="utf-8"))
            for path, info in data.get("files", {}).items():
                summary = info.get("summary", {})
                pct = summary.get("percent_covered", 100.0)
                if pct < self.threshold:
                    items.append({
                        "objective": f"Improve test coverage for {path} ({pct:.0f}%)",
                        "type": TaskType.TEST,
                        "priority": 2,
                        "context": f"Coverage {pct:.0f}% below threshold {self.threshold}%",
                    })
        except Exception as e:
            logger.debug(f"Coverage scan failed: {e}")
        return items


class LintSource(SelfReviewSource):
    """Discover lint/type errors."""

    name = "lint"
    checks = (
        ["ruff", "check", "--quiet"],
        ["mypy", "--no-error-summary", "--quiet"],
    )

    def discover(self, workspace: Path) -> list[dict]:
        items = []
        for cmd in self.checks:
            try:
                result = subprocess.run(
                    cmd + [str(workspace)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode != 0:
                    errors = (result.stdout + result.stderr)[:500]
                    items.append({
                        "objective": f"Fix lint errors from {' '.join(cmd[:2])}",
                        "type": TaskType.EDIT,
                        "priority": 2,
                        "context": errors,
                    })
            except Exception:
                pass
        return items


class PerformanceSource(SelfReviewSource):
    """Discover performance hotspots from DatabaseManager."""

    name = "performance"
    threshold: float = 1.0

    def __init__(self, db: DatabaseManager | None = None, threshold: float = 1.0):
        self.db = db
        self.threshold = threshold

    def discover(self, workspace: Path) -> list[dict]:
        items = []
        if self.db is None:
            return items
        try:
            for func, total in self.db.get_hotspots(self.threshold):
                items.append({
                    "objective": f"Optimize {func} ({total:.2f}s)",
                    "type": TaskType.CODE,
                    "priority": 1,
                    "context": f"Hotspot: {func} total={total:.2f}s",
                })
        except Exception as e:
            logger.debug(f"Performance scan failed: {e}")
        return items


class TodoSource(SelfReviewSource):
    """Discover pending TODOs from PluginTodoQueue."""

    name = "todo"

    def __init__(self, plugin_queue: PluginTodoQueue | None = None):
        self.plugin_queue = plugin_queue

    def discover(self, workspace: Path) -> list[dict]:
        items = []
        if self.plugin_queue is None:
            return items
        while True:
            todo = self.plugin_queue.pop()
            if todo is None:
                break
            items.append({
                "objective": f"Resolve TODO: {todo.gap}",
                "type": TaskType.CODE,
                "priority": 3,
                "context": todo.context,
            })
        return items


class SelfThinkEngine:
    """Orchestrates the self-review cycle with auto-fix and verification.

    Full loop: scan → discover → prioritize → fix → verify → adjust policy
    When the agent has no pending tasks, this engine scans for
    improvement opportunities and injects them as Tasks.

    Phase 18 extension: architecture self-diagnosis and refactoring.
    When arch_diagnoser is provided, scan() also discovers architecture
    issues and auto_fix_cycle() can apply refactoring patches via ArchRefactorer.
    """

    def __init__(
        self,
        workspace: Path,
        sources: list[SelfReviewSource] | None = None,
        message_queue: Any = None,
        agent_name: str = "AutoGPT",
        max_self_tasks: int = 5,
        auto_fix: bool = True,
        verify_after_fix: bool = True,
        policy_evolver: Any | None = None,
        self_modify_pipeline: Any | None = None,
        arch_diagnoser: Any | None = None,
        arch_refactorer: Any | None = None,
        capability_injector: Any | None = None,
        protocol_upgrader: Any | None = None,
        boundary_manager: Any | None = None,
    ):
        self.workspace = workspace
        self.message_queue = message_queue
        self.agent_name = agent_name
        self.max_self_tasks = max_self_tasks
        self.auto_fix = auto_fix
        self.verify_after_fix = verify_after_fix
        self._policy_evolver = policy_evolver
        self._self_modify_pipeline = self_modify_pipeline
        self._arch_diagnoser = arch_diagnoser
        self._arch_refactorer = arch_refactorer
        self._capability_injector = capability_injector
        self._protocol_upgrader = protocol_upgrader
        self._boundary_manager = boundary_manager
        self._sources = sources or []
        self._scan_count = 0
        self._fix_count = 0
        self._fix_success = 0
        self._fix_failed = 0
        self._verify_count = 0
        self._history: list[dict] = []
        self._arch_scan_count = 0
        self._arch_fix_count = 0

    def add_source(self, source: SelfReviewSource) -> None:
        self._sources.append(source)

    def scan(self) -> list[Task]:
        """Run all sources and collect improvement opportunities as Tasks."""
        all_items = []
        for source in self._sources:
            try:
                items = source.discover(self.workspace)
                all_items.extend(items)
                logger.debug(f"[SelfThink] {source.name}: found {len(items)} items")
            except Exception as e:
                logger.warning(f"[SelfThink] {source.name} scan failed: {e}")

        all_items.sort(key=lambda x: x.get("priority", 1), reverse=True)
        all_items = all_items[: self.max_self_tasks]

        tasks = []
        for item in all_items:
            task = Task(
                objective=item["objective"],
                type=item.get("type", TaskType.CODE),
                priority=item.get("priority", 1),
                ready_criteria=["Issue identified"],
                acceptance_criteria=["Issue resolved"],
            )
            tasks.append(task)

        self._scan_count += 1

        if self.message_queue and tasks:
            self.message_queue.publish(
                EventMessage(
                    event_type="self_review",
                    payload={
                        "scan_count": self._scan_count,
                        "tasks_found": len(tasks),
                        "sources": [s.name for s in self._sources],
                    },
                    source_agent=self.agent_name,
                )
            )

        return tasks

    def inject_into_queue(self, task_queue: list[Task]) -> int:
        """Scan and inject self-improvement tasks into the given queue.

        Returns the number of tasks injected.
        """
        new_tasks = self.scan()
        if not new_tasks:
            return 0

        existing_objectives = {t.objective for t in task_queue}
        injected = 0
        for task in new_tasks:
            if task.objective not in existing_objectives:
                task_queue.append(task)
                existing_objectives.add(task.objective)
                injected += 1

        if injected > 0:
            task_queue.sort(key=lambda t: t.priority, reverse=True)
            logger.info(f"[SelfThink] Injected {injected} self-improvement tasks")

        return injected

    async def auto_fix_cycle(self, task_queue: list[Task], fix_executor: Any | None = None) -> dict[str, Any]:
        """Complete self-evolution cycle: scan → fix → verify → policy adjust.

        When self_modify_pipeline is available and autonomy >= L2,
        uses the full self-modification pipeline (patch→apply→test→commit→reload).
        Otherwise falls back to the basic fix_executor.

        Args:
            task_queue: The agent's task queue to inject into
            fix_executor: Optional callable(task) -> result for executing fixes

        Returns:
            Summary dict with counts of discovered/fixed/verified/failed
        """
        summary = {
            "discovered": 0,
            "fixed": 0,
            "verified": 0,
            "failed": 0,
            "policy_adjusted": False,
            "self_modified": 0,
            "reverted": 0,
        }

        new_tasks = self.scan()
        summary["discovered"] = len(new_tasks)
        if not new_tasks:
            return summary

        existing_objectives = {t.objective for t in task_queue}

        for task in new_tasks:
            if task.objective in existing_objectives:
                continue

            if not self.auto_fix or (fix_executor is None and self._self_modify_pipeline is None):
                task_queue.append(task)
                existing_objectives.add(task.objective)
                continue

            if self._self_modify_pipeline is not None and self._self_modify_pipeline.can_modify:
                mod_result = await self._execute_self_modification(task)
                self._fix_count += 1
                if mod_result.get("success"):
                    self._fix_success += 1
                    summary["fixed"] += 1
                    summary["self_modified"] += 1
                    summary["verified"] += 1
                    task.context.status = TaskStatus.DONE
                    self._record_history(task, "self_modified_and_verified", mod_result)
                else:
                    self._fix_failed += 1
                    summary["failed"] += 1
                    if mod_result.get("reverted"):
                        summary["reverted"] += 1
                    task_queue.append(task)
                    existing_objectives.add(task.objective)
                    self._record_history(task, "self_modify_failed", mod_result)
                continue

            fix_result = await self._attempt_fix(task, fix_executor)
            self._fix_count += 1

            if fix_result.get("success"):
                self._fix_success += 1
                summary["fixed"] += 1

                if self.verify_after_fix:
                    verified = await self._verify_fix(task, fix_result)
                    self._verify_count += 1
                    if verified:
                        summary["verified"] += 1
                        task.context.status = TaskStatus.DONE
                        self._record_history(task, "fixed_and_verified", fix_result)
                    else:
                        summary["failed"] += 1
                        self._fix_failed += 1
                        task_queue.append(task)
                        existing_objectives.add(task.objective)
                        self._record_history(task, "fix_verification_failed", fix_result)
                else:
                    summary["verified"] += 1
                    task.context.status = TaskStatus.DONE
                    self._record_history(task, "fixed", fix_result)
            else:
                self._fix_failed += 1
                summary["failed"] += 1
                task_queue.append(task)
                existing_objectives.add(task.objective)
                self._record_history(task, "fix_failed", fix_result)

        if self._policy_evolver and summary["fixed"] > 0:
            try:
                self._policy_evolver.evolve_from_cycle(
                    fixed_count=summary["fixed"],
                    failed_count=summary["failed"],
                )
                summary["policy_adjusted"] = True
            except Exception as e:
                logger.warning(f"[SelfThink] Policy evolution failed: {e}")

        if self._boundary_manager is not None:
            try:
                for _ in range(summary["fixed"]):
                    self._boundary_manager.autonomy.record_success()
                for _ in range(summary["failed"]):
                    self._boundary_manager.autonomy.record_failure()
                summary["autonomy_level"] = self._boundary_manager.autonomy.level
            except Exception as e:
                logger.warning(f"[SelfThink] Boundary autonomy update failed: {e}")

        if self.message_queue and summary["discovered"] > 0:
            self.message_queue.publish(
                EventMessage(
                    event_type="self_evolution_cycle",
                    payload={
                        "scan_count": self._scan_count,
                        **summary,
                    },
                    source_agent=self.agent_name,
                )
            )

        return summary

    async def _attempt_fix(self, task: Task, fix_executor: Any) -> dict[str, Any]:
        """Attempt to fix a single issue."""
        try:
            if asyncio.iscoroutinefunction(fix_executor):
                result = await fix_executor(task)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: fix_executor(task))
            return {"success": True, "result": result}
        except Exception as e:
            logger.warn(f"[SelfThink] Fix failed for '{task.objective}': {e}")
            return {"success": False, "error": str(e)}

    async def _execute_self_modification(self, task: Task) -> dict[str, Any]:
        """Execute self-modification via SelfModifyPipeline.

        Generates a patch diff from the task, then delegates to the pipeline
        for apply→test→commit/revert→reload.
        """
        pipeline = self._self_modify_pipeline
        if pipeline is None:
            return {"success": False, "error": "no_pipeline"}

        patch_diff = f"# Auto-fix for: {task.objective}\n"
        target_files = []
        context = getattr(task, "context", None)
        if context and hasattr(context, "context"):
            target_files = [context.context] if isinstance(context.context, str) else []

        from governance.modification_chain import ModificationType
        mod_type = ModificationType.CODE_PATCH
        if task.type == TaskType.TEST:
            mod_type = ModificationType.CODE_PATCH
        elif task.type == TaskType.EDIT:
            mod_type = ModificationType.CODE_PATCH

        try:
            result = await pipeline.execute_modification(
                patch_diff=patch_diff,
                target_files=target_files or ["unknown"],
                mod_type=mod_type,
            )
            return result
        except Exception as e:
            logger.warn(f"[SelfThink] Self-modification failed for '{task.objective}': {e}")
            return {"success": False, "error": str(e)}

    async def _verify_fix(self, task: Task, fix_result: dict) -> bool:
        """Verify that a fix resolved the issue by re-scanning the relevant source."""
        if fix_result.get("result") and isinstance(fix_result["result"], dict) and fix_result["result"].get("fixed"):
            return True
        for source in self._sources:
            try:
                remaining = source.discover(self.workspace)
                for item in remaining:
                    if task.objective == item.get("objective", ""):
                        return False
            except Exception:
                pass
        return True

    def _record_history(self, task: Task, outcome: str, fix_result: dict) -> None:
        self._history.append({
            "objective": task.objective,
            "type": str(task.type),
            "outcome": outcome,
            "scan_count": self._scan_count,
            "fix_result_keys": list(fix_result.keys()),
        })

    def arch_diagnose(self) -> dict[str, Any] | None:
        """Run architecture self-diagnosis. Returns ArchReport summary or None."""
        if self._arch_diagnoser is None:
            return None
        try:
            report = self._arch_diagnoser.diagnose()
            self._arch_scan_count += 1

            if self.message_queue:
                self.message_queue.publish(
                    EventMessage(
                        event_type="arch_diagnosis",
                        payload=report.summary(),
                        source_agent=self.agent_name,
                    )
                )
            return report.summary()
        except Exception as e:
            logger.warn(f"[SelfThink] Architecture diagnosis failed: {e}")
            return None

    async def arch_refactor(self) -> dict[str, Any]:
        """Diagnose architecture issues and apply refactoring patches.

        Full loop: diagnose → generate plans → apply patches → verify.
        Requires arch_diagnoser, arch_refactorer, and self_modify_pipeline.
        """
        result = {"diagnosed": False, "plans_generated": 0, "plans_applied": 0, "plans_rejected": 0}

        if self._arch_diagnoser is None or self._arch_refactorer is None:
            return result

        try:
            report = self._arch_diagnoser.diagnose()
            self._arch_scan_count += 1
            result["diagnosed"] = True
            result["issues_found"] = len(report.issues)
            result["critical"] = report.critical_count

            if not report.issues:
                return result

            plans = self._arch_refactorer.generate_plans(report)
            result["plans_generated"] = len(plans)

            if not plans:
                return result

            if self._self_modify_pipeline and self._self_modify_pipeline.can_modify:
                refactor_result = await self._arch_refactorer.apply_plans(
                    plans, self_modify_pipeline=self._self_modify_pipeline,
                )
                result["plans_applied"] = refactor_result.plans_applied
                result["plans_rejected"] = refactor_result.plans_rejected
                self._arch_fix_count += refactor_result.plans_applied
            else:
                for plan in plans:
                    logger.info(f"[SelfThink] Refactor suggestion (not applied): {plan.description}")

        except Exception as e:
            logger.warn(f"[SelfThink] Architecture refactoring failed: {e}")
            result["error"] = str(e)

        return result

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "fix_count": self._fix_count,
            "fix_success": self._fix_success,
            "fix_failed": self._fix_failed,
            "verify_count": self._verify_count,
            "history_size": len(self._history),
            "arch_scan_count": self._arch_scan_count,
            "arch_fix_count": self._arch_fix_count,
        }


def create_default_self_think(
    workspace: Path,
    db: DatabaseManager | None = None,
    plugin_queue: PluginTodoQueue | None = None,
    message_queue: Any = None,
    agent_name: str = "AutoGPT",
    coverage_threshold: float = 80.0,
    perf_threshold: float = 1.0,
    boundary_manager: Any | None = None,
) -> SelfThinkEngine:
    """Factory: create a SelfThinkEngine with default sources."""
    engine = SelfThinkEngine(
        workspace=workspace,
        message_queue=message_queue,
        agent_name=agent_name,
        boundary_manager=boundary_manager,
    )
    engine.add_source(CoverageSource(threshold=coverage_threshold))
    engine.add_source(LintSource())
    engine.add_source(PerformanceSource(db=db, threshold=perf_threshold))
    engine.add_source(TodoSource(plugin_queue=plugin_queue))
    return engine
