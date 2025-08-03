from pathlib import Path
from typing import Any

import yaml

from autogpt.self_improve import DatabaseManager, PatchAgent
from autogpt.self_improve.plugin_processor import handle_plugin_todo
from autogpt.self_improve.plugin_todo_queue import PluginTodo


def test_handle_plugin_todo(tmp_path: Path, monkeypatch: Any) -> None:
    db = DatabaseManager(tmp_path / "improvement.db")
    patch_agent = PatchAgent(db=db)

    file_path = tmp_path / "target.py"
    file_path.write_text("def foo() -> int:\n    return 1\n")

    prompt_file = tmp_path / "prompt_settings.yaml"
    prompt_file.write_text("constraints: []\n")

    diff = (
        "--- target.py\n"
        "+++ target.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def foo() -> int:\n"
        "-    return 1\n"
        "+    return 2\n"
    )

    verify_calls: list[list[Path]] = []

    def spy_verify(files: list[Path]) -> None:  # type: ignore[override]
        verify_calls.append(list(files))

    patch_agent.verify = spy_verify  # type: ignore[assignment]

    monkeypatch.setattr(
        "autogpt.self_improve.plugin_processor.generate_diff", lambda context: diff
    )

    todo = PluginTodo(gap="test-gap", context="ctx", goal="goal")
    handle_plugin_todo(todo, patch_agent, db, tmp_path)

    assert file_path.read_text() == "def foo() -> int:\n    return 2\n"
    assert verify_calls, "PatchAgent.verify was not called"

    incoming = tmp_path / "evolve_strategies" / "population" / "incoming"
    exported = list(incoming.glob("selfmod_*.yaml"))
    assert exported, "Prompt config was not exported"
    assert yaml.safe_load(exported[0].read_text()) == yaml.safe_load(
        prompt_file.read_text()
    )


def test_handle_plugin_todo_export_failure(tmp_path: Path, monkeypatch: Any) -> None:
    db = DatabaseManager(tmp_path / "improvement.db")
    patch_agent = PatchAgent(db=db)

    file_path = tmp_path / "target.py"
    file_path.write_text("def foo() -> int:\n    return 1\n")

    prompt_file = tmp_path / "prompt_settings.yaml"
    prompt_file.write_text("constraints: []\n")

    diff = (
        "--- target.py\n"
        "+++ target.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def foo() -> int:\n"
        "-    return 1\n"
        "+    return 2\n"
    )

    verify_calls: list[list[Path]] = []

    def spy_verify(files: list[Path]) -> None:  # type: ignore[override]
        verify_calls.append(list(files))

    patch_agent.verify = spy_verify  # type: ignore[assignment]

    monkeypatch.setattr(
        "autogpt.self_improve.plugin_processor.generate_diff", lambda context: diff
    )

    def fail_dump(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("dump fail")

    monkeypatch.setattr("autogpt.self_improve.yaml_exporter.yaml.safe_dump", fail_dump)

    todo = PluginTodo(gap="test-gap", context="ctx", goal="goal")
    handle_plugin_todo(todo, patch_agent, db, tmp_path)

    assert file_path.read_text() == "def foo() -> int:\n    return 2\n"
    assert verify_calls, "PatchAgent.verify was not called"
    incoming = tmp_path / "evolve_strategies" / "population" / "incoming"
    exported = list(incoming.glob("selfmod_*.yaml"))
    assert exported and exported[0].read_text() == ""
