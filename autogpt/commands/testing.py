"""Commands to run tests"""

COMMAND_CATEGORY = "testing"
COMMAND_CATEGORY_TITLE = "Testing"

import io
import json
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

    The function relies on ``pytest-json-report`` to obtain a machine readable
    summary of the test run. If the plugin is unavailable, the exit code of
    ``pytest`` is used to infer the outcome.

    Args:
        path: Path to the tests to run.
        agent: The Agent running the command.

    Returns:
        Dictionary with keys ``status``, ``exit_code``, ``successes``,
        ``failures``, ``errors`` and ``logs``.
    """

    output_buffer = io.StringIO()
    report_file = Path(agent.config.workspace_path) / ".pytest_report.json"

    try:
        prev_cwd = os.getcwd()
        os.chdir(agent.config.workspace_path)
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            exit_code = pytest.main(
                [path, "--json-report", f"--json-report-file={report_file}"]
            )

        summary: Dict[str, int] = {}
        if report_file.is_file():
            try:
                with report_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                summary = data.get("summary", {})
            except Exception:  # pragma: no cover - best effort
                summary = {}
    except Exception as e:  # pragma: no cover - defensive programming
        return {
            "status": "error",
            "exit_code": 1,
            "successes": 0,
            "failures": 0,
            "errors": 1,
            "logs": f"Error: {e}",
        }
    finally:
        os.chdir(prev_cwd)
        try:
            report_file.unlink()
        except FileNotFoundError:
            pass

    successes = int(summary.get("passed", 0))
    failures = int(summary.get("failed", 0))
    errors = int(summary.get("errors", summary.get("error", 0)))
    if exit_code == 2 and failures == 0 and errors == 0:
        errors = 1

    status = "passed" if exit_code == 0 else "failed"

    return {
        "status": status,
        "exit_code": exit_code,
        "successes": successes,
        "failures": failures,
        "errors": errors,
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
