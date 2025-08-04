"""Commands to run tests"""

COMMAND_CATEGORY = "testing"
COMMAND_CATEGORY_TITLE = "Testing"

import subprocess

from autogpt.agents.agent import Agent
from autogpt.command_decorator import command

from .decorators import sanitize_path_arg


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
