import importlib
import sys
import types
from pathlib import Path

from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    DiagnosisComplete,
    EventBus,
    EventMessage,
    MessageQueue,
)

# Avoid importing autogpt.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autogpt.agents")
agents_pkg.__path__ = ["autogpt/agents"]
sys.modules.setdefault("autogpt.agents", agents_pkg)

arch_module = importlib.import_module("autogpt.agents.archaeologist")
Archaeologist = arch_module.Archaeologist
ISSUE_DETECTED = arch_module.ISSUE_DETECTED


def test_archaeologist_handles_issue(tmp_path: Path) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    payload = {
        "plugin": "test_plugin",
        "error_log": "traceback",
        "commit": "HEAD",
        "file": "autogpt/agents/agent.py",
        "line": 10,
        "extra": "meta",
    }

    message_queue.publish(
        EventMessage(event_type=ISSUE_DETECTED, payload=payload, source_agent="tester")
    )

    assert len(received) == 1
    diag = received[0]
    assert "test_plugin" in diag.summary
    assert isinstance(diag.actionable_recommendations, str)


def test_archaeologist_parses_python_traceback(tmp_path: Path) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    payload = {
        "plugin": "test_plugin",
        "error_log": (
            "Traceback (most recent call last):\n"
            '  File "autogpt/agents/agent.py", line 42, in <module>\n'
            "    raise Exception()\n"
        ),
    }

    message_queue.publish(
        EventMessage(event_type=ISSUE_DETECTED, payload=payload, source_agent="tester")
    )

    assert "autogpt/agents/agent.py:42" in received[0].summary


def test_archaeologist_parses_plugin_log(tmp_path: Path) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    payload = {
        "plugin": "test_plugin",
        "error_log": "ERROR at autogpt/agents/agent.py:50 something went wrong",
    }

    message_queue.publish(
        EventMessage(event_type=ISSUE_DETECTED, payload=payload, source_agent="tester")
    )

    assert "autogpt/agents/agent.py:50" in received[0].summary


def test_archaeologist_parsing_fails_gracefully(tmp_path: Path) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    payload = {
        "plugin": "test_plugin",
        "error_log": "unstructured log message",
    }

    message_queue.publish(
        EventMessage(event_type=ISSUE_DETECTED, payload=payload, source_agent="tester")
    )

    assert "autogpt/agents/agent.py" not in received[0].summary
