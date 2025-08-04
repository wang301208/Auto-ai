import pytest
from git.exc import GitCommandError
from git.repo.base import Repo
from pathlib import Path

from autogpt.agents.agent import Agent
from autogpt.commands.git_operations import (
    clone_repository,
    git_blame,
    git_checkout,
    git_commit,
    git_create_branch,
    git_push,
)


@pytest.fixture
def mock_clone_from(mocker):
    return mocker.patch.object(Repo, "clone_from")


def test_clone_auto_gpt_repository(workspace, mock_clone_from, agent: Agent):
    mock_clone_from.return_value = None

    repo = "github.com/Significant-Gravitas/Auto-GPT.git"
    scheme = "https://"
    url = scheme + repo
    clone_path = str(workspace.get_path("auto-gpt-repo"))

    expected_output = f"Cloned {url} to {clone_path}"

    clone_result = clone_repository(url=url, clone_path=clone_path, agent=agent)

    assert clone_result == expected_output
    mock_clone_from.assert_called_once_with(
        url=f"{scheme}{agent.config.github_username}:{agent.config.github_api_key}@{repo}",
        to_path=clone_path,
    )


def test_clone_repository_error(workspace, mock_clone_from, agent: Agent):
    url = "https://github.com/this-repository/does-not-exist.git"
    clone_path = str(workspace.get_path("does-not-exist"))

    mock_clone_from.side_effect = GitCommandError(
        "clone", "fatal: repository not found", ""
    )

    result = clone_repository(url=url, clone_path=clone_path, agent=agent)

    assert "Error: " in result


def test_git_commit_success(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    mock_repo = mocker.Mock()
    mock_repo.is_dirty.return_value = True
    mock_repo.git.add.return_value = None
    mock_repo.index.commit.return_value = None
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_commit(repo_path=repo_path, message="message", agent=agent)

    assert result == f"Committed changes to {repo_path}"
    mock_repo.git.add.assert_called_once_with(A=True)
    mock_repo.index.commit.assert_called_once_with("message")


def test_git_commit_no_changes(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    mock_repo = mocker.Mock()
    mock_repo.is_dirty.return_value = False
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_commit(repo_path=repo_path, message="message", agent=agent)

    assert result == "No changes to commit."
    mock_repo.git.add.assert_not_called()
    mock_repo.index.commit.assert_not_called()


def test_git_commit_error(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    mock_repo = mocker.Mock()
    mock_repo.is_dirty.return_value = True
    mock_repo.git.add.return_value = None
    mock_repo.index.commit.side_effect = GitCommandError("commit", "err", "")
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_commit(repo_path=repo_path, message="message", agent=agent)

    assert result.startswith("Error: ")


def test_git_push_success(mocker, workspace, agent: Agent):
    agent.config.github_username = "user"
    agent.config.github_api_key = "key"
    repo_path = str(workspace.get_path("repo"))
    branch = "main"
    mock_origin = mocker.Mock()
    mock_origin.url = "https://github.com/repo.git"
    mock_repo = mocker.Mock()
    mock_repo.remote.return_value = mock_origin
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_push(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result == f"Pushed branch {branch} to remote"
    mock_repo.remote.assert_called_once_with(name="origin")
    mock_origin.set_url.assert_called_once_with(
        "https://user:key@github.com/repo.git"
    )
    mock_origin.push.assert_called_once_with(branch)


def test_git_push_error(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    branch = "main"
    mock_origin = mocker.Mock()
    mock_origin.url = "https://github.com/repo.git"
    mock_origin.push.side_effect = GitCommandError("push", "err", "")
    mock_repo = mocker.Mock()
    mock_repo.remote.return_value = mock_origin
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_push(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result.startswith("Error: ")


def test_git_create_branch_success(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    branch = "develop"
    existing_head = mocker.Mock()
    existing_head.name = "main"
    mock_repo = mocker.Mock()
    mock_repo.heads = [existing_head]
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_create_branch(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result == f"Created branch {branch}"
    mock_repo.create_head.assert_called_once_with(branch)


def test_git_create_branch_exists(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    branch = "develop"
    existing_head = mocker.Mock()
    existing_head.name = branch
    mock_repo = mocker.Mock()
    mock_repo.heads = [existing_head]
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_create_branch(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result == f"Branch {branch} already exists"
    mock_repo.create_head.assert_not_called()


def test_git_create_branch_error(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    branch = "develop"
    mock_repo = mocker.Mock()
    mock_repo.heads = []
    mock_repo.create_head.side_effect = GitCommandError("branch", "err", "")
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_create_branch(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result.startswith("Error: ")


def test_git_checkout_success(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    branch = "develop"
    mock_repo = mocker.Mock()
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_checkout(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result == f"Checked out branch {branch}"
    mock_repo.git.checkout.assert_called_once_with(branch)


def test_git_checkout_error(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    branch = "develop"
    mock_repo = mocker.Mock()
    mock_repo.git.checkout.side_effect = GitCommandError("checkout", "err", "")
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_checkout(repo_path=repo_path, branch_name=branch, agent=agent)

    assert result.startswith("Error: ")


def test_git_blame_success(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    file_path = str(Path(repo_path) / "file.txt")
    line = 10
    mock_repo = mocker.Mock()
    mock_repo.git.blame.return_value = "commit info"
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_blame(
        repo_path=repo_path, file_path=file_path, line_number=line, agent=agent
    )

    assert result == "Blame for file.txt line 10: commit info"
    mock_repo.git.blame.assert_called_once_with(
        "-L", f"{line},{line}", "--", "file.txt"
    )


def test_git_blame_error(mocker, workspace, agent: Agent):
    repo_path = str(workspace.get_path("repo"))
    file_path = str(Path(repo_path) / "file.txt")
    line = 10
    mock_repo = mocker.Mock()
    mock_repo.git.blame.side_effect = GitCommandError("blame", "err", "")
    mocker.patch("autogpt.commands.git_operations.Repo", return_value=mock_repo)

    result = git_blame(
        repo_path=repo_path, file_path=file_path, line_number=line, agent=agent
    )

    assert result.startswith("Error: ")
