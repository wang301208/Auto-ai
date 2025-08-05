import importlib
import sys
import types
from pathlib import Path

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
            {"successes": 0, "failures": 1, "errors": 0, "logs": "1 failed"},
            {"successes": 1, "failures": 1, "errors": 0, "logs": "1 failed"},
            {"successes": 2, "failures": 0, "errors": 0, "logs": "2 passed"},
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
            {"successes": 0, "failures": 1, "errors": 0},
            {"successes": 0, "failures": 1, "errors": 0},
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
