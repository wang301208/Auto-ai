import importlib
import json
import sys
import types
from pathlib import Path

from pytest_mock import MockerFixture

from autoai.event_bus import (
    APPROVAL_GRANTED,
    CODE_FIX_PROPOSED,
    ApprovalGranted,
    CodeFixProposed,
    DeploymentFailed,
    HumanApprovalRequired,
    IssueResolved,
    TestsFailed,
)

# Avoid importing autoai.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autoai.agents")
agents_pkg.__path__ = ["autoai/agents"]
sys.modules.setdefault("autoai.agents", agents_pkg)

agent_stub = types.ModuleType("autoai.agents.agent")


class Agent:  # minimal stub to satisfy imports
    pass


agent_stub.Agent = Agent  # type: ignore[attr-defined]
sys.modules.setdefault("autoai.agents.agent", agent_stub)
agents_pkg.Agent = Agent  # type: ignore[attr-defined]

testing_stub = types.ModuleType("autoai.commands.testing")
testing_stub.run_tests = lambda *a, **k: ""  # type: ignore[attr-defined]
sys.modules.setdefault("autoai.commands.testing", testing_stub)

git_ops_stub = types.ModuleType("autoai.commands.git_operations")
git_ops_stub.git_checkout = lambda *a, **k: ""  # type: ignore[attr-defined]
git_ops_stub.git_clone = lambda *a, **k: ""  # type: ignore[attr-defined]
sys.modules.setdefault("autoai.commands.git_operations", git_ops_stub)

librarian_stub = types.ModuleType("autoai.skills.librarian")
librarian_stub.LibrarianAgent = object  # type: ignore[attr-defined]
sys.modules.setdefault("autoai.skills.librarian", librarian_stub)

qa_module = importlib.import_module("autoai.agents.qa_agent")
QAAgent = qa_module.QAAgent


def test_qa_agent_flow(tmp_path: Path, mocker: MockerFixture) -> None:
    message_queue = mocker.Mock(spec=["subscribe", "publish"])
    agent = mocker.Mock()
    agent.config.workspace_path = str(tmp_path)

    QAAgent(agent=agent, message_queue=message_queue)

    assert message_queue.subscribe.call_count == 2
    callbacks = {
        call.args[0]: call.args[1] for call in message_queue.subscribe.call_args_list
    }
    assert set(callbacks.keys()) == {CODE_FIX_PROPOSED, APPROVAL_GRANTED}

    on_code_fix_proposed = callbacks[CODE_FIX_PROPOSED]
    on_approval_granted = callbacks[APPROVAL_GRANTED]

    git_clone = mocker.patch.object(qa_module, "git_clone")
    git_checkout = mocker.patch.object(qa_module, "git_checkout")
    run_tests = mocker.patch.object(
        qa_module,
        "run_tests",
        return_value={
            "status": "passed",
            "exit_code": 0,
            "successes": 1,
            "failures": 0,
            "errors": 0,
            "logs": "tests passed",
        },
    )
    repo_mock = mocker.MagicMock()
    repo_mock.git.checkout.return_value = ""
    repo_mock.git.merge.return_value = ""
    repo_mock.git.diff.return_value = "diff content"
    origin_mock = mocker.MagicMock()
    origin_mock.url = "https://example.com/repo.git"
    remotes_mock = mocker.MagicMock()
    remotes_mock.origin = origin_mock
    repo_mock.remotes = remotes_mock
    mocker.patch.object(qa_module, "Repo", return_value=repo_mock)
    subprocess_run = mocker.patch.object(
        qa_module.subprocess, "run", return_value=mocker.MagicMock(returncode=0)
    )

    clone_dir = tmp_path / "clone"
    mocker.patch.object(
        qa_module.tempfile,
        "TemporaryDirectory",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=str(clone_dir)),
            __exit__=mocker.MagicMock(return_value=None),
        ),
    )

    event = CodeFixProposed(branch_name="fix/123", commit_hash="abc", summary="Fix bug")
    on_code_fix_proposed(event)

    git_clone.assert_called_once_with(
        "https://example.com/repo.git", str(clone_dir), agent
    )
    git_checkout.assert_called_once_with(str(clone_dir), "fix/123", agent)
    run_tests.assert_called_once_with(str(clone_dir), agent)
    message_queue.publish.assert_called_once()
    published_event = message_queue.publish.call_args[0][0]
    assert isinstance(published_event, HumanApprovalRequired)
    assert published_event.branch_name == "fix/123"
    assert published_event.test_output == "tests passed"
    assert published_event.summary == "Fix bug"
    assert published_event.diff == "diff content"

    message_queue.publish.reset_mock()

    approval_event = ApprovalGranted(
        branch_name="fix/123", commit_hash="abc", summary="Fix bug"
    )
    on_approval_granted(approval_event)

    repo_mock.git.checkout.assert_called_once_with("main")
    repo_mock.git.merge.assert_called_once_with("fix/123")
    subprocess_run.assert_called_once_with(
        ["bash", "scripts/deploy.sh"], cwd=str(tmp_path), check=False
    )
    message_queue.publish.assert_called_once()
    resolved_event = message_queue.publish.call_args[0][0]
    assert isinstance(resolved_event, IssueResolved)
    assert resolved_event.branch_name == "fix/123"
    assert resolved_event.commit_hash == "abc"
    assert resolved_event.summary == "Fix bug"


