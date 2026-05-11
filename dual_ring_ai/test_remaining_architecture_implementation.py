import json

from fastapi.testclient import TestClient

from dual_ring_ai.core.agent_blueprint import AgentBlueprint, ThinkingEngineRef


def test_runtime_config_loads_managed_paths_and_adapters(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime

    config_path = tmp_path / "runtime.json"
    config_path.write_text(
        json.dumps(
            {
                "root_path": str(tmp_path / "runtime"),
                "enable_agents": False,
                "cockpit": {"host": "127.0.0.1", "port": 8765},
                "managed_paths": {
                    "skill_library": "skills",
                    "algorithm_library": "algorithms",
                    "algorithm_experiments": "experiments",
                    "workspace": "work",
                    "governance": "gov",
                    "logs": "audit",
                },
                "adapters": {
                    "academic_search": {
                        "provider": "local",
                        "fixture_path": str(tmp_path / "papers.json"),
                    },
                    "docker_sandbox": {
                        "enabled": False,
                        "image": "python:3.12-slim",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "papers.json").write_text(
        json.dumps([{"title": "Causal Graphs", "summary": "Better diagnosis"}]),
        encoding="utf-8",
    )

    runtime = LocalRuntime.from_config_file(config_path)

    assert runtime.root_path == tmp_path / "runtime"
    assert runtime.skill_lifecycle.skill_library_path == tmp_path / "runtime" / "skills"
    assert runtime.algorithm_registry.root_path == tmp_path / "runtime" / "algorithms"
    assert runtime.algorithm_experiments.output_path == tmp_path / "runtime" / "experiments"
    assert runtime.sandbox_runner.workspace_path == tmp_path / "runtime" / "work"
    assert runtime.adapters["academic_search"].search("diagnosis").items[0]["title"] == "Causal Graphs"


def test_builtin_algorithm_engines_run_deterministic_benchmarks():
    from dual_ring_ai.algorithms.bayesian_diagnostics import BayesianDiagnosticsEngine
    from dual_ring_ai.algorithms.causal_graph_diagnostics import CausalGraphDiagnosticsEngine
    from dual_ring_ai.algorithms.thought_tree_reasoner import ThoughtTreeReasoner

    incidents = [
        {
            "signals": {"api_errors": 0.9, "db_latency": 0.8, "deploy_recent": 0.7},
            "expected_root_cause": "database_regression",
        },
        {
            "signals": {"api_errors": 0.8, "network_errors": 0.9, "deploy_recent": 0.1},
            "expected_root_cause": "network_outage",
        },
    ]

    baseline = BayesianDiagnosticsEngine().evaluate(incidents)
    candidate = CausalGraphDiagnosticsEngine().evaluate(incidents)
    reasoning = ThoughtTreeReasoner(branch_limit=3).solve(
        goal="reduce repeated failed searches",
        options=[
            "retry the same search",
            "change query terms and inspect source credibility",
            "ignore the failure",
        ],
    )

    assert candidate["f1_score"] >= baseline["f1_score"]
    assert candidate["latency_ms"] <= baseline["latency_ms"]
    assert reasoning["selected_option"] == "change query terms and inspect source credibility"


def test_algorithmist_scans_local_academic_fixture_and_creates_research_proposal(tmp_path):
    from dual_ring_ai.adapters.academic_search import AcademicSearchAdapter
    from dual_ring_ai.core.event_bus import EventBus
    from dual_ring_ai.genesis.algorithmist import AlgorithmistAgent

    fixture_path = tmp_path / "papers.json"
    fixture_path.write_text(
        json.dumps(
            [
                {
                    "title": "Causal Graph Diagnostics",
                    "summary": "Causal graphs improve root cause analysis accuracy.",
                    "candidate_engine": "causal_graph_diagnostics:1.0.0",
                    "metrics": ["f1_score", "latency_ms"],
                }
            ]
        ),
        encoding="utf-8",
    )
    event_bus = EventBus()
    adapter = AcademicSearchAdapter(provider="local", fixture_path=fixture_path)
    algorithmist = AlgorithmistAgent(event_bus, tmp_path / "workspace", adapter)

    proposal = algorithmist.scan_literature_and_propose(
        target_agent="Archaeologist",
        current_engine="bayesian_diagnostics:1.0.0",
        query="root cause diagnosis",
    )

    assert proposal.candidate_engine == "causal_graph_diagnostics:1.0.0"
    assert "Causal Graph Diagnostics" in proposal.hypothesis
    assert event_bus.list_events("ALGORITHM_RESEARCH_PROPOSED")


def test_blueprint_orchestrator_hot_reloads_changed_thinking_engine(tmp_path):
    from dual_ring_ai.core.blueprint_orchestrator import BlueprintOrchestrator

    charter_path = tmp_path / "charter"
    blueprint_path = charter_path / "archaeologist.yaml"
    charter_path.mkdir()
    AgentBlueprint(
        role_name="Archaeologist",
        version="1.0",
        agent_class="dual_ring_ai.genesis.archaeologist.ArchaeologistAgent",
        thinking_engine=ThinkingEngineRef(
            name="bayesian_diagnostics",
            version="1.0.0",
            evaluation_suite="diagnostics_v1",
        ),
    ).save(blueprint_path)

    orchestrator = BlueprintOrchestrator(charter_path)
    first = orchestrator.load_blueprints()
    AgentBlueprint.load(blueprint_path).__class__(
        role_name="Archaeologist",
        version="1.1",
        agent_class="dual_ring_ai.genesis.archaeologist.ArchaeologistAgent",
        thinking_engine=ThinkingEngineRef(
            name="causal_graph_diagnostics",
            version="1.0.0",
            evaluation_suite="diagnostics_v1",
        ),
    ).save(blueprint_path)
    changed = orchestrator.reload_changed()

    assert first["Archaeologist"].thinking_engine.name == "bayesian_diagnostics"
    assert changed["Archaeologist"].thinking_engine.name == "causal_graph_diagnostics"


def test_docker_sandbox_adapter_builds_open_command_without_running(tmp_path):
    from dual_ring_ai.adapters.container_sandbox import DockerSandboxAdapter

    adapter = DockerSandboxAdapter(enabled=True, dry_run=True, image="python:3.12-slim")
    result = adapter.run(["python", "-m", "pytest"], workspace=tmp_path)

    assert result["status"] == "dry_run"
    assert "--network" not in result["command"]
    assert str(tmp_path.resolve()) + ":/workspace" in result["command"]


def test_cockpit_decision_endpoint_is_used_by_page_and_updates_approval(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    request = runtime.governance.create_request(
        request_type="algorithm_research",
        title="Research causal graph engine",
        payload={"proposal_id": "aep-1"},
        requested_by="algorithmist_agent",
        risk_level="high",
    )
    client = TestClient(create_cockpit_app(runtime))

    decision = client.post(
        f"/approvals/{request.request_id}/decision",
        json={"decision": "approved", "decided_by": "architect", "comments": "ok"},
    )

    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"
