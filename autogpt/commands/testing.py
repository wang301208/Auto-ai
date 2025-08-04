"""Commands to run tests"""

COMMAND_CATEGORY = "testing"
COMMAND_CATEGORY_TITLE = "Testing"

import subprocess
from pathlib import Path

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
def run_tests(path: str, agent: Agent) -> str:
    """Run tests using pytest and return the combined output.

    Args:
        path: Path to the tests to run.
        agent: The Agent running the command.

    Returns:
        stdout and stderr from running pytest, or an error message.
    """
    try:
        result = subprocess.run(
            ["pytest", path],
            capture_output=True,
            text=True,
            cwd=agent.config.workspace_path,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


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
