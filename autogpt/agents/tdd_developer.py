"""Event-driven TDD developer agent that responds to diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import json
import logging

from git import Repo  # type: ignore[import-not-found]

from autogpt.agents.agent import Agent
from autogpt.commands.file_operations import write_to_file
from autogpt.commands.git_operations import git_checkout, git_commit, git_create_branch
from autogpt.commands.testing import create_test_file, run_tests
from autogpt.commands.code_reader import read_and_understand_code
from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    CodeFixProposed,
    EventMessage,
    MessageQueue,
)
from autogpt.skills.librarian import LibrarianAgent


logger = logging.getLogger(__name__)

class TDDDeveloper:
    """Agent that creates failing tests and proposes fixes based on diagnostics.

    Args:
        agent: The ``Agent`` used for executing commands.
        message_queue: Queue for communication with other agents.
        librarian: Optional ``LibrarianAgent`` for registering new skills.
    """

    def __init__(
        self,
        agent: Agent,
        message_queue: MessageQueue,
        librarian: LibrarianAgent | None = None,
    ) -> None:
        self.agent = agent
        self.message_queue = message_queue
        self.librarian = librarian
        self.learned_sources: dict[str, str] = {}
        self.message_queue.subscribe(DIAGNOSIS_COMPLETE, self._on_diagnosis_complete)

    # ------------------------------------------------------------------
    def _use_recommended_skill(
        self,
        repo_path: str,
        branch: str,
        issue_id: str,
        skill: dict[str, Any],
    ) -> None:
        """Create a helper script that invokes a recommended skill.

        A small wrapper is written to ``scripts/use_<skill>.py`` which loads the
        skill's ``run`` function and executes it with the provided parameters.
        A corresponding test ensures the script calls the skill. If the test
        passes, the change is committed and a :class:`CodeFixProposed` event is
        emitted.
        """

        name = skill.get("name")
        version = skill.get("version", "")
        params = skill.get("parameters", {}) or {}

        script_path = Path(repo_path) / "scripts" / f"use_{name}.py"
        arg_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
        call_line = f"module.run({arg_str})" if arg_str else "module.run()"
        script_content = (
            "from __future__ import annotations\n\n"
            "import importlib.util\n"
            "from importlib.machinery import ModuleSpec\n"
            "from pathlib import Path\n"
            "from types import ModuleType\n\n"
            "def _load_skill() -> ModuleType:\n"
            f"    spec: ModuleSpec | None = importlib.util.spec_from_file_location(\n"
            f"        'skill', Path(__file__).resolve().parent.parent / 'skill_library' / '{name}_{version}' / 'main.py'\n"
            "    )\n"
            "    assert spec is not None and spec.loader is not None\n"
            "    module = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(module)\n"
            "    return module\n\n"
            "def main() -> None:\n"
            "    module = _load_skill()\n"
            f"    {call_line}\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        test_path = Path(repo_path) / "tests" / f"test_use_{name}.py"
        assert_line = (
            f"    mock_run.assert_called_once_with({arg_str})\n"
            if arg_str
            else "    mock_run.assert_called_once_with()\n"
        )
        test_content = (
            "from __future__ import annotations\n\n"
            "from importlib.machinery import ModuleSpec\n"
            "from types import ModuleType\n"
            "from unittest.mock import MagicMock, patch\n\n"
            f"import scripts.use_{name} as script\n\n"
            "def test_main_calls_run() -> None:\n"
            "    mock_run = MagicMock()\n"
            "    module = ModuleType('skill')\n"
            "    spec = ModuleSpec('skill', loader=MagicMock())\n"
            "    spec.loader.exec_module.side_effect = lambda mod: setattr(mod, 'run', mock_run)\n"
            "    with patch('importlib.util.spec_from_file_location', return_value=spec), patch(\n"
            "        'importlib.util.module_from_spec', return_value=module\n"
            "    ):\n"
            "        script.main()\n"
            f"{assert_line}"
        )
        try:
            write_to_file(str(script_path), script_content, self.agent)
            create_test_file(str(test_path), test_content, self.agent)
        except Exception:
            logger.exception(
                "Failed to generate script or test for skill %s", name
            )
            return
        try:
            result = run_tests(str(test_path), self.agent)
        except Exception:
            logger.exception("Failed to run tests for skill %s", name)
            return
        if result.get("exit_code", 1) != 0:
            return

        git_commit(repo_path, f"Use recommended skill {name}", self.agent)
        try:
            commit_hash = Repo(repo_path).head.commit.hexsha
        except Exception:
            commit_hash = ""

        self.message_queue.publish(
            CodeFixProposed(
                branch_name=branch,
                commit_hash=commit_hash,
                summary=f"Use recommended skill {name}",
                source_agent="tdd_developer",
            )
        )
        return

    # ------------------------------------------------------------------
    def _on_diagnosis_complete(self, event: EventMessage) -> None:
        """Handle a ``DIAGNOSIS_COMPLETE`` event."""

        payload = event.payload or {}
        if not isinstance(payload, dict):
            return

        repo_path = payload.get("repo_path")
        details = payload.get("details", {})
        diagnostics: Any = payload.get("diagnostics") or details

        if not repo_path:
            return

        # Perform learning phase if source code paths are provided
        source_paths: dict[str, str] = {}
        if isinstance(diagnostics, dict):
            source_paths = diagnostics.get("source_code_paths", {}) or source_paths
        if isinstance(details, dict) and not source_paths:
            source_paths = details.get("source_code_paths", {}) or {}
        for name, lib_path in source_paths.items():
            try:
                report = read_and_understand_code(lib_path, self.agent)
                self.learned_sources[name] = report
            except Exception:
                logger.exception("Failed to learn from source path %s", lib_path)

        new_skill = details.get("new_skill") if isinstance(details, dict) else None
        if new_skill:
            name = new_skill.get("skill_name") or new_skill.get("name")
            version = new_skill.get("version", "1.0")
            branch = f"new-skill/{name}_{version}"
            git_create_branch(repo_path, branch, self.agent)
            git_checkout(repo_path, branch, self.agent)

            skill_dir = Path(repo_path) / "skill_library" / f"{name}_{version}"
            code = new_skill.get("code", "")
            metadata = {
                "skill_name": name,
                "version": version,
                "description": new_skill.get("description", ""),
                "tags": new_skill.get("tags", []),
                "parameters": new_skill.get("parameters", {}),
            }
            for key in [
                "dependencies_file",
                "entry_point",
                "return_type",
                "author_agent",
                "creation_timestamp",
            ]:
                if new_skill.get(key) is not None:
                    metadata[key] = new_skill[key]
            try:
                write_to_file(str(skill_dir / "main.py"), code, self.agent)
                write_to_file(
                    str(skill_dir / "skill.json"),
                    json.dumps(metadata, indent=2),
                    self.agent,
                )
            except Exception:
                logger.exception("Failed to generate files for new skill %s", name)
                return
            if self.librarian:
                try:
                    added = self.librarian.add_skill(
                        metadata, str(skill_dir / "main.py")
                    )
                    if not added:
                        logger.error("Librarian rejected new skill %s", name)
                        return
                except Exception:
                    logger.exception(
                        "Failed to add new skill %s to librarian", name
                    )
                    return
            git_commit(repo_path, f"Add new skill {name}", self.agent)
            try:
                commit_hash = Repo(repo_path).head.commit.hexsha
            except Exception:
                commit_hash = ""
            self.message_queue.publish(
                CodeFixProposed(
                    branch_name=branch,
                    commit_hash=commit_hash,
                    summary=f"Add new skill {name}",
                    source_agent="tdd_developer",
                )
            )
            return

        issue_id = payload.get("issue_id")
        if not issue_id:
            return

        branch = f"fix/{issue_id}"
        git_create_branch(repo_path, branch, self.agent)
        git_checkout(repo_path, branch, self.agent)

        recommended_skill = (
            details.get("recommended_skill") if isinstance(details, dict) else None
        )
        if recommended_skill:
            self._use_recommended_skill(repo_path, branch, issue_id, recommended_skill)
            return

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
        try:
            create_test_file(str(test_file), test_content, self.agent)
        except Exception:
            logger.exception("Failed to create test for issue %s", issue_id)
            return

        try:
            initial_result = run_tests(str(test_file), self.agent)
        except Exception:
            logger.exception("Failed to run initial tests for issue %s", issue_id)
            return
        if initial_result.get("exit_code", 1) == 0:
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

            try:
                result = run_tests(repo_path, self.agent)
            except Exception:
                logger.exception("Failed to run tests for issue %s", issue_id)
                return
            if result.get("exit_code", 1) == 0:
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
