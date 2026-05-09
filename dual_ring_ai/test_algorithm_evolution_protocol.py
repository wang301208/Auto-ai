import json

import pytest
from fastapi.testclient import TestClient

from dual_ring_ai.core.agent_blueprint import AgentBlueprint, ThinkingEngineRef
from dual_ring_ai.core.algorithm_registry import AlgorithmManifest
from dual_ring_ai.core.event_bus import EventTypes
from dual_ring_ai.genesis.algorithmist import AlgorithmistAgent


def test_algorithm_evolution_requires_approval_before_experiment_and_blueprint_upgrade(
    tmp_path,
):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    runtime.start()

    blueprint_path = tmp_path / "charter" / "archaeologist.yaml"
    blueprint_path.parent.mkdir(parents=True)
    AgentBlueprint(
        role_name="Archaeologist",
        version="1.0",
        agent_class="dual_ring_ai.genesis.archaeologist.ArchaeologistAgent",
        thinking_engine=ThinkingEngineRef(
            name="diagnostics_engine",
            version="1.0.0",
            evaluation_suite="diagnostics_v1",
        ),
        authorized_plugins=["Plugin_LogReader"],
        subscribed_events=[EventTypes.ISSUE_DETECTED],
        config={},
    ).save(blueprint_path)

    runtime.algorithm_registry.register(
        AlgorithmManifest(
            name="diagnostics_engine",
            version="2.0.0",
            description="Causal graph diagnostics engine",
            source_module="dual_ring_ai.algorithms.diagnostics_v2",
            status="candidate",
            metrics={"f1_score": 0.84, "latency_ms": 92},
            rollback_to="1.0.0",
            evaluation_suite="diagnostics_v1",
        )
    )

    algorithmist = AlgorithmistAgent(runtime.event_bus, tmp_path / "workspace")
    proposal = algorithmist.propose_research(
        target_agent="Archaeologist",
        current_engine="diagnostics_engine:1.0.0",
        candidate_engine="diagnostics_engine:2.0.0",
        bottleneck="Concurrent incident diagnosis loses accuracy.",
        hypothesis="A causal graph engine improves multi-fault diagnosis.",
        experiment_design="Replay historical incident cases and compare averages.",
        metrics=["f1_score", "latency_ms"],
    )

    research_request = runtime.create_algorithm_research_request(
        tmp_path
        / "workspace"
        / "algorithm_research_proposals"
        / f"{proposal.proposal_id}.json",
        requested_by="algorithmist_agent",
    )

    dataset_path = tmp_path / "diagnostics_dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "baseline": {"f1_score": 0.70, "latency_ms": 140},
                    "candidate": {"f1_score": 0.85, "latency_ms": 100},
                },
                {
                    "baseline": {"f1_score": 0.72, "latency_ms": 130},
                    "candidate": {"f1_score": 0.86, "latency_ms": 96},
                },
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(PermissionError):
        runtime.run_algorithm_experiment_from_approval(
            research_request.request_id,
            dataset_path,
            thresholds={"f1_score": 0.05, "latency_ms": -10},
        )

    runtime.governance.decide(research_request.request_id, "approved", "architect")
    report = runtime.run_algorithm_experiment_from_approval(
        research_request.request_id,
        dataset_path,
        thresholds={"f1_score": 0.05, "latency_ms": -10},
    )

    assert report.recommendation == "promote_candidate"

    promotion_request = runtime.create_algorithm_promotion_request(
        report.report_path,
        blueprint_path,
        requested_by="algorithmist_agent",
    )

    with pytest.raises(PermissionError):
        runtime.apply_algorithm_promotion_from_approval(
            promotion_request.request_id,
            approved_by="architect",
        )

    runtime.governance.decide(promotion_request.request_id, "approved", "architect")
    updated_blueprint = runtime.apply_algorithm_promotion_from_approval(
        promotion_request.request_id,
        approved_by="architect",
    )

    reloaded = AgentBlueprint.load(blueprint_path)
    assert updated_blueprint.thinking_engine.name == "diagnostics_engine"
    assert updated_blueprint.thinking_engine.version == "2.0.0"
    assert reloaded.thinking_engine.version == "2.0.0"

    events = runtime.event_bus.list_events(EventTypes.ALGORITHM_PROMOTED)
    assert events[-1].payload["target_agent"] == "Archaeologist"
    assert runtime.read_algorithm_evolution_audit()[-1]["action"] == "apply_promotion"


def test_cockpit_api_exposes_algorithm_evolution_audit(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    runtime.start()
    runtime.algorithm_evolution.record_audit(
        "manual_check",
        {"proposal_id": "aep-1", "status": "reviewed"},
    )

    client = TestClient(create_cockpit_app(runtime))
    response = client.get("/audit/algorithm-evolution")

    assert response.status_code == 200
    assert response.json()[0]["action"] == "manual_check"
