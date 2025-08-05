"""Event-driven TDD developer agent that responds to diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from git import Repo  # type: ignore[import-not-found]

from autogpt.agents.agent import Agent
from autogpt.commands.file_operations import write_to_file
from autogpt.commands.git_operations import git_checkout, git_commit, git_create_branch
from autogpt.commands.testing import create_test_file, run_tests
from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    CodeFixProposed,
    EventMessage,
    MessageQueue,
)


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

        # Attempt to parse stack traces like: File "<path>", line X, in <func>
        diag_text = diagnostics if isinstance(diagnostics, str) else ""
        file_match = re.search(r'File "([^"]+)", line \d+, in (\w+)', diag_text)
        err_match = re.search(r'^(\w+(?:Error|Exception))', diag_text.splitlines()[-1]) if diag_text else None

        test_body = diag_text
        if file_match and err_match:
            file_path, func_name = file_match.groups()
            error_type = err_match.group(1)
            try:
                rel_path = Path(file_path).relative_to(repo_path)
                module = rel_path.with_suffix("").as_posix().replace("/", ".")
                test_body = (
                    f"import pytest\nfrom {module} import {func_name}\n\n"
                    f"def test_issue_{issue_id}():\n"
                    f"    with pytest.raises({error_type}):\n"
                    f"        {func_name}()\n"
                )
            except ValueError:
                # If path is outside repo, fall back to including diagnostics text
                test_body = diag_text

        test_content = (
            f"# Auto-generated regression test for issue {issue_id}\n" f"{test_body}\n"
        )
        create_test_file(str(test_file), test_content, self.agent)

        initial_result = run_tests(str(test_file), self.agent)
        if (
            initial_result.get("failures", 0) == 0
            and initial_result.get("errors", 0) == 0
        ):
            return

        fixes: list[dict[str, str]] = []
        if isinstance(diagnostics, dict):
            fixes = diagnostics.get("fixes", []) or []

        max_iterations = payload.get("max_iterations", len(fixes) or 1)

        for i in range(max_iterations):
            if i < len(fixes):
                for rel_path, new_content in fixes[i].items():
                    file_path = Path(repo_path) / rel_path
                    write_to_file(str(file_path), new_content, self.agent)

            result = run_tests(repo_path, self.agent)
            if result.get("failures", 0) == 0 and result.get("errors", 0) == 0:
                git_commit(repo_path, f"Fix issue {issue_id}", self.agent)
                try:
                    commit_hash = Repo(repo_path).head.commit.hexsha
                except Exception:
                    commit_hash = ""

                self.message_queue.publish(
                    CodeFixProposed(
                        branch_name=branch,
                        commit_hash=commit_hash,
                        summary=f"Fix issue {issue_id}",
                        source_agent="tdd_developer",
                    )
                )
                return

        # If we exit the loop without passing tests, no commit or event is produced
        return
