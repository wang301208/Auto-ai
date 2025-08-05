from __future__ import annotations

"""QA agent that validates proposed code fixes before deployment."""

import subprocess
import tempfile
from typing import Any

from git import Repo

from autogpt.agents.agent import Agent
from autogpt.commands.git_operations import git_checkout, git_clone
from autogpt.commands.testing import run_tests
from autogpt.event_bus import (
    APPROVAL_GRANTED,
    CODE_FIX_PROPOSED,
    ApprovalGranted,
    CodeFixProposed,
    DeploymentFailed,
    HumanApprovalRequired,
    IssueResolved,
    MessageQueue,
    TestsFailed,
)


class QAAgent:
    """Agent that verifies proposed fixes and merges them after approval."""

    def __init__(self, agent: Agent, message_queue: MessageQueue) -> None:
        self.agent = agent
        self.message_queue = message_queue
        self.message_queue.subscribe(CODE_FIX_PROPOSED, self._on_code_fix_proposed)
        self.message_queue.subscribe(APPROVAL_GRANTED, self._on_approval_granted)

    # ------------------------------------------------------------------
    def _on_code_fix_proposed(self, event: CodeFixProposed) -> None:
        """Handle a ``CODE_FIX_PROPOSED`` event."""

        payload: dict[str, Any] | None = (
            event.payload if isinstance(event.payload, dict) else None
        )
        repo_path = (payload or {}).get("repo_path", self.agent.config.workspace_path)

        branch = event.branch_name
        if not branch or not repo_path:
            return

        repo_url = Repo(repo_path).remotes.origin.url

        with tempfile.TemporaryDirectory() as tmp_repo_path:
            git_clone(repo_url, tmp_repo_path, self.agent)
            git_checkout(tmp_repo_path, branch, self.agent)
            test_result = run_tests(tmp_repo_path, self.agent)

        if (
            test_result.get("status") == "passed"
            and test_result.get("failures", 0) == 0
            and test_result.get("errors", 0) == 0
        ):
            self.message_queue.publish(
                HumanApprovalRequired(
                    branch_name=branch,
                    test_output=test_result["logs"],
                    summary=event.summary,
                    source_agent="qa_agent",
                )
            )
        else:
            self.message_queue.publish(
                TestsFailed(
                    branch_name=branch,
                    test_output=test_result.get("logs", ""),
                    summary=event.summary,
                    source_agent="qa_agent",
                )
            )

    def _on_approval_granted(self, event: ApprovalGranted) -> None:
        """Handle an ``APPROVAL_GRANTED`` event."""

        payload: dict[str, Any] | None = (
            event.payload if isinstance(event.payload, dict) else None
        )
        repo_path = (payload or {}).get("repo_path", self.agent.config.workspace_path)

        branch = event.branch_name
        if not branch or not repo_path:
            return

        repo = Repo(repo_path)
        repo.git.checkout("main")
        repo.git.merge(branch)

        try:
            result = subprocess.run(
                ["bash", "scripts/deploy.sh"], cwd=repo_path, check=False
            )
        except Exception:
            result = subprocess.CompletedProcess([], returncode=1)  # type: ignore[arg-type]

        if result.returncode != 0:
            self.message_queue.publish(
                DeploymentFailed(
                    branch_name=branch,
                    commit_hash=event.commit_hash,
                    summary=event.summary,
                    return_code=result.returncode,
                    source_agent="qa_agent",
                )
            )
            return

        self.message_queue.publish(
            IssueResolved(
                branch_name=branch,
                commit_hash=event.commit_hash,
                summary=event.summary,
                source_agent="qa_agent",
            )
        )
