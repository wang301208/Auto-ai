"""Commands to execute code"""

COMMAND_CATEGORY = "execute_code"
COMMAND_CATEGORY_TITLE = "Execute Code"

import os
import re
import subprocess
from pathlib import Path

from autogpt.agents.agent import Agent
from autogpt.command_decorator import command
from autogpt.config import Config
from autogpt.logs import logger

from .decorators import sanitize_path_arg

ALLOWLIST_CONTROL = "allowlist"
DENYLIST_CONTROL = "denylist"

SHELL_META_CHARS = re.compile(r"[;|&`$\(\)\{\}<>!\n\r]")


@command(
    "execute_python_code",
    "Creates a Python file and executes it",
    {
        "code": {
            "type": "string",
            "description": "The Python code to run",
            "required": True,
        },
        "name": {
            "type": "string",
            "description": "A name to be given to the python file",
            "required": True,
        },
    },
)
def execute_python_code(code: str, name: str, agent: Agent) -> str:
    """Create and execute a Python file and return the STDOUT of the executed code.
    If there is any data that needs to be captured use a print statement

    Args:
        code (str): The Python code to run
        name (str): A name to be given to the Python file

    Returns:
        str: The STDOUT captured from the code when it ran
    """
    ai_name = agent.ai_config.ai_name
    code_dir = agent.workspace.get_path(Path(ai_name, "executed_code"))
    os.makedirs(code_dir, exist_ok=True)

    if not name.endswith(".py"):
        name = name + ".py"

    # The `name` arg is not covered by @sanitize_path_arg,
    # so sanitization must be done here to prevent path traversal.
    file_path = agent.workspace.get_path(code_dir / name)
    if not file_path.is_relative_to(code_dir):
        return "Error: 'name' argument resulted in path traversal, operation aborted"

    try:
        with open(file_path, "w+", encoding="utf-8") as f:
            f.write(code)

        return execute_python_file(str(file_path), agent)
    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "execute_python_file",
    "Executes an existing Python file",
    {
        "filename": {
            "type": "string",
            "description": "The name of te file to execute",
            "required": True,
        },
    },
)
@sanitize_path_arg("filename")
def execute_python_file(filename: str, agent: Agent) -> str:
    """Execute a Python file and return the output

    Args:
        filename (str): The name of the file to execute

    Returns:
        str: The output of the file
    """
    logger.info(
        f"Executing python file '{filename}' in working directory '{agent.config.workspace_path}'"
    )

    if not filename.endswith(".py"):
        return "Error: Invalid file type. Only .py files are allowed."

    file_path = Path(filename)
    if not file_path.is_file():
        # Mimic the response that you get from the command line so that it's easier to identify
        return (
            f"python: can't open file '{filename}': [Errno 2] No such file or directory"
        )

    try:
        resolved = file_path.resolve()
        if hasattr(agent, "workspace") and not resolved.is_relative_to(
            agent.workspace.root
        ):
            return "Error: File is outside of workspace."
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["python", str(file_path)],
            capture_output=True,
            encoding="utf8",
            cwd=agent.config.workspace_path,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


def validate_command(command: str, config: Config) -> bool:
    """Validate a command to ensure it is allowed

    Args:
        command (str): The command to validate
        config (Config): The config to use to validate the command

    Returns:
        bool: True if the command is allowed, False otherwise
    """
    if not command:
        return False

    if SHELL_META_CHARS.search(command):
        return False

    command_name = command.split()[0]

    if config.shell_command_control == ALLOWLIST_CONTROL:
        return command_name in config.shell_allowlist
    else:
        return command_name not in config.shell_denylist


@command(
    "execute_shell",
    "Executes a Shell Command, non-interactive commands only",
    {
        "command_line": {
            "type": "string",
            "description": "The command line to execute",
            "required": True,
        }
    },
    enabled=lambda config: config.execute_local_commands,
    disabled_reason="You are not allowed to run local shell commands. To execute"
    " shell commands, EXECUTE_LOCAL_COMMANDS must be set to 'True' "
    "in your config file: .env - do not attempt to bypass the restriction.",
)
def execute_shell(command_line: str, agent: Agent) -> str:
    """Execute a shell command and return the output

    Args:
        command_line (str): The command line to execute

    Returns:
        str: The output of the command
    """
    if not validate_command(command_line, agent.config):
        logger.info(f"Command '{command_line}' not allowed")
        return "Error: This Shell Command is not allowed."

    current_dir = Path.cwd()
    # Change dir into workspace if necessary
    if not current_dir.is_relative_to(agent.config.workspace_path):
        os.chdir(agent.config.workspace_path)

    logger.info(
        f"Executing command '{command_line}' in working directory '{os.getcwd()}'"
    )

    result = subprocess.run(command_line, capture_output=True, shell=True)
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # Change back to whatever the prior working dir was

    os.chdir(current_dir)
    return output


@command(
    "execute_shell_popen",
    "Executes a Shell Command, non-interactive commands only",
    {
        "command_line": {
            "type": "string",
            "description": "The command line to execute",
            "required": True,
        }
    },
    lambda config: config.execute_local_commands,
    "You are not allowed to run local shell commands. To execute"
    " shell commands, EXECUTE_LOCAL_COMMANDS must be set to 'True' "
    "in your config. Do not attempt to bypass the restriction.",
)
def execute_shell_popen(command_line, agent: Agent) -> str:
    """Execute a shell command with Popen and returns an english description
    of the event and the process id

    Args:
        command_line (str): The command line to execute

    Returns:
        str: Description of the fact that the process started and its id
    """
    if not validate_command(command_line, agent.config):
        logger.info(f"Command '{command_line}' not allowed")
        return "Error: This Shell Command is not allowed."

    current_dir = os.getcwd()
    # Change dir into workspace if necessary
    if not Path(current_dir).is_relative_to(agent.config.workspace_path):
        os.chdir(agent.config.workspace_path)

    logger.info(
        f"Executing command '{command_line}' in working directory '{os.getcwd()}'"
    )

    do_not_show_output = subprocess.DEVNULL
    process = subprocess.Popen(
        command_line, shell=True, stdout=do_not_show_output, stderr=do_not_show_output
    )

    # Change back to whatever the prior working dir was

    os.chdir(current_dir)

    return f"Subprocess started with PID:'{str(process.pid)}'"
