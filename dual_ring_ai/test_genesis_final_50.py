import json

import pytest
from fastapi.testclient import TestClient

from dual_ring_ai.core.agent_blueprint import AgentBlueprint, ThinkingEngineRef


def write_blueprint(path, role_name="TDD_Developer", subscribed_events=None):
    AgentBlueprint(
        role_name=role_name,
        version="1.0",
        agent_class="dual_ring_ai.genesis.tdd_developer.TDDDeveloperAgent",
        thinking_engine=ThinkingEngineRef(
            name="thought_tree_reasoner",
            version="1.0.0",
            evaluation_suite="planning_v1",
        ),
        authorized_plugins=["Plugin_FileIO", "Plugin_PytestRunner"],
        subscribed_events=subscribed_events or ["DIAGNOSIS_COMPLETE"],
        config={"max_parallel_tasks": 1},
    ).save(path)


def test_ollama_adapter_has_disabled_dry_run_and_http_boundaries():
    from dual_ring_ai.adapters.ollama import OllamaAdapter

    disabled = OllamaAdapter(enabled=False)
    assert disabled.probe()["status"] == "disabled"
    assert disabled.generate("hello")["status"] == "disabled"

    dry_run = OllamaAdapter(enabled=True, dry_run=True, model="llama3.1")
    probe = dry_run.probe()
    generated = dry_run.generate("summarize status")

    assert probe["status"] == "dry_run"
    assert probe["url"] == "http://127.0.0.1:11434/api/tags"
    assert generated["status"] == "dry_run"
    assert generated["request"]["json"]["model"] == "llama3.1"
    assert generated["request"]["json"]["prompt"] == "summarize status"


def test_whisper_and_xtts_adapters_build_commands_without_running(tmp_path):
    from dual_ring_ai.adapters.whisper import WhisperAdapter
    from dual_ring_ai.adapters.xtts import XTTSAdapter

    audio_path = tmp_path / "input.wav"
    output_path = tmp_path / "voice.wav"
    audio_path.write_bytes(b"RIFF")

    whisper = WhisperAdapter(enabled=True, dry_run=True, model="base")
    xtts = XTTSAdapter(enabled=True, dry_run=True, speaker_wav=tmp_path / "speaker.wav")

    transcription = whisper.transcribe(audio_path)
    speech = xtts.synthesize("Runtime ready", output_path)

    assert transcription["status"] == "dry_run"
    assert "--model" in transcription["command"]
    assert str(audio_path) in transcription["command"]
    assert speech["status"] == "dry_run"
    assert "--text" in speech["command"]
    assert str(output_path) in speech["command"]


def test_docker_sandbox_command_uses_resource_limits_and_open_workspace_by_default(
    tmp_path,
):
    from dual_ring_ai.adapters.container_sandbox import DockerSandboxAdapter

    adapter = DockerSandboxAdapter(
        enabled=True,
        dry_run=True,
        image="python:3.12-slim",
        memory_limit="256m",
        cpus="0.5",
    )
    result = adapter.run(["python", "-m", "pytest"], workspace=tmp_path)
    command = result["command"]

    assert result["status"] == "dry_run"
    assert "--network" not in command
    assert "--read-only" not in command
    assert "--memory" in command
    assert "256m" in command
    assert "--cpus" in command
    assert "0.5" in command
    assert "--pids-limit" in command
    assert f"{tmp_path.resolve()}:/workspace:rw" in command


def test_docker_sandbox_can_still_build_restricted_command(tmp_path):
    from dual_ring_ai.adapters.container_sandbox import DockerSandboxAdapter

    adapter = DockerSandboxAdapter(
        enabled=True,
        dry_run=True,
        network_mode="none",
        read_only=True,
    )
    result = adapter.run(["python", "-m", "pytest"], workspace=tmp_path)
    command = result["command"]

    assert result["status"] == "dry_run"
    assert ["--network", "none"] == command[3:5]
    assert "--read-only" in command
    assert "--tmpfs" in command


