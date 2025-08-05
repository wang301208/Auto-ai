from types import SimpleNamespace

from autogpt.agents.archaeologist import Archaeologist
from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    ISSUE_DETECTED,
    DiagnosisComplete,
    EventMessage,
    MessageQueue,
)


def test_archaeologist_recommends_skill_without_git_ops(monkeypatch):
    mq = MessageQueue()
    received = []
    schemas = []

    def handler(msg: DiagnosisComplete) -> None:
        received.append(msg)
        rec = msg.details["recommended_skill"]
        if rec:
            schemas.append(rec["parameters"])

    mq.subscribe(DIAGNOSIS_COMPLETE, handler)

    class FakeLibrarian:
        def find_skill(self, query: str, top_k: int = 3):
            return [
                {
                    "skill_name": "sample_skill",
                    "version": "1",
                    "parameters": {"path": "str"},
                }
            ]

    Archaeologist(mq, librarian=FakeLibrarian())

    monkeypatch.setattr(
        "autogpt.agents.archaeologist.analyze_dependency",
        lambda dep, src, new_version=None: {
            "dependency": dep,
            "version": None,
            "new_version": new_version,
            "usages": [],
            "release_notes": None,
            "findings": [],
        },
    )

    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr("autogpt.agents.archaeologist.subprocess.run", fake_run)

    payload = {
        "plugin": "example_plugin",
        "issue_type": "bug",
        "description": "failing function",
    }
    mq.publish(
        EventMessage(
            event_type=ISSUE_DETECTED,
            payload=payload,
            source_agent="tester",
        )
    )

    assert calls == []
    assert len(received) == 1
    assert schemas == [{"path": "str"}]
    diag = received[0]
    assert diag.details["recommended_skill"] == {
        "name": "sample_skill",
        "version": "1",
        "parameters": {"path": "str"},
    }
    assert "skill_sample_skill_v1" in diag.actionable_recommendations
