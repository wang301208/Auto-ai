"""Commands to run tests"""

COMMAND_CATEGORY = "testing"
COMMAND_CATEGORY_TITLE = "Testing"

import io
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict

import pytest

from autogpt.agents.agent import Agent
from autogpt.command_decorator import command

from .decorators import sanitize_path_arg
from .file_operations import write_to_file


@command(
    "run_tests",
    "Run tests located at a given path using pytest",
    {
        "path": {
            "type": "string",
            "description": "Path to the tests to run",
            "required": True,
        }
    },
)
@sanitize_path_arg("path")
def run_tests(path: str, agent: Agent) -> Dict[str, Any]:
    """Run tests using pytest and return structured results.

    Args:
        path: Path to the tests to run.
        agent: The Agent running the command.

    Returns:
        Dict with keys ``successes``, ``failures``, ``errors`` and ``logs``.
    """

    class ResultAggregator:
        """Pytest plugin to aggregate test results."""

        def __init__(self) -> None:
            self.passed = 0
            self.failed = 0
            self.errors = 0

        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:  # type: ignore[override]
            if report.when == "call":
                if report.passed:
                    self.passed += 1
                elif report.failed:
                    self.failed += 1
            elif report.failed:
                self.errors += 1

    aggregator = ResultAggregator()
    output_buffer = io.StringIO()

    try:
        prev_cwd = os.getcwd()
        os.chdir(agent.config.workspace_path)
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            pytest.main([path], plugins=[aggregator])
    except Exception as e:  # pragma: no cover - defensive programming
        return {
            "successes": 0,
            "failures": 0,
            "errors": 1,
            "logs": f"Error: {e}",
        }
    finally:
        os.chdir(prev_cwd)

    return {
        "successes": aggregator.passed,
        "failures": aggregator.failed,
        "errors": aggregator.errors,
        "logs": output_buffer.getvalue(),
    }


@command(
    "create_test_file",
    "Create a new test file",
    {
        "file_path": {
            "type": "string",
            "description": "Path where the test file should be created",
            "required": True,
        },
        "content": {
            "type": "string",
            "description": "Content of the test file",
            "required": True,
        },
    },
)
@sanitize_path_arg("file_path")
def create_test_file(file_path: str, content: str, agent: Agent) -> str:
    """Create a new test file inside the tests/ directory.

    Args:
        file_path: Destination path for the new test file.
        content: Content to write into the test file.
        agent: The Agent running the command.

    Returns:
        A message indicating success or failure.
    """
    path = Path(file_path)

    try:
        relative = path.relative_to(agent.workspace.root)
    except ValueError:
        return "Error: file_path is outside of the workspace."

    if not relative.parts or relative.parts[0] != "tests":
        return "Error: Test files must be created inside the tests/ directory."
    if not path.name.startswith("test_"):
        return "Error: Test file name must start with 'test_'."

    return write_to_file(file_path, content, agent)
