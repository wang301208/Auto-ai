import json

from fastapi.testclient import TestClient


def test_host_integration_probe_reports_required_tools_without_claiming_success(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    report = runtime.host_integration_probe()
    report_path = runtime.write_host_integration_probe()
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["summary"]["status"] in {"ready", "partial", "missing_requirements"}
    assert {"docker", "node", "npm", "ollama", "whisper", "xtts"}.issubset(
        report["tools"]
    )
    assert "tauri" not in report["tools"]
    assert "cargo" not in report["tools"]
    assert all("status" in item for item in report["tools"].values())
    assert report_path.name == "host_integration_probe.json"
    assert saved["summary"]["status"] == report["summary"]["status"]


def test_final_acceptance_includes_host_integration_gate(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))

    report = runtime.final_acceptance_report(stress_cycles=1)

    assert "host_integration" in report["gates"]
    assert report["gates"]["terminal_ui"]["status"] == "ready"
    assert "tools" in report["gates"]["host_integration"]
    assert report["gates"]["host_integration"]["summary"]["status"] in {
        "ready",
        "partial",
        "missing_requirements",
    }


def test_cockpit_api_exposes_host_integration_probe(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/host-integration-probe")

    assert response.status_code == 200
    assert "docker" in response.json()["tools"]
    assert response.json()["summary"]["status"] in {
        "ready",
        "partial",
        "missing_requirements",
    }


def test_cockpit_api_writes_same_host_probe_report_it_returns(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/api/host-integration-probe")
    saved = json.loads((tmp_path / "host_integration_probe.json").read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert response.json() == saved


def test_host_integration_script_exists_and_writes_probe():
    from pathlib import Path

    script_path = Path("scripts/run_host_integration_probe.ps1")
    script_text = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "write_host_integration_probe" in script_text
    assert "LocalRuntime.from_config_file" in script_text
    assert "DUAL_RING_CONFIG_PATH" in script_text
