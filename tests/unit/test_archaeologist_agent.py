import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    DiagnosisComplete,
    EventMessage,
    MessageQueue,
)

# Avoid importing autogpt.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autogpt.agents")
agents_pkg.__path__ = ["autogpt/agents"]
sys.modules.setdefault("autogpt.agents", agents_pkg)

arch_module = importlib.import_module("autogpt.agents.archaeologist")
dep_module = importlib.import_module("autogpt.agents.archaeologist_dependency")
Archaeologist = arch_module.Archaeologist
ISSUE_DETECTED = arch_module.ISSUE_DETECTED


def test_archaeologist_agent_diagnosis_complete(tmp_path: Path) -> None:
    message_queue = MessageQueue()
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    source_file = tmp_path / "mod.py"
    source_file.write_text("import sample_dep\n")

    commands: list[list[str]] = []

    def fake_run(cmd, capture_output=True, text=True):
        commands.append(cmd)
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return SimpleNamespace(stdout="main\n", stderr="")
        if cmd[:2] == ["git", "checkout"]:
            return SimpleNamespace(stdout="", stderr="")
        if cmd[:2] == ["git", "blame"]:
            return SimpleNamespace(stdout="^123 (user 2023-01-01 1) line\n", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    with (
        patch.object(arch_module.subprocess, "run", side_effect=fake_run) as mock_run,
        patch.object(dep_module.metadata, "version", return_value="1.0"),
        patch.object(
            dep_module,
            "fetch_release_notes",
            return_value="deprecated features may break",
        ),
        patch.object(
            arch_module,
            "analyze_dependency",
            wraps=arch_module.analyze_dependency,
        ) as mock_analyze,
    ):
        payload = {
            "plugin": "test_plugin",
            "error_log": (
                "Traceback (most recent call last):\n"
                f'  File "{source_file}", line 1, in <module>'
            ),
            "commit": "abc123",
        }
        message_queue.publish(
            EventMessage(event_type=ISSUE_DETECTED, payload=payload, source_agent="tester")
        )

    assert any(cmd[:2] == ["git", "checkout"] for cmd in commands)
    assert any(cmd[:2] == ["git", "blame"] for cmd in commands)
    assert mock_run.call_count >= 3
    assert mock_analyze.called

    assert len(received) == 1
    diag = received[0]
    expected_summary = f"Diagnostics for plugin test_plugin at {source_file}:1"
    assert diag.summary == expected_summary
    assert "Investigate compatibility issues in: sample_dep" in diag.actionable_recommendations
