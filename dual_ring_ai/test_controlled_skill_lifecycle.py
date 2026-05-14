import json
import subprocess
import sys
from pathlib import Path

from autoai.event_bus.message_types import EventMessage

from dual_ring_ai.core.event_bus import EventBus
from dual_ring_ai.core.event_bus import EventTypes
from dual_ring_ai.executor.execution_engine import ExecutionEngine
from dual_ring_ai.genesis.qa_agent import DEFAULT_QA_CONFIG, QAAgent
from dual_ring_ai.genesis.tdd_developer import DEFAULT_TDD_DEVELOPER_CONFIG, TDDDeveloperAgent


class FakeEventBus:
    def __init__(self):
        self.subscriptions = []
        self.published = []

    def subscribe(self, event_type, handler):
        self.subscriptions.append((event_type, handler))

    def publish(self, event_type, payload, source_agent, correlation_id=None):
        self.published.append(
            {
                "event_type": event_type,
                "payload": payload,
                "source_agent": source_agent,
                "correlation_id": correlation_id,
            }
        )


class FakeLibrarian:
    def __init__(self, paths=None):
        self.paths = paths or {}

    def get_source_code_path(self, name, item_type):
        return self.paths.get((item_type, name))


def write_skill(skill_dir: Path, name: str = "echo_skill", version: str = "1.0.0"):
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "main.py").write_text(
        """
import argparse
import json


def main(value="default"):
    return {"status": "success", "skill_name": "echo_skill", "value": value}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--value", default="default")
    args = parser.parse_args()
    print(json.dumps(main(args.value)))
""".lstrip(),
        encoding="utf-8",
    )
    (skill_dir / "test_main.py").write_text(
        """
from main import main


def test_echo_skill_returns_value():
    assert main("checked")["value"] == "checked"
""".lstrip(),
        encoding="utf-8",
    )
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "skill_name": name,
                "version": version,
                "description": "Echo a value",
                "security_policy": {
                    "network": False,
                    "shell": False,
                    "filesystem": {"read": ["."], "write": ["workspace"]},
                },
                "parameters": {
                    "value": {
                        "type": "string",
                        "required": False,
                        "description": "Value to echo",
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_execution_engine_runs_skill_without_shell(monkeypatch, tmp_path):
    skill_dir = tmp_path / "echo_skill"
    write_skill(skill_dir)
    event_bus = FakeEventBus()
    librarian = FakeLibrarian({("skill", "echo_skill"): str(skill_dir)})
    engine = ExecutionEngine(event_bus, librarian, {"execution_timeout": 10})

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"status": "success", "skill_name": "echo_skill"}),
            stderr="",
        )

    monkeypatch.setattr("dual_ring_ai.executor.execution_engine.subprocess.run", fake_run)

    result = engine._run_skill("echo_skill", {"value": "hello"})

    assert result["status"] == "success"
    assert captured["command"] == [
        sys.executable,
        str(skill_dir / "main.py"),
        "--value",
        "hello",
    ]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["cwd"] == str(skill_dir)


def test_event_bus_unwraps_dual_ring_payload():
    outer_message = EventMessage(
        event_type=EventTypes.SKILL_CREATED,
        payload={
            "event_type": EventTypes.SKILL_CREATED,
            "payload": {"skill_name": "echo_skill"},
            "source_agent": "skill_lifecycle_manager",
            "timestamp": "2026-05-01T00:00:00",
            "correlation_id": "corr-1",
        },
        source_agent=None,
        timestamp="ignored",
    )

    event = EventBus._coerce_event_message(outer_message)

    assert event.event_type == EventTypes.SKILL_CREATED
    assert event.payload == {"skill_name": "echo_skill"}
    assert event.source_agent == "skill_lifecycle_manager"
    assert event.timestamp == "2026-05-01T00:00:00"
    assert event.correlation_id == "corr-1"


