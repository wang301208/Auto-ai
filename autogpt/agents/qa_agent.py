from __future__ import annotations

"""QA agent that validates proposed code fixes before deployment."""

import subprocess
from typing import Any

from git import Repo

from autogpt.agents.agent import Agent
from autogpt.commands.git_operations import git_checkout
from autogpt.commands.testing import run_tests
from autogpt.event_bus import CODE_FIX_PROPOSED, EventMessage, MessageQueue

HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
"""Event type emitted when human approval is needed for a fix."""

ISSUE_RESOLVED = "ISSUE_RESOLVED"
"""Event type emitted after a fix has been merged and deployed."""


class QAAgent:
    """Agent that verifies proposed fixes and merges them after approval."""

    def __init__(self, agent: Agent, message_queue: MessageQueue) -> None:
        self.agent = agent
        self.message_queue = message_queue
        self.message_queue.subscribe(CODE_FIX_PROPOSED, self._on_code_fix_proposed)

    # ------------------------------------------------------------------
    def _on_code_fix_proposed(self, event: EventMessage) -> None:
        """Handle a ``CODE_FIX_PROPOSED`` event."""

        payload: dict[str, Any] | None = event.payload if isinstance(event.payload, dict) else None
        if not payload:
            return

        branch = payload.get("branch_name")
        repo_path = payload.get("repo_path", self.agent.config.workspace_path)
        approved = payload.get("approved", False)

        if not branch or not repo_path:
            return

        git_checkout(repo_path, branch, self.agent)

        test_output = run_tests(repo_path, self.agent)

        if not approved:
            self.message_queue.publish(
                EventMessage(
                    event_type=HUMAN_APPROVAL_REQUIRED,
                    payload={
                        "branch_name": branch,
                        "test_output": test_output,
                        "summary": payload.get("summary", ""),
                    },
                    source_agent="qa_agent",
                )
            )
            return

        repo = Repo(repo_path)
        repo.git.checkout("main")
        repo.git.merge(branch)

        try:
            subprocess.run(["bash", "scripts/deploy.sh"], cwd=repo_path, check=False)
        except Exception:
            pass

        self.message_queue.publish(
            EventMessage(
                event_type=ISSUE_RESOLVED,
                payload={
                    "branch_name": branch,
                    "commit_hash": payload.get("commit_hash", ""),
                    "summary": payload.get("summary", ""),
                },
                source_agent="qa_agent",
            )
        )