def test_qa_agent_handles_failed_tests(tmp_path: Path, mocker: MockerFixture) -> None:
    message_queue = mocker.Mock(spec=["subscribe", "publish"])
    agent = mocker.Mock()
    agent.config.workspace_path = str(tmp_path)

    QAAgent(agent=agent, message_queue=message_queue)

    callbacks = {
        call.args[0]: call.args[1] for call in message_queue.subscribe.call_args_list
    }
    on_code_fix_proposed = callbacks[CODE_FIX_PROPOSED]

    git_clone = mocker.patch.object(qa_module, "git_clone")
    git_checkout = mocker.patch.object(qa_module, "git_checkout")
    run_tests = mocker.patch.object(
        qa_module,
        "run_tests",
        return_value={
            "status": "failed",
            "exit_code": 1,
            "successes": 0,
            "failures": 1,
            "errors": 0,
            "logs": "tests failed",
        },
    )
    repo_mock = mocker.MagicMock()
    origin_mock = mocker.MagicMock()
    origin_mock.url = "https://example.com/repo.git"
    remotes_mock = mocker.MagicMock()
    remotes_mock.origin = origin_mock
    repo_mock.remotes = remotes_mock
    mocker.patch.object(qa_module, "Repo", return_value=repo_mock)
    mocker.patch.object(qa_module.subprocess, "run")

    clone_dir = tmp_path / "clone"
    mocker.patch.object(
        qa_module.tempfile,
        "TemporaryDirectory",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=str(clone_dir)),
            __exit__=mocker.MagicMock(return_value=None),
        ),
    )

    event = CodeFixProposed(branch_name="fix/123", commit_hash="abc", summary="Fix bug")
    on_code_fix_proposed(event)

    git_clone.assert_called_once_with(
        "https://example.com/repo.git", str(clone_dir), agent
    )
    git_checkout.assert_called_once_with(str(clone_dir), "fix/123", agent)
    run_tests.assert_called_once_with(str(clone_dir), agent)
    message_queue.publish.assert_called_once()
    published_event = message_queue.publish.call_args[0][0]
    assert isinstance(published_event, TestsFailed)
    assert repo_mock.git.merge.call_count == 0


