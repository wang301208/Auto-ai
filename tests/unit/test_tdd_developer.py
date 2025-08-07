import importlib
import sys
import types
from pathlib import Path
from unittest.mock import ANY

from pytest_mock import MockerFixture

from autogpt.agents.agent import Agent
from autogpt.event_bus import (
    CODE_FIX_PROPOSED,
    DIAGNOSIS_COMPLETE,
    EventBus,
    EventMessage,
    MessageQueue,
)
from autogpt.workspace import Workspace

# Avoid importing autogpt.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autogpt.agents")
agents_pkg.__path__ = ["autogpt/agents"]
sys.modules.setdefault("autogpt.agents", agents_pkg)

tdd_module = importlib.import_module("autogpt.agents.tdd_developer")
TDDDeveloper = tdd_module.TDDDeveloper


def test_tdd_developer_handles_diagnosis(
    agent: Agent, workspace: Workspace, tmp_path: Path, mocker: MockerFixture
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    TDDDeveloper(agent=agent, message_queue=message_queue)

    create_branch = mocker.patch(
        "autogpt.agents.tdd_developer.git_create_branch", return_value=""
    )
    checkout = mocker.patch(
        "autogpt.agents.tdd_developer.git_checkout", return_value=""
    )
    create_test = mocker.patch(
        "autogpt.agents.tdd_developer.create_test_file", return_value=""
    )
    write_file = mocker.patch(
        "autogpt.agents.tdd_developer.write_to_file", return_value=""
    )
    run = mocker.patch(
        "autogpt.agents.tdd_developer.run_tests",
        side_effect=[
            {
                "status": "failed",
                "exit_code": 1,
                "successes": 0,
                "failures": 1,
                "errors": 0,
                "logs": "1 failed",
            },
            {
                "status": "failed",
                "exit_code": 1,
                "successes": 1,
                "failures": 1,
                "errors": 0,
                "logs": "1 failed",
            },
            {
                "status": "passed",
                "exit_code": 0,
                "successes": 2,
                "failures": 0,
                "errors": 0,
                "logs": "2 passed",
            },
        ],
    )
    commit = mocker.patch("autogpt.agents.tdd_developer.git_commit", return_value="")

    received: list[EventMessage] = []
    message_queue.subscribe(CODE_FIX_PROPOSED, lambda msg: received.append(msg))

    repo_path = str(workspace.root)
    payload = {
        "issue_id": "123",
        "repo_path": repo_path,
        "diagnostics": {
            "fixes": [
                {"module.py": "print('fix1')"},
                {"module.py": "print('fix2')"},
            ]
        },
    }

    message_queue.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
        )
    )

    create_branch.assert_called_once_with(repo_path, "fix/123", agent)
    checkout.assert_called_once_with(repo_path, "fix/123", agent)
    create_test.assert_called_once()
    assert write_file.call_count == 2
    assert run.call_count == 3
    commit.assert_called_once_with(repo_path, "Fix issue 123", agent)
    assert len(received) == 1
    assert received[0].event_type == CODE_FIX_PROPOSED
    assert received[0].payload["branch_name"] == "fix/123"
    assert received[0].payload["summary"] == "Fix issue 123"
    assert "commit_hash" in received[0].payload


def test_tdd_developer_generates_repro_test(
    agent: Agent, workspace: Workspace, tmp_path: Path, mocker: MockerFixture
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    TDDDeveloper(agent=agent, message_queue=message_queue)

    mocker.patch("autogpt.agents.tdd_developer.git_create_branch", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.git_checkout", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.git_commit", return_value="")

    captured: dict[str, str] = {}

    def capture_create_test_file(path: str, content: str, *_: object) -> str:
        captured["content"] = content
        return ""

    mocker.patch(
        "autogpt.agents.tdd_developer.create_test_file", side_effect=capture_create_test_file
    )

    mocker.patch(
        "autogpt.agents.tdd_developer.run_tests",
        side_effect=[
            {
                "status": "failed",
                "exit_code": 1,
                "successes": 0,
                "failures": 1,
                "errors": 0,
            },
            {
                "status": "failed",
                "exit_code": 1,
                "successes": 0,
                "failures": 1,
                "errors": 0,
            },
        ],
    )

    repo_path = str(workspace.root)
    module_path = Path(repo_path) / "buggy.py"
    diag = (
        "Traceback (most recent call last):\n"
        f"  File \"{module_path}\", line 1, in buggy_fn\n"
        "    buggy_fn()\n"
        "ValueError: boom\n"
    )

    payload = {"issue_id": "456", "repo_path": repo_path, "diagnostics": diag}

    message_queue.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
        )
    )

    content = captured.get("content", "")
    assert "from buggy import buggy_fn" in content
    assert "pytest.raises(ValueError)" in content


