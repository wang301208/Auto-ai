"""Background manager to automatically develop the codebase."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread
from typing import List

from autogpt.event_bus import EventMessage, MessageQueue

from .database import DatabaseManager
from .patcher import PatchAgent
from .plugin_processor import _files_from_diff, generate_diff
from .plugin_todo_queue import PluginTodoQueue
from .yaml_exporter import export_prompt_config


@dataclass
class Issue:
    """Representation of an improvement opportunity."""

    description: str
    context: str


class SelfDevelopManager:
    """Periodically review repository state and apply fixes."""

    def __init__(
        self,
        *,
        plugin_queue: PluginTodoQueue,
        patch_agent: PatchAgent,
        db: DatabaseManager,
        message_queue: MessageQueue | None,
        workspace: Path,
        interval: float = 300.0,
        coverage_threshold: float = 80.0,
        performance_threshold: float = 1.0,
        enabled: bool = True,
    ) -> None:
        self.plugin_queue = plugin_queue
        self.patch_agent = patch_agent
        self.db = db
        self.message_queue = message_queue
        self.workspace = workspace
        self.interval = interval
        self.coverage_threshold = coverage_threshold
        self.performance_threshold = performance_threshold
        self.enabled = enabled
        self._stop_event: Event | None = None
        self._thread: Thread | None = None
        self._events_processed = 0

    # --- Thread control -------------------------------------------------
    def start(self) -> tuple[Thread, Event]:
        """Start the self development loop."""

        stop_event = Event()

        def worker() -> None:
            while not stop_event.is_set():
                if self.enabled:
                    self.review_repository()
                stop_event.wait(self.interval)

        thread = Thread(target=worker, daemon=True)
        thread.start()
        self._stop_event = stop_event
        self._thread = thread
        return thread, stop_event

    def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join()

    # --- Core logic -----------------------------------------------------
    def review_repository(self) -> None:
        """Collect issues and attempt to resolve them."""

        for issue in self._collect_issues():
            self._handle_issue(issue)

    # --- Helpers --------------------------------------------------------
    def _collect_issues(self) -> List[Issue]:
        issues: List[Issue] = []

        # Plugin TODOs
        while True:
            todo = self.plugin_queue.pop()
            if todo is None:
                break
            issues.append(Issue(f"Plugin TODO {todo.gap}", todo.context))

        # Event log failures
        if self.message_queue:
            events = list(self.message_queue.get_events())
            new_events = events[self._events_processed :]
            self._events_processed = len(events)
            for event in new_events:
                if event.event_type in {"error", "lint_failure", "test_failure"}:
                    issues.append(
                        Issue(
                            f"Event {event.event_type}",
                            json.dumps(event.payload),
                        )
                    )

        # Coverage report
        coverage_file = self.workspace / "coverage.json"
        if coverage_file.exists():
            try:
                data = json.loads(coverage_file.read_text())
                files = data.get("files", {})
                for path, info in files.items():
                    summary = info.get("summary", {})
                    if summary.get("percent_covered", 100.0) < self.coverage_threshold:
                        issues.append(
                            Issue(
                                f"Low coverage {path}",
                                f"Improve test coverage for {path}",
                            )
                        )
            except Exception:
                pass

        # Performance hotspots
        for func, total in self.db.get_hotspots(self.performance_threshold):
            issues.append(
                Issue(
                    f"Hotspot {func}",
                    f"Optimise performance of {func} taking {total:.2f}s",
                )
            )

        # Linter / test failures
        checks = (
            ["black", "--check", str(self.workspace)],
            ["ruff", "check", str(self.workspace)],
            ["mypy", str(self.workspace)],
            ["pytest", "-q"],
        )
        for cmd in checks:
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                issues.append(
                    Issue(
                        " ".join(cmd),
                        process.stdout + process.stderr,
                    )
                )

        return issues

    def _handle_issue(self, issue: Issue) -> None:
        """Generate a patch for ``issue`` and apply it."""

        try:
            diff = generate_diff(issue.context)
            self.patch_agent.apply_diff(diff, cwd=self.workspace)
            files = _files_from_diff(diff, self.workspace)
            self.patch_agent.verify(files)
            export_prompt_config(self.workspace)
            self.db.log_execution(f"Self develop {issue.description}", "success")
            if self.message_queue:
                self.message_queue.publish(
                    EventMessage(
                        event_type="self_develop",
                        payload={"issue": issue.description, "result": "success"},
                        source_agent="self_develop",
                    )
                )
        except Exception as err:  # pragma: no cover - error path
            self.db.log_execution(
                f"Self develop {issue.description}",
                f"failure: {err}",
            )
            if self.message_queue:
                self.message_queue.publish(
                    EventMessage(
                        event_type="self_develop",
                        payload={
                            "issue": issue.description,
                            "result": f"failure: {err}",
                        },
                        source_agent="self_develop",
                    )
                )