def test_qa_agent_handles_deployment_failure(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    message_queue = mocker.Mock(spec=["subscribe", "publish"])
    agent = mocker.Mock()
    agent.config.workspace_path = str(tmp_path)

    QAAgent(agent=agent, message_queue=message_queue)

    callbacks = {
        call.args[0]: call.args[1] for call in message_queue.subscribe.call_args_list
    }
    on_code_fix_proposed = callbacks[CODE_FIX_PROPOSED]
    on_approval_granted = callbacks[APPROVAL_GRANTED]

    mocker.patch.object(qa_module, "git_clone")
    mocker.patch.object(qa_module, "git_checkout")
    mocker.patch.object(
        qa_module,
        "run_tests",
        return_value={
            "status": "passed",
            "exit_code": 0,
            "successes": 1,
            "failures": 0,
            "errors": 0,
            "logs": "tests passed",
        },
    )
    repo_mock = mocker.MagicMock()
    repo_mock.git.checkout.return_value = ""
    repo_mock.git.merge.return_value = ""
    origin_mock = mocker.MagicMock()
    origin_mock.url = "https://example.com/repo.git"
    remotes_mock = mocker.MagicMock()
    remotes_mock.origin = origin_mock
    repo_mock.remotes = remotes_mock
    mocker.patch.object(qa_module, "Repo", return_value=repo_mock)
    subprocess_run = mocker.patch.object(
        qa_module.subprocess,
        "run",
        return_value=mocker.MagicMock(returncode=1),
    )

    clone_dir = tmp_path / "clone"
    mocker.patch.object(
        qa_module.tempfile,
        "TemporaryDirectory",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=str(clone_dir)),
            __exit__=mocker.MagicMock(return_value=None),
        ),
    )

    event = CodeFixProposed(branch_name="fix/123", commit_hash="abc", summary="Fix bug")
    on_code_fix_proposed(event)

    approval_event = ApprovalGranted(
        branch_name="fix/123", commit_hash="abc", summary="Fix bug"
    )
    on_approval_granted(approval_event)

    repo_mock.git.checkout.assert_called_once_with("main")
    repo_mock.git.merge.assert_called_once_with("fix/123")
    subprocess_run.assert_called_once_with(
        ["bash", "scripts/deploy.sh"], cwd=str(tmp_path), check=False
    )
    message_queue.publish.assert_called()
    assert all(
        not isinstance(call.args[0], IssueResolved)
        for call in message_queue.publish.call_args_list
    )
    assert len(message_queue.publish.call_args_list) == 2
    published_event = message_queue.publish.call_args_list[-1][0][0]
    assert isinstance(published_event, DeploymentFailed)


def test_qa_agent_registers_new_skills(tmp_path: Path, mocker: MockerFixture) -> None:
    message_queue = mocker.Mock(spec=["subscribe", "publish"])
    agent = mocker.Mock()
    agent.config.workspace_path = str(tmp_path)
    librarian = mocker.Mock()

    QAAgent(agent=agent, message_queue=message_queue, librarian=librarian)

    callbacks = {call.args[0]: call.args[1] for call in message_queue.subscribe.call_args_list}
    on_approval_granted = callbacks[APPROVAL_GRANTED]

    repo_mock = mocker.MagicMock()
    repo_mock.git.checkout.return_value = ""
    repo_mock.git.merge.return_value = ""
    repo_mock.git.diff.return_value = "A\tskill_library/test_skill/skill.json"
    origin_mock = mocker.MagicMock()
    origin_mock.url = "https://example.com/repo.git"
    remotes_mock = mocker.MagicMock()
    remotes_mock.origin = origin_mock
    repo_mock.remotes = remotes_mock
    mocker.patch.object(qa_module, "Repo", return_value=repo_mock)
    mocker.patch.object(
        qa_module.subprocess, "run", return_value=mocker.MagicMock(returncode=0)
    )

    skill_dir = tmp_path / "skill_library" / "test_skill"
    skill_dir.mkdir(parents=True)
    metadata = {
        "name": "Test Skill",
        "entry_point": "run.py",
    }
    (skill_dir / "skill.json").write_text(json.dumps(metadata), encoding="utf-8")
    (skill_dir / "run.py").write_text("def run(): pass", encoding="utf-8")

    approval_event = ApprovalGranted(
        branch_name="fix/123",
        commit_hash="abc",
        summary="Fix bug",
        approved_by="alice",
        approval_timestamp="2024-01-02T00:00:00Z",
    )
    on_approval_granted(approval_event)

    expected_metadata = {
        "name": "Test Skill",
        "entry_point": "run.py",
        "approved_by": "alice",
        "approval_timestamp": "2024-01-02T00:00:00Z",
    }
    librarian.add_skill.assert_called_once_with(
        expected_metadata, str(skill_dir / "run.py")
    )
