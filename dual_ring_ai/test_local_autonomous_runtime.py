import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from dual_ring_ai.core.event_bus import EventTypes
from dual_ring_ai.test_controlled_skill_lifecycle import FakeEventBus, write_skill


def test_governance_store_persists_approval_decisions(tmp_path):
    from dual_ring_ai.core.governance import GovernanceStore

    store = GovernanceStore(tmp_path / "governance")
    request = store.create_request(
        request_type="skill_publish",
        title="Publish skill",
        payload={"skill_name": "echo_skill"},
        requested_by="qa_agent",
        risk_level="medium",
    )

    assert request.status == "pending"
    approved = store.decide(request.request_id, "approved", "architect", "looks safe")
    reloaded = GovernanceStore(tmp_path / "governance").get_request(request.request_id)

    assert approved.status == "approved"
    assert reloaded.status == "approved"
    assert reloaded.decided_by == "architect"
    assert store.list_requests(status="approved")[0].request_id == request.request_id


def test_permission_gate_blocks_policy_violations():
    from dual_ring_ai.core.governance import PermissionGate
    from dual_ring_ai.core.skill_lifecycle import SandboxPolicy

    gate = PermissionGate()
    policy = SandboxPolicy(
        network=False,
        shell=False,
        filesystem={"read": ["."], "write": ["workspace"]},
    )

    denied_network = gate.evaluate(policy, "network", {"host": "example.com"})
    denied_shell = gate.evaluate(policy, "shell", {"command": "dir"})
    denied_write = gate.evaluate(policy, "filesystem.write", {"path": "C:/Users"})
    allowed_write = gate.evaluate(policy, "filesystem.write", {"path": "workspace/out.txt"})

    assert denied_network.allowed is False
    assert denied_shell.allowed is False
    assert denied_write.allowed is False
    assert allowed_write.allowed is True


def test_sandbox_runner_runs_skill_within_workspace(tmp_path):
    from dual_ring_ai.core.sandbox_runner import SandboxRunner
    from dual_ring_ai.core.skill_lifecycle import SandboxPolicy

    skill_dir = tmp_path / "skill"
    write_skill(skill_dir)
    workspace = tmp_path / "workspace"
    runner = SandboxRunner(workspace)
    policy = SandboxPolicy(
        network=False,
        shell=False,
        filesystem={"read": ["."], "write": ["workspace"]},
    )

    result = runner.run_skill(skill_dir, {"value": "checked"}, policy, timeout=10)

    assert result.return_code == 0
    assert result.output["value"] == "checked"
    assert result.command == [
        sys.executable,
        str(skill_dir / "main.py"),
        "--value",
        "checked",
    ]
    assert result.workspace == workspace


def test_sandbox_runner_rejects_unsafe_policy(tmp_path):
    from dual_ring_ai.core.sandbox_runner import SandboxRunner
    from dual_ring_ai.core.skill_lifecycle import SandboxPolicy

    skill_dir = tmp_path / "skill"
    write_skill(skill_dir)
    runner = SandboxRunner(tmp_path / "workspace")
    policy = SandboxPolicy(
        network=True,
        shell=False,
        filesystem={"read": ["."], "write": ["workspace"]},
    )

    result = runner.run_skill(skill_dir, {"value": "blocked"}, policy, timeout=10)

    assert result.return_code == 126
    assert result.output["status"] == "blocked"
    assert "network access is not allowed" in result.stderr


def test_algorithm_experiment_recommends_candidate_only_when_thresholds_pass(tmp_path):
    from dual_ring_ai.core.algorithm_experiment import (
        AlgorithmExperimentRunner,
        ExperimentSpec,
    )

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "incident-1",
                    "baseline": {"f1_score": 0.70, "latency_ms": 130},
                    "candidate": {"f1_score": 0.82, "latency_ms": 100},
                },
                {
                    "case_id": "incident-2",
                    "baseline": {"f1_score": 0.75, "latency_ms": 120},
                    "candidate": {"f1_score": 0.86, "latency_ms": 105},
                },
            ]
        ),
        encoding="utf-8",
    )
    runner = AlgorithmExperimentRunner(tmp_path / "experiments")
    spec = ExperimentSpec(
        proposal_id="aep-1",
        baseline_engine="diagnostics_engine:1.0.0",
        candidate_engine="causal_graph_engine:0.1.0",
        dataset_path=dataset_path,
        thresholds={"f1_score": 0.05, "latency_ms": -10},
    )

    report = runner.run(spec)

    assert report.recommendation == "promote_candidate"
    assert report.metric_deltas["f1_score"] > 0.05
    assert report.metric_deltas["latency_ms"] < -10
    assert report.report_path.exists()


def test_local_runtime_exposes_core_services(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntimeConfig, LocalRuntime

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            enable_agents=False,
        )
    )
    runtime.start()
    snapshot = runtime.status_snapshot()

    assert snapshot["running"] is True
    assert snapshot["services"]["governance"] == "ready"
    assert snapshot["services"]["skill_lifecycle"] == "ready"
    assert snapshot["services"]["algorithm_registry"] == "ready"
    assert snapshot["paths"]["root_path"] == str(tmp_path)

    runtime.stop()
    assert runtime.status_snapshot()["running"] is False


def test_cockpit_api_lists_and_decides_approvals(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    runtime.start()
    request = runtime.governance.create_request(
        request_type="algorithm_research",
        title="Try new diagnostics engine",
        payload={"proposal_id": "aep-1"},
        requested_by="algorithmist_agent",
        risk_level="high",
    )
    app = create_cockpit_app(runtime)
    client = TestClient(app)

    status_response = client.get("/status")
    approvals_response = client.get("/approvals")
    decision_response = client.post(
        f"/approvals/{request.request_id}/decision",
        json={"decision": "approved", "decided_by": "architect", "comments": "ok"},
    )

    assert status_response.status_code == 200
    assert status_response.json()["running"] is True
    assert approvals_response.status_code == 200
    assert approvals_response.json()[0]["request_id"] == request.request_id
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"
