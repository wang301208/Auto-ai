import pytest
from pathlib import Path
from git import Repo, Actor

from autogpt.utils.git import git_checkout, git_blame


@pytest.fixture
def init_repo(tmp_path: Path):
    repo_path = tmp_path / "repo"
    repo = Repo.init(repo_path)
    file_path = repo_path / "file.txt"
    author = Actor("Test User", "test@example.com")

    file_path.write_text("line1\nline2\n")
    repo.index.add([str(file_path)])
    commit1 = repo.index.commit("initial", author=author, committer=author)

    file_path.write_text("line1 changed\nline2\n")
    repo.index.add([str(file_path)])
    commit2 = repo.index.commit("second", author=author, committer=author)

    return repo_path, file_path, commit1, commit2


def test_git_checkout_success(init_repo):
    repo_path, file_path, commit1, commit2 = init_repo

    result = git_checkout(str(repo_path), commit1.hexsha)

    assert result["commit_hash"] == commit1.hexsha
    assert file_path.read_text() == "line1\nline2\n"


def test_git_checkout_invalid_revision(init_repo):
    repo_path, _, _, _ = init_repo
    with pytest.raises(ValueError):
        git_checkout(str(repo_path), "missing-branch")


def test_git_blame_success(init_repo):
    repo_path, file_path, commit1, commit2 = init_repo

    result = git_blame(str(file_path), 1)

    assert result["commit_hash"] == commit2.hexsha
    assert result["code"] == "line1 changed"


def test_git_blame_out_of_range(init_repo):
    _, file_path, _, _ = init_repo
    with pytest.raises(ValueError):
        git_blame(str(file_path), 10)


def test_git_blame_no_repo(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    with pytest.raises(FileNotFoundError):
        git_blame(str(file_path), 1)

def test_git_checkout_missing_repo(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        git_checkout(str(tmp_path / "missing"), "main")
