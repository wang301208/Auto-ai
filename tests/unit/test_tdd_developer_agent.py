import importlib
import sys
import types
from pathlib import Path

from autogpt.event_bus import CODE_FIX_PROPOSED, DIAGNOSIS_COMPLETE, EventMessage

# Avoid importing autogpt.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autogpt.agents")
agents_pkg.__path__ = ["autogpt/agents"]
sys.modules.setdefault("autogpt.agents", agents_pkg)

agent_stub = types.ModuleType("autogpt.agents.agent")
class Agent:  # minimal stub to satisfy imports
    pass
agent_stub.Agent = Agent
sys.modules.setdefault("autogpt.agents.agent", agent_stub)

# Stub memory and text processing modules to avoid heavy dependencies
memory_pkg = types.ModuleType("autogpt.memory")
vector_stub = types.ModuleType("autogpt.memory.vector")
class MemoryItem:  # minimal stub
    pass
class VectorMemory:  # minimal stub
    pass
vector_stub.MemoryItem = MemoryItem
vector_stub.VectorMemory = VectorMemory
memory_pkg.vector = vector_stub
sys.modules.setdefault("autogpt.memory", memory_pkg)
sys.modules.setdefault("autogpt.memory.vector", vector_stub)
sys.modules.setdefault(
    "autogpt.memory.vector.providers", types.ModuleType("autogpt.memory.vector.providers")
)

processing_stub = types.ModuleType("autogpt.processing.text")
processing_stub.chunk_content = lambda *a, **k: []
processing_stub.split_text = lambda *a, **k: []
processing_stub.summarize_text = lambda *a, **k: ""
sys.modules.setdefault("autogpt.processing.text", processing_stub)

testing_stub = types.ModuleType("autogpt.commands.testing")
testing_stub.create_test_file = lambda *a, **k: ""
testing_stub.run_tests = lambda *a, **k: ""
sys.modules.setdefault("autogpt.commands.testing", testing_stub)

git_ops_stub = types.ModuleType("autogpt.commands.git_operations")
git_ops_stub.git_create_branch = lambda *a, **k: ""
git_ops_stub.git_checkout = lambda *a, **k: ""
git_ops_stub.git_commit = lambda *a, **k: ""
sys.modules.setdefault("autogpt.commands.git_operations", git_ops_stub)

tdd_module = importlib.import_module("autogpt.agents.tdd_developer")
TDDDeveloper = tdd_module.TDDDeveloper


def test_tdd_developer_agent_flow(tmp_path, mocker):
    message_queue = mocker.Mock(spec=["subscribe", "publish"])
    agent = mocker.Mock()

    TDDDeveloper(agent=agent, message_queue=message_queue)

    message_queue.subscribe.assert_called_once()
    subscribed_event, callback = message_queue.subscribe.call_args[0]
    assert subscribed_event == DIAGNOSIS_COMPLETE

    create_branch = mocker.patch.object(tdd_module, "git_create_branch", return_value="")
    checkout = mocker.patch.object(tdd_module, "git_checkout", return_value="")
    create_test = mocker.patch.object(tdd_module, "create_test_file", return_value="")
    run = mocker.patch.object(
        tdd_module, "run_tests", side_effect=["1 failed", "1 passed"]
    )
    commit = mocker.patch.object(tdd_module, "git_commit", return_value="")
    mocker.patch.object(tdd_module, "Repo", side_effect=Exception("git error"))

    repo_path = str(tmp_path)
    payload = {"issue_id": "123", "repo_path": repo_path, "diagnostics": "details"}
    event = EventMessage(
        event_type=DIAGNOSIS_COMPLETE, payload=payload, source_agent="tester"
    )

    callback(event)

    create_branch.assert_called_once_with(repo_path, "fix/123", agent)
    checkout.assert_called_once_with(repo_path, "fix/123", agent)

    expected_test_file = Path(repo_path) / "tests" / "test_issue_123.py"
    create_test.assert_called_once_with(
        str(expected_test_file),
        "# Auto-generated regression test for issue 123\ndetails\n",
        agent,
    )

    assert run.call_count == 2
    run.assert_has_calls([
        mocker.call(str(expected_test_file), agent),
        mocker.call(repo_path, agent),
    ])

    commit.assert_called_once_with(repo_path, "Fix issue 123", agent)

    message_queue.publish.assert_called_once()
    published_event = message_queue.publish.call_args[0][0]
    assert published_event.event_type == CODE_FIX_PROPOSED
    assert published_event.payload["branch_name"] == "fix/123"
    assert published_event.payload["summary"] == "Fix issue 123"
    assert published_event.payload["commit_hash"] == ""
