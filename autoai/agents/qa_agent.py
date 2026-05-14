from __future__ import annotations

"""QA agent that validates proposed code fixes before deployment."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from git import Repo

import logging

from autoai.agents.agent import Agent
from autoai.commands.git_operations import git_checkout, git_clone
from autoai.commands.testing import run_tests
from autoai.event_bus import (
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
from autoai.skills.librarian import LibrarianAgent


logger = logging.getLogger(__name__)

class QAAgent:
    """验证提议修复并在批准后合并的代理。"""

    def __init__(
        self,
        agent: Agent,
        message_queue: MessageQueue,
        librarian: LibrarianAgent | None = None,
    ) -> None:
        self.agent = agent
        self.message_queue = message_queue
        self.librarian = librarian or getattr(agent, "librarian", None)
        self.message_queue.subscribe(CODE_FIX_PROPOSED, self._on_code_fix_proposed)
        self.message_queue.subscribe(APPROVAL_GRANTED, self._on_approval_granted)

    # ------------------------------------------------------------------
    def _on_code_fix_proposed(self, event: CodeFixProposed) -> None:
        """处理``CODE_FIX_PROPOSED``事件。"""

        payload: dict[str, Any] | None = (
            event.payload if isinstance(event.payload, dict) else None
        )
        repo_path = (payload or {}).get("repo_path", self.agent.config.workspace_path)
        approved_by = (payload or {}).get("approved_by")
        approval_timestamp = (payload or {}).get("approval_timestamp")

        branch = event.branch_name
        if not branch or not repo_path:
            return

        repo = Repo(repo_path)
        repo_url = repo.remotes.origin.url

        with tempfile.TemporaryDirectory() as tmp_repo_path:
            git_clone(repo_url, tmp_repo_path, self.agent)
            git_checkout(tmp_repo_path, branch, self.agent)
            try:
                test_result = run_tests(tmp_repo_path, self.agent)
            except Exception:
                logger.exception("Failed to run tests for branch %s", branch)
                return

        if (
            test_result.get("status") == "passed"
            and test_result.get("failures", 0) == 0
            and test_result.get("errors", 0) == 0
        ):
            diff = repo.git.diff("main", branch)
            self.message_queue.publish(
                HumanApprovalRequired(
                    branch_name=branch,
                    test_output=test_result["logs"],
                    summary=event.summary,
                    diff=diff,
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
        """处理``APPROVAL_GRANTED``事件。"""

        payload: dict[str, Any] | None = (
            event.payload if isinstance(event.payload, dict) else None
        )
        repo_path = (payload or {}).get("repo_path", self.agent.config.workspace_path)
        approved_by = (payload or {}).get("approved_by")
        approval_timestamp = (payload or {}).get("approval_timestamp")

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

        if self.librarian:
            try:
                diff_output = repo.git.diff(
                    "main~1",
                    "main",
                    "--name-status",
                    "--",
                    "skill_library/*/skill.json",
                )
            except Exception:
                diff_output = ""

            for line in diff_output.splitlines():
                try:
                    status, path = line.split("\t", 1)
                except ValueError:
                    continue
                if status != "A":
                    continue
                skill_json_path = Path(repo_path) / path
                try:
                    metadata = json.loads(skill_json_path.read_text(encoding="utf-8"))
                except Exception:
                    logger.exception(
                        "Failed to load skill metadata from %s", skill_json_path
                    )
                    continue
                metadata["approved_by"] = approved_by
                metadata["approval_timestamp"] = approval_timestamp
                skill_dir_path = (
                    skill_json_path.parent / metadata.get("entry_point", "main.py")
                )
                try:
                    self.librarian.add_skill(metadata, str(skill_dir_path))
                except Exception:
                    logger.exception(
                        "Failed to add new skill from %s", skill_json_path
                    )

        self.message_queue.publish(
            IssueResolved(
                branch_name=branch,
                commit_hash=event.commit_hash,
                summary=event.summary,
                source_agent="qa_agent",
            )
        )
