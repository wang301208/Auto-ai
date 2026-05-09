import json

from fastapi.testclient import TestClient

from dual_ring_ai.core.agent_blueprint import AgentBlueprint, ThinkingEngineRef


def make_blueprint(role_name):
    return AgentBlueprint(
        role_name=role_name,
        version="1.0",
        agent_class="dual_ring_ai.genesis.tdd_developer.TDDDeveloperAgent",
        thinking_engine=ThinkingEngineRef(
            name="thought_tree_reasoner",
            version="1.0.0",
            evaluation_suite="planning_v1",
        ),
        core_prompt=f"{role_name} prompt",
        authorized_plugins=["Plugin_FileIO"],
        subscribed_events=["DIAGNOSIS_COMPLETE"],
        config={"max_parallel_tasks": 1},
    )


def test_runtime_health_report_includes_adapter_matrix_and_security_posture(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            adapters={
                "docker_sandbox": {"enabled": True, "dry_run": True},
                "ollama": {"enabled": True, "dry_run": True},
                "remote_llm": {"enabled": True, "dry_run": True},
                "whisper": {"enabled": True, "dry_run": True},
                "xtts": {"enabled": True, "dry_run": True},
            },
        )
    )

    health = runtime.health_report()

    assert health["runtime"]["running"] is False
    assert health["security"]["network"] is True
    assert health["security"]["shell"] is True
    assert health["adapters"]["ollama"]["status"] == "dry_run"
    assert health["adapters"]["remote_llm"]["status"] == "dry_run"
    assert health["adapters"]["docker_sandbox"]["status"] == "dry_run"
    assert health["adapters"]["whisper"]["status"] == "dry_run"
    assert health["adapters"]["xtts"]["status"] == "dry_run"


def test_runtime_lists_blueprints_and_rolls_back_applied_organization_change(tmp_path):
    from dual_ring_ai.genesis.founder import FounderAgent
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    charter_path = tmp_path / "charter"
    charter_path.mkdir()
    make_blueprint("TDD_Developer").save(charter_path / "tdd_developer.yaml")
    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path / "runtime",
            managed_paths={"organizational_charter": str(charter_path)},
        )
    )
    founder = FounderAgent(runtime.event_bus, charter_path)
    proposal = founder.propose_frontend_developer("Need frontend specialist.")
    request = runtime.create_organization_change_request(
        proposal.proposal_path,
        requested_by="founder_agent",
    )
    runtime.governance.decide(request.request_id, "approved", "architect")
    applied = runtime.apply_organization_change_from_approval(
        request.request_id,
        approved_by="architect",
    )

    listed = runtime.list_agent_blueprints()
    rollback = runtime.rollback_organization_change(
        applied.role_name,
        requested_by="architect",
        reason="rollback test",
    )

    assert {item["role_name"] for item in listed} == {
        "TDD_Developer",
        "Frontend_Developer",
    }
    assert rollback["status"] == "rolled_back"
    assert rollback["role_name"] == "Frontend_Developer"
    assert not (charter_path / "frontend_developer.yaml").exists()
    assert "Frontend_Developer" not in runtime.blueprint_orchestrator.reload_changed()
    assert runtime.event_bus.list_events("ORGANIZATION_CHANGE_ROLLED_BACK")


def test_cockpit_exposes_health_adapters_blueprints_and_rollback(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    charter_path = tmp_path / "charter"
    charter_path.mkdir()
    make_blueprint("Frontend_Developer").save(charter_path / "frontend_developer.yaml")
    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path / "runtime",
            managed_paths={"organizational_charter": str(charter_path)},
        )
    )
    client = TestClient(create_cockpit_app(runtime))

    health = client.get("/health")
    adapters = client.get("/adapters")
    blueprints = client.get("/blueprints")
    rollback = client.post(
        "/blueprints/Frontend_Developer/rollback",
        json={"requested_by": "architect", "reason": "remove duplicate"},
    )

    assert health.status_code == 200
    assert adapters.status_code == 200
    assert "ollama" in adapters.json()
    assert blueprints.status_code == 200
    assert blueprints.json()[0]["role_name"] == "Frontend_Developer"
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"


def test_terminal_ui_status_replaces_desktop_shell_readiness(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))

    assert runtime.terminal_ui_status()["status"] == "ready"
