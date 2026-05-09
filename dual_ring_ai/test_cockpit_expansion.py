import json

from fastapi.testclient import TestClient

from dual_ring_ai.core.algorithm_experiment import ExperimentSpec
from dual_ring_ai.core.algorithm_registry import AlgorithmManifest
from dual_ring_ai.core.event_bus import EventTypes
from dual_ring_ai.test_controlled_skill_lifecycle import write_skill


def test_cockpit_api_exposes_events_skills_audit_and_experiment_reports(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    runtime.start()

    proposal_dir = tmp_path / "workspace" / "skill_proposals" / "echo_skill"
    write_skill(proposal_dir, name="echo_skill", version="4.0.0")
    request = runtime.create_skill_publication_request(
        proposal_dir,
        requested_by="tdd_developer",
        title="Publish echo skill",
    )
    runtime.governance.decide(request.request_id, "approved", "architect")
    runtime.publish_skill_from_approval(request.request_id, approved_by="architect")

    runtime.algorithm_registry.register(
        AlgorithmManifest(
            name="diagnostics_engine",
            version="1.0.0",
            description="Baseline diagnostics",
            source_module="dual_ring_ai.algorithms.diagnostics",
            status="active",
            metrics={"f1_score": 0.75},
            rollback_to=None,
            evaluation_suite="diagnostics_v1",
        )
    )
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "baseline": {"f1_score": 0.70},
                    "candidate": {"f1_score": 0.80},
                }
            ]
        ),
        encoding="utf-8",
    )
    runtime.algorithm_experiments.run(
        ExperimentSpec(
            proposal_id="proposal-1",
            baseline_engine="diagnostics_engine:1.0.0",
            candidate_engine="diagnostics_engine:1.1.0",
            dataset_path=dataset_path,
            thresholds={"f1_score": 0.05},
        )
    )

    client = TestClient(create_cockpit_app(runtime))

    events_response = client.get(f"/events?event_type={EventTypes.SKILL_CREATED}")
    skills_response = client.get("/skills")
    audit_response = client.get("/audit/skill-lifecycle")
    algorithms_response = client.get("/algorithms")
    reports_response = client.get("/algorithm-experiments")
    root_response = client.get("/")

    assert events_response.status_code == 200
    assert events_response.json()[-1]["payload"]["skill_name"] == "echo_skill"
    assert skills_response.status_code == 200
    assert skills_response.json()[0]["skill_name"] == "echo_skill"
    assert audit_response.status_code == 200
    assert audit_response.json()[-1]["action"] == "publish_approved_skill"
    assert algorithms_response.status_code == 200
    assert algorithms_response.json()[0]["name"] == "diagnostics_engine"
    assert reports_response.status_code == 200
    assert reports_response.json()[0]["proposal_id"] == "proposal-1"
    assert root_response.status_code == 404
