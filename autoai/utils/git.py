"""Helpers for interacting with Git repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError


class GitError(RuntimeError):
    """Raised when a git operation cannot be completed."""


def _get_repo(repo_path: Path) -> Repo:
    """Load a Git repository from ``repo_path``.

    Raises:
        FileNotFoundError: If the path does not exist or is not a git repository.
    """

    try:
        return Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):  # pragma: no cover - error path
        raise FileNotFoundError(f"Repository not found at {repo_path}")


def git_checkout(repo_path: str | Path, commit_or_branch: str) -> Dict[str, str]:
    """Checkout ``commit_or_branch`` in the repository located at ``repo_path``.

    Parameters
    ----------
    repo_path
        Path to the repository working tree.
    commit_or_branch
        Commit hash or branch name to check out.

    Returns
    -------
    dict
        Information about the checked out commit with keys:
        ``commit_hash``, ``author``, ``timestamp``, ``code`` (commit message).

    Raises
    ------
    FileNotFoundError
        If ``repo_path`` does not point to a valid Git repository.
    ValueError
        If ``commit_or_branch`` does not exist in the repository.
    """

    repo = _get_repo(Path(repo_path))

    try:
        repo.git.checkout(commit_or_branch)
    except GitCommandError as e:  # pragma: no cover - exercised in tests
        raise ValueError(f"Could not checkout '{commit_or_branch}': {e}")

    commit = repo.head.commit
    return {
        "commit_hash": commit.hexsha,
        "author": commit.author.name,
        "timestamp": commit.committed_datetime.isoformat(),
        # Using the commit message as a snippet describing the checkout
        "code": commit.message.strip(),
    }


def git_blame(file_path: str | Path, line_number: int) -> Dict[str, str]:
    """Return blame information for ``line_number`` in ``file_path``.

    Parameters
    ----------
    file_path
        Path to the file to blame.
    line_number
        1-indexed line number within the file.

    Returns
    -------
    dict
        Information about the blamed line with keys:
        ``commit_hash``, ``author``, ``timestamp``, ``code`` (line contents).

    Raises
    ------
    FileNotFoundError
        If the file or repository does not exist.
    ValueError
        If ``line_number`` is out of range for the file.
    """

    if line_number < 1:
        raise ValueError("line_number must be greater than zero")

    path = Path(file_path)
    if not path.exists():  # pragma: no cover - error path
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        repo = Repo(path.parent, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):  # pragma: no cover
        raise FileNotFoundError(f"No git repository found for {file_path}")

    rel_path = path.relative_to(repo.working_tree_dir)

    try:
        blame_data = repo.blame("HEAD", str(rel_path))
    except GitCommandError as e:  # pragma: no cover - error path
        raise ValueError(f"Could not retrieve blame for {file_path}: {e}")

    current_line = 1
    for commit, lines in blame_data:
        if current_line <= line_number <= current_line + len(lines) - 1:
            line = lines[line_number - current_line]
            return {
                "commit_hash": commit.hexsha,
                "author": commit.author.name,
                "timestamp": commit.committed_datetime.isoformat(),
                "code": line.rstrip("\n"),
            }
        current_line += len(lines)

    raise ValueError(
        f"Line number {line_number} out of range for file '{file_path}'"
    )
