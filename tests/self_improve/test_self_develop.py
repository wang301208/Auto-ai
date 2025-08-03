from pathlib import Path
from typing import Any

from autogpt.event_bus import EventBus
from autogpt.self_improve import (
    DatabaseManager,
    PatchAgent,
    PluginTodoQueue,
    SelfDevelopManager,
)


def test_self_develop_processes_plugin_todo(tmp_path: Path, monkeypatch: Any) -> None:
    db = DatabaseManager(tmp_path / "improvement.db")
    event_bus = EventBus(tmp_path / "events.db")
    plugin_queue = PluginTodoQueue(tmp_path / "todo.json", event_bus)
    patch_agent = PatchAgent(db=db)

    file_path = tmp_path / "target.py"
    file_path.write_text("def foo() -> int:\n    return 1\n")

    diff = (
        "--- target.py\n"
        "+++ target.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def foo() -> int:\n"
        "-    return 1\n"
        "+    return 2\n"
    )

    verify_calls: list[list[Path]] = []
    orig_verify = patch_agent.verify

    def spy_verify(files: list[Path]) -> None:  # type: ignore[override]
        verify_calls.append(list(files))
        return orig_verify(files)

    patch_agent.verify = spy_verify  # type: ignore[assignment]

    monkeypatch.setattr(
        "autogpt.self_improve.self_develop.generate_diff", lambda context: diff
    )

    plugin_queue.record_failure("gap", "ctx", "goal", threshold=1)

    mgr = SelfDevelopManager(
        plugin_queue=plugin_queue,
        patch_agent=patch_agent,
        db=db,
        event_bus=event_bus,
        workspace=tmp_path,
    )
    mgr.review_repository()

    assert file_path.read_text() == "def foo() -> int:\n    return 2\n"
    assert verify_calls, "PatchAgent.verify was not called"