def test_tdd_developer_handles_recommended_skill_without_fix_loop(
    agent: Agent, workspace: Workspace, tmp_path: Path, mocker: MockerFixture
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    TDDDeveloper(agent=agent, message_queue=message_queue)

    mocker.patch("autogpt.agents.tdd_developer.git_create_branch", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.git_checkout", return_value="")
    write_file = mocker.patch(
        "autogpt.agents.tdd_developer.write_to_file", return_value="",
    )
    create_test = mocker.patch(
        "autogpt.agents.tdd_developer.create_test_file", return_value="",
    )

    repo_path = str(workspace.root)
    script_path = Path(repo_path) / "scripts" / "use_hello_world.py"
    test_path = Path(repo_path) / "tests" / "test_use_hello_world.py"

    run_paths: list[str] = []

    def capture_run(path: str, *_: object) -> dict[str, int]:
        run_paths.append(path)
        return {"exit_code": 0}

    run = mocker.patch(
        "autogpt.agents.tdd_developer.run_tests", side_effect=capture_run
    )
    commit = mocker.patch("autogpt.agents.tdd_developer.git_commit", return_value="")

    received: list[EventMessage] = []
    message_queue.subscribe(CODE_FIX_PROPOSED, lambda msg: received.append(msg))

    payload = {
        "issue_id": "99",
        "repo_path": repo_path,
        "details": {
            "recommended_skill": {
                "name": "hello_world",
                "version": "1.0",
                "parameters": {"foo": "bar"},
            }
        },
    }

    message_queue.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
        )
    )

    write_file.assert_called_once_with(str(script_path), ANY, agent)
    create_test.assert_called_once_with(str(test_path), ANY, agent)
    assert run_paths == [str(test_path)]
    commit.assert_called_once_with(repo_path, "Use recommended skill hello_world", agent)
    assert len(received) == 1
    assert received[0].payload["branch_name"] == "fix/99"
    assert received[0].payload["summary"] == "Use recommended skill hello_world"


def test_tdd_developer_adds_new_skill(
    agent: Agent, workspace: Workspace, tmp_path: Path, mocker: MockerFixture
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    librarian = mocker.Mock()
    TDDDeveloper(agent=agent, message_queue=message_queue, librarian=librarian)

    create_branch = mocker.patch("autogpt.agents.tdd_developer.git_create_branch", return_value="")
    checkout = mocker.patch("autogpt.agents.tdd_developer.git_checkout", return_value="")
    write_file = mocker.patch("autogpt.agents.tdd_developer.write_to_file", return_value="")
    run = mocker.patch("autogpt.agents.tdd_developer.run_tests")
    commit = mocker.patch("autogpt.agents.tdd_developer.git_commit", return_value="")

    repo_obj = types.SimpleNamespace(head=types.SimpleNamespace(commit=types.SimpleNamespace(hexsha="abc123")))
    mocker.patch("autogpt.agents.tdd_developer.Repo", return_value=repo_obj)

    received: list[EventMessage] = []
    message_queue.subscribe(CODE_FIX_PROPOSED, lambda msg: received.append(msg))

    repo_path = str(workspace.root)
    payload = {
        "repo_path": repo_path,
        "details": {
            "new_skill": {
                "skill_name": "awesome",
                "version": "1.0",
                "code": "def run(): pass",
            }
        },
    }

    message_queue.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
        )
    )

    branch = 'new-skill/awesome_1.0'
    create_branch.assert_called_once_with(repo_path, branch, agent)
    checkout.assert_called_once_with(repo_path, branch, agent)
    skill_dir = Path(repo_path) / "skill_library" / "awesome_1.0"
    write_file.assert_any_call(str(skill_dir / "main.py"), "def run(): pass", agent)
    write_file.assert_any_call(str(skill_dir / "skill.json"), ANY, agent)
    assert write_file.call_count == 2
    expected_metadata = {
        "skill_name": "awesome",
        "version": "1.0",
        "description": "",
        "tags": [],
        "parameters": {},
    }
    librarian.add_skill.assert_called_once_with(expected_metadata, str(skill_dir / "main.py"))
    commit.assert_called_once_with(repo_path, "Add new skill awesome", agent)
    run.assert_not_called()
    assert len(received) == 1
    assert received[0].payload["branch_name"] == "new-skill/awesome_1.0"
    assert received[0].payload["summary"] == "Add new skill awesome"


def test_tdd_developer_aborts_on_failed_add_skill(
    agent: Agent, workspace: Workspace, tmp_path: Path, mocker: MockerFixture
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    librarian = mocker.Mock()
    librarian.add_skill.side_effect = RuntimeError("failure")
    TDDDeveloper(agent=agent, message_queue=message_queue, librarian=librarian)

    mocker.patch("autogpt.agents.tdd_developer.git_create_branch", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.git_checkout", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.write_to_file", return_value="")
    commit = mocker.patch("autogpt.agents.tdd_developer.git_commit", return_value="")

    repo_path = str(workspace.root)
    payload = {
        "repo_path": repo_path,
        "details": {
            "new_skill": {
                "skill_name": "awesome",
                "version": "1.0",
                "code": "def run(): pass",
            }
        },
    }

    message_queue.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
        )
    )

    librarian.add_skill.assert_called_once()
    commit.assert_not_called()


def test_tdd_developer_learning_phase(
    agent: Agent, workspace: Workspace, tmp_path: Path, mocker: MockerFixture
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    dev = TDDDeveloper(agent=agent, message_queue=message_queue)

    learn = mocker.patch(
        "autogpt.agents.tdd_developer.read_and_understand_code", return_value="report"
    )
    mocker.patch("autogpt.agents.tdd_developer.git_create_branch", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.git_checkout", return_value="")
    mocker.patch(
        "autogpt.agents.tdd_developer.create_test_file", return_value=""
    )
    mocker.patch(
        "autogpt.agents.tdd_developer.run_tests",
        return_value={"status": "failed", "exit_code": 1, "successes": 0, "failures": 1, "errors": 0, "logs": ""},
    )
    mocker.patch("autogpt.agents.tdd_developer.git_commit", return_value="")
    mocker.patch("autogpt.agents.tdd_developer.write_to_file", return_value="")

    repo_path = str(workspace.root)
    payload = {
        "issue_id": "1",
        "repo_path": repo_path,
        "diagnostics": {"source_code_paths": {"lib": str(tmp_path)}}
    }

    message_queue.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
        )
    )

    learn.assert_called_once_with(str(tmp_path), agent)
    assert dev.learned_sources["lib"] == "report"
