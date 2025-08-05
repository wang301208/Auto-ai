from __future__ import annotations

from pathlib import Path

from autogpt.agents.tdd_developer import TDDDeveloper
from autogpt.event_bus import (
    CODE_FIX_PROPOSED,
    DIAGNOSIS_COMPLETE,
    EventMessage,
    MessageQueue,
)


class FakeLibrarian:
    def add_skill(self, *args, **kwargs):
        pass


def test_tdd_developer_uses_recommended_skill(agent, workspace, monkeypatch):
    mq = MessageQueue()
    events: list[EventMessage] = []
    mq.subscribe(CODE_FIX_PROPOSED, lambda msg: events.append(msg))

    developer = TDDDeveloper(agent=agent, message_queue=mq, librarian=FakeLibrarian())

    monkeypatch.setattr(
        "autogpt.agents.tdd_developer.git_create_branch", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "autogpt.agents.tdd_developer.git_checkout", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "autogpt.agents.tdd_developer.git_commit", lambda *a, **k: None
    )

    repo_path = str(agent.workspace.root)
    run_results: list[dict] = []

    from autogpt.agents import tdd_developer as tdd_module

    original_run_tests = tdd_module.run_tests

    def capture_run_tests(path: str, agent) -> dict:
        import sys
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)
        result = original_run_tests(path, agent)
        run_results.append(result)
        return result

    monkeypatch.setattr(tdd_module, "run_tests", capture_run_tests)

    scripts_dir = Path(repo_path) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "__init__.py").write_text("", encoding="utf-8")
    skill_dir = Path(repo_path) / "skill_library" / "demo_1.0"
    skill_dir.mkdir(parents=True)
    (skill_dir / "main.py").write_text("def run():\n    return 'ok'\n", encoding="utf-8")

    payload = {
        "issue_id": "42",
        "repo_path": repo_path,
        "details": {
            "recommended_skill": {"name": "demo", "version": "1.0", "parameters": {}}
        },
    }

    mq.publish(
        EventMessage(
            event_type=DIAGNOSIS_COMPLETE,
            payload=payload,
            source_agent="tester",
        )
    )

    script_path = Path(repo_path) / "scripts" / "use_demo.py"
    assert script_path.is_file()
    assert run_results and run_results[0]["exit_code"] == 0
    assert events and events[0].event_type == CODE_FIX_PROPOSED
