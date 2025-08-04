"""Commands to perform Git operations"""

COMMAND_CATEGORY = "git_operations"
COMMAND_CATEGORY_TITLE = "Git Operations"

import os

from git import Repo
from git.exc import GitCommandError

from autogpt.agents.agent import Agent
from autogpt.command_decorator import command
from autogpt.url_utils.validators import validate_url

from .decorators import sanitize_path_arg


@command(
    "clone_repository",
    "Clones a Repository",
    {
        "url": {
            "type": "string",
            "description": "The URL of the repository to clone",
            "required": True,
        },
        "clone_path": {
            "type": "string",
            "description": "The path to clone the repository to",
            "required": True,
        },
    },
    lambda config: bool(config.github_username and config.github_api_key),
    "Configure github_username and github_api_key.",
)
@sanitize_path_arg("clone_path")
@validate_url
def clone_repository(url: str, clone_path: str, agent: Agent) -> str:
    """Clone a GitHub repository locally.

    Args:
        url (str): The URL of the repository to clone.
        clone_path (str): The path to clone the repository to.

    Returns:
        str: The result of the clone operation.
    """
    split_url = url.split("//")
    auth_repo_url = (
        f"//{agent.config.github_username}:{agent.config.github_api_key}@".join(
            split_url
        )
    )
    try:
        Repo.clone_from(url=auth_repo_url, to_path=clone_path)
        return f"""Cloned {url} to {clone_path}"""
    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "git_commit",
    "Commit changes to a repository",
    {
        "repo_path": {
            "type": "string",
            "description": "Path to the repository",
            "required": True,
        },
        "message": {
            "type": "string",
            "description": "Commit message",
            "required": True,
        },
    },
    lambda config: bool(config.github_username and config.github_api_key),
    "Configure github_username and github_api_key.",
)
@sanitize_path_arg("repo_path")
def git_commit(repo_path: str, message: str, agent: Agent) -> str:
    """Commit changes in a git repository."""
    try:
        repo = Repo(repo_path)
        if not repo.is_dirty(untracked_files=True):
            return "No changes to commit."
        repo.git.add(A=True)
        repo.index.commit(message)
        return f"Committed changes to {repo_path}"
    except GitCommandError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "git_push",
    "Push changes to remote",
    {
        "repo_path": {
            "type": "string",
            "description": "Path to the repository",
            "required": True,
        },
        "branch_name": {
            "type": "string",
            "description": "Name of the branch to push",
            "required": True,
        },
    },
    lambda config: bool(config.github_username and config.github_api_key),
    "Configure github_username and github_api_key.",
)
@sanitize_path_arg("repo_path")
def git_push(repo_path: str, branch_name: str, agent: Agent) -> str:
    """Push a branch to the remote repository."""
    try:
        repo = Repo(repo_path)
        origin = repo.remote(name="origin")
        url = origin.url
        if "@" not in url:
            split_url = url.split("//")
            auth_url = (
                f"//{agent.config.github_username}:{agent.config.github_api_key}@".join(
                    split_url
                )
            )
            origin.set_url(auth_url)
        origin.push(branch_name)
        return f"Pushed branch {branch_name} to remote"
    except GitCommandError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "git_create_branch",
    "Create a new branch",
    {
        "repo_path": {
            "type": "string",
            "description": "Path to the repository",
            "required": True,
        },
        "branch_name": {
            "type": "string",
            "description": "Name of the branch to create",
            "required": True,
        },
    },
    lambda config: bool(config.github_username and config.github_api_key),
    "Configure github_username and github_api_key.",
)
@sanitize_path_arg("repo_path")
def git_create_branch(repo_path: str, branch_name: str, agent: Agent) -> str:
    """Create a new branch in the repository."""
    try:
        repo = Repo(repo_path)
        if branch_name in [h.name for h in repo.heads]:
            return f"Branch {branch_name} already exists"
        repo.create_head(branch_name)
        return f"Created branch {branch_name}"
    except GitCommandError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "git_checkout",
    "Checkout a branch",
    {
        "repo_path": {
            "type": "string",
            "description": "Path to the repository",
            "required": True,
        },
        "branch_name": {
            "type": "string",
            "description": "Name of the branch to checkout",
            "required": True,
        },
    },
    lambda config: bool(config.github_username and config.github_api_key),
    "Configure github_username and github_api_key.",
)
@sanitize_path_arg("repo_path")
def git_checkout(repo_path: str, branch_name: str, agent: Agent) -> str:
    """Checkout the specified branch."""
    try:
        repo = Repo(repo_path)
        repo.git.checkout(branch_name)
        return f"Checked out branch {branch_name}"
    except GitCommandError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@command(
    "git_blame",
    "Get blame information for a file and line number",
    {
        "repo_path": {
            "type": "string",
            "description": "Path to the repository",
            "required": True,
        },
        "file_path": {
            "type": "string",
            "description": "Path to the file to blame",
            "required": True,
        },
        "line_number": {
            "type": "number",
            "description": "Line number to blame",
            "required": True,
        },
    },
    lambda config: bool(config.github_username and config.github_api_key),
    "Configure github_username and github_api_key.",
)
@sanitize_path_arg("repo_path")
@sanitize_path_arg("file_path")
def git_blame(repo_path: str, file_path: str, line_number: int, agent: Agent) -> str:
    """Return blame information for the specified line of a file."""
    try:
        repo = Repo(repo_path)
        rel_path = os.path.relpath(file_path, repo_path)
        blame_output = repo.git.blame(
            "-L", f"{line_number},{line_number}", "--", rel_path
        )
        return f"Blame for {rel_path} line {line_number}: {blame_output}"
    except GitCommandError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
