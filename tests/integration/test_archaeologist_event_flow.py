from types import SimpleNamespace

import pytest

from autogpt.agents.archaeologist import Archaeologist
from autogpt.config import Config
from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    ISSUE_DETECTED,
    EventMessage,
    MessageQueue,
)


@pytest.mark.parametrize("use_librarian", [True, False])
def test_archaeologist_recommends_skill_without_git_ops(monkeypatch, use_librarian):
    mq = MessageQueue()
    received = []
    mq.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    class FakeLibrarian:
        def find_skill(self, query: str, top_k: int = 3):
            return [
                {
                    "skill_name": "sample_low",
                    "version": "1",
                    "parameters": {"path": "str"},
                    "score": 0.1,
                    "description": "Low scoring skill",
                },
                {
                    "skill_name": "sample_high",
                    "version": "2",
                    "parameters": {"path": "str"},
                    "score": 0.9,
                    "description": "High scoring skill",
                },
            ]

    Archaeologist(
        mq, librarian=FakeLibrarian(), config=Config(use_librarian=use_librarian)
    )

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
    diag = received[0]
    if use_librarian:
        assert diag.details["recommended_skill"] == {
            "name": "sample_high",
            "version": "2",
            "parameters": {"path": "str"},
        }
        assert diag.details["skill_search"] == [
            {
                "skill_name": "sample_low",
                "version": "1",
                "parameters": {"path": "str"},
                "score": 0.1,
                "description": "Low scoring skill",
            },
            {
                "skill_name": "sample_high",
                "version": "2",
                "parameters": {"path": "str"},
                "score": 0.9,
                "description": "High scoring skill",
            },
        ]
        assert "skill_sample_high_v2" in diag.actionable_recommendations
        assert "High scoring skill" in diag.actionable_recommendations
    else:
        assert diag.details["recommended_skill"] is None
        assert "skill_sample_high_v2" not in diag.actionable_recommendations
