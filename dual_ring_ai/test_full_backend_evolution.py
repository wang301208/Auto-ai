import json
from pathlib import Path

import pytest
import yaml

from dual_ring_ai.core.event_bus import EventTypes
from dual_ring_ai.test_controlled_skill_lifecycle import FakeEventBus, write_skill


def update_skill_policy(skill_dir: Path, policy: dict):
    metadata_path = skill_dir / "skill.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["security_policy"] = policy
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def test_skill_validation_requires_security_policy(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir)
    metadata_path = proposal_dir / "skill.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("security_policy", None)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    result = manager.validate_proposal(proposal_dir)

    assert result.passed is False
    assert "security_policy is required" in result.output


def test_skill_validation_rejects_unsafe_policy(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir)
    update_skill_policy(
        proposal_dir,
        {
            "network": True,
            "shell": True,
            "filesystem": {"read": ["."], "write": ["C:/Users"]},
        },
    )
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    result = manager.validate_proposal(proposal_dir)

    assert result.passed is False
    assert "network access is not allowed" in result.output
    assert "shell access is not allowed" in result.output
    assert "write path outside workspace" in result.output


def test_skill_publication_records_policy_and_audit_log(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir, name="policy_skill", version="1.2.0")
    update_skill_policy(
        proposal_dir,
        {
            "network": False,
            "shell": False,
            "filesystem": {"read": ["."], "write": ["workspace"]},
        },
    )
    audit_path = tmp_path / "logs" / "audit.jsonl"
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=audit_path,
    )

    published = manager.publish_approved_skill(
        proposal_dir,
        approved_by="architect",
        source_request_id="req-1",
    )

    lifecycle = json.loads((published.target_dir / "lifecycle.json").read_text())
    assert lifecycle["security_policy"]["network"] is False
    audit_entries = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [entry["action"] for entry in audit_entries] == [
        "validate_proposal",
        "publish_approved_skill",
    ]
    assert audit_entries[-1]["result"] == "success"
    assert audit_entries[-1]["skill_name"] == "policy_skill"


def test_algorithm_registry_registers_versioned_algorithm(tmp_path):
    from dual_ring_ai.core.algorithm_registry import AlgorithmManifest, AlgorithmRegistry

    registry = AlgorithmRegistry(tmp_path / "algorithm_library")
    manifest = AlgorithmManifest(
        name="diagnostics_engine",
        version="1.0.0",
        description="Baseline diagnostics engine",
        source_module="algorithm_library.diagnostics_engine_v1",
        status="candidate",
        metrics={"accuracy": 0.82, "latency_ms": 120},
        rollback_to=None,
        evaluation_suite="diagnostics_v1",
    )

    saved = registry.register(manifest)
    loaded = registry.get("diagnostics_engine", "1.0.0")

    assert saved == tmp_path / "algorithm_library" / "diagnostics_engine_1.0.0"
    assert loaded == manifest
    assert registry.list_algorithms()[0].name == "diagnostics_engine"


def test_algorithmist_creates_research_proposal_event(tmp_path):
    from dual_ring_ai.genesis.algorithmist import AlgorithmistAgent

    event_bus = FakeEventBus()
    algorithmist = AlgorithmistAgent(event_bus, workspace_path=tmp_path)

    proposal = algorithmist.propose_research(
        target_agent="Archaeologist",
        current_engine="diagnostics_engine:1.0.0",
        candidate_engine="causal_graph_engine:0.1.0",
        bottleneck="Accuracy drops below 70% on concurrent faults",
        hypothesis="A causal graph engine should model concurrent causes more directly.",
        experiment_design="Replay historical incident bundles and compare F1 and latency.",
        metrics=["f1_score", "latency_ms", "token_cost"],
    )

    assert proposal.requires_human_approval is True
    assert proposal.status == "proposed"
    event = next(
        event
        for event in event_bus.published
        if event["event_type"] == EventTypes.ALGORITHM_RESEARCH_PROPOSED
    )
    assert event["event_type"] == EventTypes.ALGORITHM_RESEARCH_PROPOSED
    assert event["payload"]["target_agent"] == "Archaeologist"
    assert event["payload"]["metrics"] == ["f1_score", "latency_ms", "token_cost"]


def test_agent_blueprint_round_trips_thinking_engine(tmp_path):
    from dual_ring_ai.core.agent_blueprint import AgentBlueprint

    blueprint_path = tmp_path / "archaeologist.yaml"
    blueprint_path.write_text(
        yaml.safe_dump(
            {
                "role_name": "Archaeologist",
                "version": "2.0",
                "agent_class": "dual_ring_ai.genesis.archaeologist.ArchaeologistAgent",
                "thinking_engine": {
                    "name": "diagnostics_engine",
                    "version": "1.0.0",
                    "evaluation_suite": "diagnostics_v1",
                },
                "authorized_plugins": ["Plugin_FileIO"],
                "subscribed_events": ["ISSUE_DETECTED"],
                "config": {"workspace_path": "workspace/archaeologist"},
            }
        ),
        encoding="utf-8",
    )

    blueprint = AgentBlueprint.load(blueprint_path)
    output_path = tmp_path / "copy.yaml"
    blueprint.save(output_path)
    reloaded = AgentBlueprint.load(output_path)

    assert reloaded.role_name == "Archaeologist"
    assert reloaded.thinking_engine.name == "diagnostics_engine"
    assert reloaded.thinking_engine.version == "1.0.0"
    assert reloaded.thinking_engine.evaluation_suite == "diagnostics_v1"