def test_event_bus_dispatches_to_local_subscribers_without_redis(monkeypatch):
    monkeypatch.setattr("dual_ring_ai.core.event_bus.redis_publish", lambda *a, **k: None)
    monkeypatch.setattr("dual_ring_ai.core.event_bus.redis_subscribe", lambda *a, **k: None)

    event_bus = EventBus()
    event_bus._connected = True
    received = []

    event_bus.subscribe(EventTypes.SKILL_CREATED, received.append)
    event_bus.publish(
        EventTypes.SKILL_CREATED,
        {"skill_name": "local_skill"},
        "test_agent",
        correlation_id="corr-local",
    )

    assert len(received) == 1
    assert received[0].payload == {"skill_name": "local_skill"}
    assert received[0].source_agent == "test_agent"
    assert received[0].correlation_id == "corr-local"


def test_skill_lifecycle_validation_requires_complete_skill(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager

    proposal_dir = tmp_path / "incomplete"
    proposal_dir.mkdir()
    (proposal_dir / "main.py").write_text("def main(): return {}", encoding="utf-8")

    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )
    result = manager.validate_proposal(proposal_dir)

    assert result.passed is False
    assert result.missing_files == ["skill.json", "test_main.py"]


def test_skill_lifecycle_validates_with_pytest(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir)

    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )
    result = manager.validate_proposal(proposal_dir)

    assert result.passed is True
    assert result.metadata["skill_name"] == "echo_skill"
    assert result.pytest_return_code == 0


def test_skill_lifecycle_publishes_approved_skill(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir, name="echo_skill", version="2.0.0")
    event_bus = FakeEventBus()
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        event_bus,
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    published = manager.publish_approved_skill(
        proposal_dir,
        approved_by="architect",
        source_request_id="approval-123",
    )

    assert published.target_dir == tmp_path / "skill_library" / "echo_skill_2.0.0"
    assert (published.target_dir / "main.py").exists()
    lifecycle = json.loads((published.target_dir / "lifecycle.json").read_text())
    assert lifecycle["approved_by"] == "architect"
    assert lifecycle["source_request_id"] == "approval-123"
    assert event_bus.published[-1]["event_type"] == EventTypes.SKILL_CREATED
    assert event_bus.published[-1]["payload"]["skill_name"] == "echo_skill"


def test_qa_deploy_publishes_skill_without_git(monkeypatch, tmp_path):
    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir, name="qa_skill", version="1.0.0")
    event_bus = FakeEventBus()
    config = {
        **DEFAULT_QA_CONFIG,
        "skill_library_path": str(tmp_path / "skill_library"),
        "skill_lifecycle_audit_path": str(tmp_path / "logs" / "audit.jsonl"),
    }
    qa = QAAgent(event_bus, FakeLibrarian(), config)

    original_run = subprocess.run

    def fail_on_git(command, *args, **kwargs):
        if command and command[0] == "git":
            raise AssertionError("QA deployment must not call git subprocess commands")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr("dual_ring_ai.genesis.qa_agent.subprocess.run", fail_on_git)

    qa._deploy_approved_fix(str(proposal_dir), approved_by="architect")

    event_types = [event["event_type"] for event in event_bus.published]
    assert EventTypes.SKILL_CREATED in event_types
    assert EventTypes.ISSUE_RESOLVED in event_types
    assert (tmp_path / "skill_library" / "qa_skill_1.0.0").exists()


def test_tdd_developer_proposes_validated_skill_directory_without_git(
    monkeypatch, tmp_path
):
    event_bus = FakeEventBus()
    config = {
        **DEFAULT_TDD_DEVELOPER_CONFIG,
        "workspace_path": str(tmp_path / "workspace"),
    }
    developer = TDDDeveloperAgent(event_bus, FakeLibrarian(), config)

    original_run = subprocess.run

    def fail_on_git(command, *args, **kwargs):
        if command and command[0] == "git":
            raise AssertionError("TDD developer must not create git branches for skills")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr("dual_ring_ai.genesis.tdd_developer.subprocess.run", fail_on_git)

    skill_dir = tmp_path / "workspace" / "generated_skill"
    developer._publish_code_fix_proposed(
        "generated_skill",
        skill_dir,
        {"issue_type": "capability_gap"},
    )

    proposed_events = [
        event
        for event in event_bus.published
        if event["event_type"] == EventTypes.CODE_FIX_PROPOSED
    ]
    assert proposed_events
    payload = proposed_events[-1]["payload"]
    assert payload["skill_name"] == "generated_skill"
    assert payload["proposal_path"] == str(skill_dir)