def test_founder_agent_creates_organization_change_request_and_runtime_applies_it(tmp_path):
    from dual_ring_ai.genesis.founder import FounderAgent
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    charter_path = tmp_path / "organizational_charter"
    charter_path.mkdir()
    write_blueprint(charter_path / "tdd_developer.yaml")

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path / "runtime",
            managed_paths={"organizational_charter": str(charter_path)},
        )
    )
    founder = FounderAgent(runtime.event_bus, charter_path)
    proposal = founder.analyze_and_propose(
        {
            "task_category_counts": {"frontend": 14, "backend": 2},
            "bottleneck_agent": "TDD_Developer",
            "failure_rates": {"frontend": 0.42},
        }
    )
    request = runtime.create_organization_change_request(
        proposal.proposal_path,
        requested_by="founder_agent",
    )

    assert proposal.change_type == "create_blueprint"
    assert proposal.target_role == "Frontend_Developer"
    assert request.request_type == "organization_change"
    assert request.risk_level == "constitutional"
    with pytest.raises(PermissionError):
        runtime.apply_organization_change_from_approval(
            request.request_id,
            approved_by="architect",
        )

    runtime.governance.decide(request.request_id, "approved", "architect")
    applied = runtime.apply_organization_change_from_approval(
        request.request_id,
        approved_by="architect",
    )

    assert applied.role_name == "Frontend_Developer"
    assert (charter_path / "frontend_developer.yaml").exists()
    assert runtime.blueprint_orchestrator.reload_changed()["Frontend_Developer"]
    assert runtime.event_bus.list_events("ORGANIZATION_CHANGE_APPLIED")


def test_cockpit_api_exposes_interaction_avatar_reviews_and_terminal_only_contract(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    review_dir = tmp_path / "algorithm_research_reports"
    review_dir.mkdir()
    (review_dir / "aep_1_peer_review.json").write_text(
        json.dumps({"proposal_id": "aep_1", "decision": "approved"}),
        encoding="utf-8",
    )
    client = TestClient(create_cockpit_app(runtime))

    interaction = client.post("/interaction", json={"text": "status please"})
    avatar = client.get("/avatar/latest")
    reviews = client.get("/algorithm-reviews")
    page = client.get("/")

    assert interaction.status_code == 200
    assert interaction.json()["transcript"] == "status please"
    assert avatar.status_code == 200
    assert avatar.json()["animation"] == interaction.json()["avatar_event"]["animation"]
    assert reviews.status_code == 200
    assert reviews.json()[0]["proposal_id"] == "aep_1"
    assert client.get("/desktop/contract").status_code == 404
    assert page.status_code == 404


def test_runtime_rejects_unsafe_config_paths_and_accepts_open_defaults(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime

    unsafe_path_config = tmp_path / "unsafe-path.json"
    unsafe_path_config.write_text(
        json.dumps(
            {
                "root_path": str(tmp_path / "runtime"),
                "managed_paths": {"workspace": "../outside"},
            }
        ),
        encoding="utf-8",
    )
    open_defaults_config = tmp_path / "open-defaults.json"
    open_defaults_config.write_text(
        json.dumps(
            {
                "root_path": str(tmp_path / "runtime"),
                "security_defaults": {
                    "network": True,
                    "shell": True,
                    "filesystem": {"read": ["*"], "write": ["*"]},
                    "environment": {"allow": ["*"], "request": ["OPENAI_API_KEY"]},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="managed path escapes runtime root"):
        LocalRuntime.from_config_file(unsafe_path_config)
    runtime = LocalRuntime.from_config_file(open_defaults_config)
    assert runtime.security_defaults["network"] is True
    assert runtime.security_defaults["shell"] is True
    assert runtime.security_defaults["filesystem"]["write"] == ["*"]
