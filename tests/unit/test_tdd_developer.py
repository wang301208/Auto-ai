import importlib
import sys
import types
from pathlib import Path

from autogpt.event_bus import DIAGNOSIS_COMPLETE, EventBus, EventMessage, MessageQueue

# Avoid importing autogpt.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autogpt.agents")
agents_pkg.__path__ = ["autogpt/agents"]
sys.modules.setdefault("autogpt.agents", agents_pkg)

tdd_module = importlib.import_module("autogpt.agents.tdd_developer")
TDDDeveloper = tdd_module.TDDDeveloper
CODE_FIX_PROPOSED = tdd_module.CODE_FIX_PROPOSED

def test_tdd_developer_handles_diagnosis(agent, workspace, tmp_path, mocker):
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
    run = mocker.patch(
        "autogpt.agents.tdd_developer.run_tests", side_effect=["1 failed", "1 passed"]
    )
    commit = mocker.patch(
        "autogpt.agents.tdd_developer.git_commit", return_value=""
    )

    received: list[EventMessage] = []
    message_queue.subscribe(
        CODE_FIX_PROPOSED, lambda msg: received.append(msg)
    )

    repo_path = str(workspace.root)
    payload = {"issue_id": "123", "repo_path": repo_path, "diagnostics": "details"}

    message_queue.publish(
        EventMessage(event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester")
    )

    create_branch.assert_called_once_with(repo_path, "fix/123", agent)
    checkout.assert_called_once_with(repo_path, "fix/123", agent)
    create_test.assert_called_once()
    assert run.call_count == 2
    commit.assert_called_once_with(repo_path, "Fix issue 123", agent)
    assert len(received) == 1
    assert received[0].event_type == CODE_FIX_PROPOSED
    assert received[0].payload["issue_id"] == "123"
