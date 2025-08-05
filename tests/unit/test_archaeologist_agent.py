import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest

import autogpt.skills.librarian as librarian_module
import autogpt.skills.library as library_module
from autogpt.app.i18n import _
from autogpt.config import Config
from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    ISSUE_DETECTED,
    TICKET_RECEIVED,
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


def make_agent() -> Archaeologist:
    """Create Archaeologist with default config for query generation tests."""
    return Archaeologist(MessageQueue(), config=Config(use_librarian=False))


@pytest.mark.parametrize(
    "payload, expected",
    [
        # Error log missing -> description is returned as-is
        ({"description": "runtime error", "plugin": "test"}, "runtime error"),
        # Description missing -> include error log and metadata
        (
            {
                "plugin": "test_plugin",
                "issue_type": "bug",
                "error_log": "ValueError: bad",
                "file": "mod.py",
                "line": 10,
            },
            "bug in plugin test_plugin, ValueError: bad, file mod.py, line 10",
        ),
        # Description and error log missing -> fall back to other metadata
        (
            {"plugin": "p", "issue_type": "dependency_update", "file": "mod.py"},
            "dependency update in plugin p, file mod.py",
        ),
        ({}, ""),
    ],
)
def test_generate_query(payload: dict, expected: str) -> None:
    agent = make_agent()
    assert agent._generate_query(payload) == expected


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_archaeologist_agent_diagnosis_complete(
    tmp_path: Path, event_type: str
) -> None:
    message_queue = MessageQueue()
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    source_file = tmp_path / "mod.py"
    source_file.write_text("import sample_dep\n")

    commands: list[list[str]] = []

    def fake_run(
        cmd: list[str], capture_output: bool = True, text: bool = True
    ) -> SimpleNamespace:
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
        patch.object(
            arch_module.LibrarianAgent,
            "find_skill",
            return_value=[
                {
                    "skill_name": "sample_skill",
                    "version": "1",
                    "parameters": {"path": "str"},
                }
            ],
        ),
    ):
        payload = {
            "plugin": "test_plugin",
            "error_log": (
                "Traceback (most recent call last):\n"
                f'  File "{source_file}", line 1, in <module>'
            ),
            "commit": "abc123",
            "description": "runtime error",
            "issue_type": "bug",
        }
        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert any(cmd[:2] == ["git", "checkout"] for cmd in commands)
    assert any(cmd[:2] == ["git", "blame"] for cmd in commands)
    assert mock_run.call_count >= 3
    assert mock_analyze.called

    assert len(received) == 1
    diag = received[0]
    expected_summary = f"Diagnostics for plugin test_plugin at {source_file}:1"
    assert diag.summary == expected_summary
    assert (
        "Investigate compatibility issues in: sample_dep"
        in diag.actionable_recommendations
    )
    assert "skill_sample_skill_v1" in diag.actionable_recommendations
    assert diag.details is not None
    details = cast(dict[str, Any], diag.details)
    blame = details["blame"]
    assert blame["commit"] == "^123"
    assert blame["author"] == "user"
    assert blame["text"].startswith("^123")
    assert details["context"][0]["content"].strip() == "import sample_dep"
    assert details["dependencies"][0]["dependency"] == "sample_dep"
    assert details["recommended_skill"] == {
        "name": "sample_skill",
        "version": "1",
        "parameters": {"path": "str"},
    }


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_archaeologist_agent_uses_dependency_new_version(
    tmp_path: Path, event_type: str
) -> None:
    message_queue = MessageQueue()
    Archaeologist(message_queue)

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    source_file = tmp_path / "mod.py"
    source_file.write_text("import sample_dep\nsample_dep.old_func()\n")

    commands: list[list[str]] = []

    def fake_run(
        cmd: list[str], capture_output: bool = True, text: bool = True
    ) -> SimpleNamespace:
        commands.append(cmd)
        if cmd[:2] == ["git", "blame"]:
            return SimpleNamespace(stdout="^123 (user 2023-01-01 1) line\n", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    called_versions: list[str | None] = []

    def fake_fetch(package: str, version: str | None) -> str:
        called_versions.append(version)
        if version == "2.0":
            return "old_func removed"
        return ""

    with (
        patch.object(arch_module.subprocess, "run", side_effect=fake_run),
        patch.object(dep_module.metadata, "version", return_value="1.0"),
        patch.object(dep_module, "fetch_release_notes", side_effect=fake_fetch),
        patch.object(arch_module.LibrarianAgent, "find_skill", return_value=[]),
    ):
        payload = {
            "plugin": "test_plugin",
            "error_log": (
                "Traceback (most recent call last):\n"
                f'  File "{source_file}", line 2, in <module>'
            ),
            "dependencies": {"sample_dep": {"new_version": "2.0"}},
            "description": "dependency update",
            "issue_type": "dependency_update",
        }
        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert len(received) == 1
    assert received[0].details is not None
    details = cast(dict[str, Any], received[0].details)
    dep_analysis = details["dependencies"][0]
    assert called_versions == ["2.0"]
    assert dep_analysis["new_version"] == "2.0"
    assert any("sample_dep 2.0" in f for f in dep_analysis["findings"])
    assert all(cmd[0] != "git" for cmd in commands)
    assert details["recommended_skill"] is None


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_on_issue_detected_recommends_existing_skill(event_type: str) -> None:
    message_queue = MessageQueue()
    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    with patch.object(arch_module, "LibrarianAgent") as MockLib:
        MockLib.return_value.find_skill.return_value = [
            {"skill_name": "mock_low", "version": "1", "parameters": {}, "score": 0.2},
            {"skill_name": "mock_high", "version": "2", "parameters": {}, "score": 0.9},
        ]
        Archaeologist(message_queue)

        payload = {
            "plugin": "test_plugin",
            "issue_type": "bug",
            "error_log": "runtime error",
            "description": "runtime error",
        }
        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert len(received) == 1
    diag = received[0]
    assert "skill_mock_high_v2" in diag.actionable_recommendations
    assert diag.details is not None
    details = cast(dict[str, Any], diag.details)
    assert details["recommended_skill"] == {
        "name": "mock_high",
        "version": "2",
        "parameters": {},
    }
    assert details["skill_search"] == [
        {"skill_name": "mock_low", "version": "1", "parameters": {}, "score": 0.2},
        {"skill_name": "mock_high", "version": "2", "parameters": {}, "score": 0.9},
    ]


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_on_issue_detected_recommends_new_skill_when_none_found(
    event_type: str,
) -> None:
    message_queue = MessageQueue()
    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    with patch.object(arch_module, "LibrarianAgent") as MockLib:
        MockLib.return_value.find_skill.return_value = []
        Archaeologist(message_queue)

        payload = {
            "plugin": "test_plugin",
            "issue_type": "bug",
            "error_log": "runtime error",
            "description": "runtime error",
        }
        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert len(received) == 1
    diag = received[0]
    assert diag.actionable_recommendations == _("New skill development recommended.")
    assert diag.details is not None
    assert diag.details["recommended_skill"] is None


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_on_issue_detected_with_missing_index(
    event_type: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message_queue = MessageQueue()
    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    monkeypatch.setattr(
        "autogpt.skills.library.get_embedding", lambda _text, _cfg: [0.1, 0.2, 0.3]
    )
    storage = tmp_path / "skills"
    monkeypatch.setattr(
        "autogpt.skills.librarian.SkillLibrary",
        lambda config: library_module.SkillLibrary(config, storage_path=storage),
    )

    with patch.object(librarian_module.logger, "warn") as mock_warn:
        Archaeologist(message_queue, config=Config())
        mock_warn.assert_called_once()

    payload = {
        "plugin": "test_plugin",
        "issue_type": "bug",
        "error_log": "runtime error",
        "description": "runtime error",
    }
    message_queue.publish(
        EventMessage(event_type=event_type, payload=payload, source_agent="tester")
    )

    assert len(received) == 1
    diag = received[0]
    assert diag.actionable_recommendations == _("New skill development recommended.")
    assert diag.details is not None
    assert diag.details["recommended_skill"] is None


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_on_issue_detected_handles_skill_exception(event_type: str) -> None:
    message_queue = MessageQueue()
    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    with (
        patch.object(arch_module, "LibrarianAgent") as MockLib,
        patch.object(arch_module.logger, "error") as mock_error,
    ):
        MockLib.return_value.find_skill.side_effect = RuntimeError("boom")
        Archaeologist(message_queue)

        payload = {
            "plugin": "test_plugin",
            "issue_type": "bug",
            "error_log": "runtime error",
            "description": "runtime error",
        }
        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert len(received) == 1
    diag = received[0]
    assert diag.actionable_recommendations == _("New skill development recommended.")
    assert diag.details is not None
    assert diag.details["recommended_skill"] is None
    assert mock_error.called


def test_archaeologist_agent_respects_config_flag() -> None:
    message_queue = MessageQueue()
    with patch.object(arch_module, "LibrarianAgent") as MockLib:
        Archaeologist(message_queue, config=Config(use_librarian=False))
        assert not MockLib.called


@pytest.mark.parametrize("event_type", [ISSUE_DETECTED, TICKET_RECEIVED])
def test_on_issue_detected_publish_retry(event_type: str) -> None:
    message_queue = MessageQueue()
    Archaeologist(message_queue, config=Config(use_librarian=False))

    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    original_publish = message_queue.publish

    def publish_side_effect(event: EventMessage, call: list[int] = [0]) -> None:
        if call[0] == 0:
            call[0] += 1
            return original_publish(event)
        if call[0] == 1:
            call[0] += 1
            raise RuntimeError("boom")
        call[0] += 1
        return original_publish(event)

    with (
        patch.object(
            message_queue, "publish", side_effect=publish_side_effect
        ) as mock_publish,
        patch.object(arch_module.logger, "error") as mock_error,
    ):
        payload = {
            "plugin": "test_plugin",
            "issue_type": "bug",
            "error_log": "runtime error",
            "description": "runtime error",
        }
        message_queue.publish(
            EventMessage(event_type=event_type, payload=payload, source_agent="tester")
        )

    assert len(received) == 1
    assert mock_publish.call_count == 3
    mock_error.assert_called_once()
