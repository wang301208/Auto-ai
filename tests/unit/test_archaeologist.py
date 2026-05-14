import importlib
import sys
import types
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from autoai.config import Config
from autoai.event_bus import (
    DIAGNOSIS_COMPLETE,
    ISSUE_DETECTED,
    DiagnosisComplete,
    EventBus,
    EventMessage,
    MessageQueue,
)

# Avoid importing autoai.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autoai.agents")
agents_pkg.__path__ = ["autoai/agents"]
sys.modules.setdefault("autoai.agents", agents_pkg)

arch_module = importlib.import_module("autoai.agents.archaeologist")
Archaeologist = arch_module.Archaeologist


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED])
@pytest.mark.parametrize("use_librarian", [True, False])
def test_archaeologist_handles_issue(
    tmp_path: Path, event_type: str, use_librarian: bool
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    with patch.object(arch_module.LibrarianAgent, "find_skill", return_value=[]):
        Archaeologist(message_queue, config=Config(use_librarian=use_librarian))

        received: list[DiagnosisComplete] = []
        message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

        payload = {
            "plugin": "test_plugin",
            "error_log": "traceback",
            "commit": "HEAD",
            "file": "autoai/agents/agent.py",
            "line": 10,
            "extra": "meta",
            "description": "traceback",
            "issue_type": "bug",
        }

        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert len(received) == 1
    diag = received[0]
    assert "test_plugin" in diag.summary
    assert isinstance(diag.actionable_recommendations, str)
    assert diag.details is not None
    details = cast(dict[str, Any], diag.details)
    assert details["blame"]["commit"]
    assert details["blame"]["author"]
    assert any(c["line"] == 10 for c in details["context"])
    assert isinstance(details["dependencies"], list)
    assert details["recommended_skill"] is None
    assert details["plugin"] == "test_plugin"


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED])
@pytest.mark.parametrize("use_librarian", [True, False])
def test_archaeologist_parses_python_traceback(
    tmp_path: Path, event_type: str, use_librarian: bool
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    with patch.object(arch_module.LibrarianAgent, "find_skill", return_value=[]):
        Archaeologist(message_queue, config=Config(use_librarian=use_librarian))

        received: list[DiagnosisComplete] = []
        message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

        payload = {
            "plugin": "test_plugin",
            "error_log": (
                "Traceback (most recent call last):\n"
                '  File "autoai/agents/agent.py", line 42, in <module>\n'
                "    raise Exception()\n"
            ),
            "description": "traceback",
            "issue_type": "bug",
        }

        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert "autoai/agents/agent.py:42" in received[0].summary


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED])
@pytest.mark.parametrize("use_librarian", [True, False])
def test_archaeologist_parses_plugin_log(
    tmp_path: Path, event_type: str, use_librarian: bool
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    with patch.object(arch_module.LibrarianAgent, "find_skill", return_value=[]):
        Archaeologist(message_queue, config=Config(use_librarian=use_librarian))

        received: list[DiagnosisComplete] = []
        message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

        payload = {
            "plugin": "test_plugin",
            "error_log": "ERROR at autoai/agents/agent.py:50 something went wrong",
            "description": "plugin log error",
            "issue_type": "bug",
        }

        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert "autoai/agents/agent.py:50" in received[0].summary


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED])
@pytest.mark.parametrize("use_librarian", [True, False])
def test_archaeologist_parsing_fails_gracefully(
    tmp_path: Path, event_type: str, use_librarian: bool
) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    with patch.object(arch_module.LibrarianAgent, "find_skill", return_value=[]):
        Archaeologist(message_queue, config=Config(use_librarian=use_librarian))

        received: list[DiagnosisComplete] = []
        message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

        payload = {
            "plugin": "test_plugin",
            "error_log": "unstructured log message",
            "description": "unstructured log message",
            "issue_type": "bug",
        }

        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert "autoai/agents/agent.py" not in received[0].summary
