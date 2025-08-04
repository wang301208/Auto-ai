from __future__ import annotations

"""Event-driven TDD developer agent that responds to diagnostics."""

from pathlib import Path
from typing import Any

from autogpt.agents.agent import Agent
from autogpt.commands.git_operations import (
    git_checkout,
    git_commit,
    git_create_branch,
)
from autogpt.commands.testing import create_test_file, run_tests
from autogpt.event_bus import DIAGNOSIS_COMPLETE, EventMessage, MessageQueue

CODE_FIX_PROPOSED = "CODE_FIX_PROPOSED"
"""Event type emitted when a code fix has been proposed."""


class TDDDeveloper:
    """Agent that creates failing tests and proposes fixes based on diagnostics."""

    def __init__(self, agent: Agent, message_queue: MessageQueue) -> None:
        self.agent = agent
        self.message_queue = message_queue
        self.message_queue.subscribe(DIAGNOSIS_COMPLETE, self._on_diagnosis_complete)

    # ------------------------------------------------------------------
    def _on_diagnosis_complete(self, event: EventMessage) -> None:
        """Handle a ``DIAGNOSIS_COMPLETE`` event."""

        payload = event.payload or {}
        if not isinstance(payload, dict):
            return

        issue_id = payload.get("issue_id")
        repo_path = payload.get("repo_path")
        diagnostics: Any = payload.get("diagnostics") or payload.get("details")

        if not issue_id or not repo_path:
            return

        branch = f"fix/{issue_id}"
        git_create_branch(repo_path, branch, self.agent)
        git_checkout(repo_path, branch, self.agent)

        test_file = Path(repo_path) / "tests" / f"test_issue_{issue_id}.py"
        test_content = (
            f"# Auto-generated regression test for issue {issue_id}\n"
            f"{diagnostics or ''}\n"
        )
        create_test_file(str(test_file), test_content, self.agent)

        initial_result = run_tests(str(test_file), self.agent)
        if "failed" not in initial_result.lower():
            return

        final_result = run_tests(repo_path, self.agent)
        if "failed" in final_result.lower():
            return

        git_commit(repo_path, f"Fix issue {issue_id}", self.agent)

        self.message_queue.publish(
            EventMessage(
                event_type=CODE_FIX_PROPOSED,
                payload={
                    "issue_id": issue_id,
                    "repo_path": repo_path,
                    "test_file": str(test_file),
                    "diagnostics": diagnostics,
                },
                source_agent="tdd_developer",
            )
        )
