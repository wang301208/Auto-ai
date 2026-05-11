import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_runtime_startup_artifacts_exist():
    config_path = ROOT / "configs" / "local_autonomous_runtime.example.json"
    runtime_script = ROOT / "scripts" / "start_local_autonomous_runtime.ps1"
    cockpit_script = ROOT / "scripts" / "start_cockpit_api.ps1"
    runbook_path = ROOT / "docs" / "superpowers" / "local-autonomous-runtime-runbook.md"

    assert config_path.exists()
    assert runtime_script.exists()
    assert cockpit_script.exists()
    assert runbook_path.exists()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["root_path"] == ".dual_ring_runtime"
    assert config["enable_agents"] is False
    assert "skill_library" in config["managed_paths"]
    assert "algorithm_experiments" in config["managed_paths"]
    assert "organizational_charter" in config["managed_paths"]
    assert config["adapters"]["remote_llm"]["enabled"] is True
    assert config["adapters"]["remote_llm"]["dry_run"] is False
    assert config["adapters"]["docker_sandbox"]["enabled"] is True
    assert config["adapters"]["docker_sandbox"]["dry_run"] is False
    assert config["adapters"]["ollama"]["enabled"] is True
    assert config["adapters"]["whisper"]["enabled"] is True
    assert config["adapters"]["xtts"]["enabled"] is True
    assert config["security_defaults"]["network"] is True
    assert config["security_defaults"]["shell"] is True
    assert config["security_defaults"]["filesystem"]["read"] == ["*"]
    assert config["security_defaults"]["filesystem"]["write"] == ["*"]
    assert config["security_defaults"]["environment"]["allow"] == ["*"]

    runtime_script_text = runtime_script.read_text(encoding="utf-8")
    cockpit_script_text = cockpit_script.read_text(encoding="utf-8")
    runbook_text = runbook_path.read_text(encoding="utf-8")

    assert "LocalRuntimeConfig" in runtime_script_text
    assert "uvicorn" in cockpit_script_text
    assert "端到端闭环" in runbook_text
    assert "算法进化闭环" in runbook_text
