import json


def test_local_llm_adapter_personalizes_backend_status_without_network():
    from dual_ring_ai.adapters.local_llm import LocalLLMAdapter

    adapter = LocalLLMAdapter(persona="calm_architect")
    response = adapter.generate_response(
        user_text="系统怎么样？",
        backend_payload={"running": True, "services": {"governance": "ready"}},
    )

    assert response["provider"] == "local_rule_based"
    assert "治理" in response["text"]
    assert response["emotion"] == "focused"
    assert response["action"] == "explain"


def test_multimodal_interaction_pipeline_combines_voice_llm_and_avatar():
    from dual_ring_ai.interaction.pipeline import InteractionPipeline

    pipeline = InteractionPipeline()
    result = pipeline.handle_text(
        "审批队列状态",
        backend_payload={"approvals": [{"status": "pending"}]},
    )

    assert result["transcript"] == "审批队列状态"
    assert "pending" in result["response_text"]
    assert result["speech"]["text"] == result["response_text"]
    assert result["avatar_event"]["animation"] == "explain"


def test_algorithm_research_report_and_peer_review_gate_promotion(tmp_path):
    from dual_ring_ai.core.algorithm_evolution import AlgorithmEvolutionProtocol
    from dual_ring_ai.core.algorithm_experiment import AlgorithmExperimentRunner
    from dual_ring_ai.core.algorithm_registry import AlgorithmManifest, AlgorithmRegistry
    from dual_ring_ai.core.event_bus import EventBus
    from dual_ring_ai.core.governance import GovernanceStore

    registry = AlgorithmRegistry(tmp_path / "algorithms")
    registry.register(
        AlgorithmManifest(
            name="causal_graph_diagnostics",
            version="1.0.0",
            description="Causal graph diagnostics",
            source_module="dual_ring_ai.algorithms.causal_graph_diagnostics",
            status="candidate",
            metrics={"f1_score": 0.9, "latency_ms": 80},
            rollback_to="bayesian_diagnostics:1.0.0",
            evaluation_suite="diagnostics_v1",
        )
    )
    protocol = AlgorithmEvolutionProtocol(
        tmp_path,
        registry,
        AlgorithmExperimentRunner(tmp_path / "experiments"),
        GovernanceStore(tmp_path / "governance"),
        EventBus(),
    )
    report_path = tmp_path / "experiments" / "aep_1_report.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "proposal_id": "aep_1",
                "baseline_engine": "bayesian_diagnostics:1.0.0",
                "candidate_engine": "causal_graph_diagnostics:1.0.0",
                "metric_deltas": {"f1_score": 0.12, "latency_ms": -30},
                "recommendation": "promote_candidate",
            }
        ),
        encoding="utf-8",
    )

    research_report = protocol.write_research_report(
        report_path,
        hypothesis="Causal graph diagnostics improves multi-fault diagnosis.",
        reviewer_agents=["strategist", "qa"],
    )
    review = protocol.peer_review_research_report(
        research_report.report_path,
        required_reviewers=["strategist", "qa"],
    )

    assert research_report.status == "ready_for_peer_review"
    assert review["decision"] == "approved_for_human_promotion_review"
    assert review["reviewers"] == ["strategist", "qa"]


def test_terminal_ui_integration_handles_text(tmp_path):
    from dual_ring_ai.interaction.terminal_ui import create_tui
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    tui = create_tui(runtime=runtime)
    response = tui.handle_text("status please")

    assert response["transcript"] == "status please"
    assert response["avatar_event"]["animation"]
