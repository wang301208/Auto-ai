import json

from fastapi.testclient import TestClient


def test_runtime_final_acceptance_report_marks_external_gates_explicitly(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))

    report = runtime.final_acceptance_report(stress_cycles=3)
    report_path = runtime.write_final_acceptance_report(stress_cycles=3)
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["summary"]["status"] in {"ready_for_real_integration", "attention_required"}
    assert report["gates"]["local_control_plane"]["status"] == "passed"
    assert report["gates"]["interaction_stress"]["cycles"] == 3
    assert report["gates"]["terminal_ui"]["status"] == "ready"
    assert report["gates"]["external_services"]["ollama"]["status"] in {
        "disabled",
        "dry_run",
        "available",
        "unavailable",
    }
    assert report_path.name == "final_acceptance_report.json"
    assert saved["summary"]["status"] == report["summary"]["status"]


def test_runtime_interaction_stress_records_all_cycles(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    stress = runtime.run_interaction_stress(cycles=5)

    assert stress["status"] == "passed"
    assert stress["cycles"] == 5
    assert len(stress["results"]) == 5
    assert all(item["avatar_event"]["animation"] for item in stress["results"])


def test_cockpit_api_exposes_final_acceptance(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post(
        "/final-acceptance",
        json={"stress_cycles": 2},
    )

    assert response.status_code == 200
    assert response.json()["gates"]["interaction_stress"]["cycles"] == 2
    assert response.json()["gates"]["terminal_ui"]["status"] == "ready"


def test_cockpit_api_writes_same_final_acceptance_report_it_returns(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post(
        "/api/final-acceptance",
        json={"stress_cycles": 2},
    )
    saved = json.loads((tmp_path / "final_acceptance_report.json").read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert response.json() == saved
    assert len(runtime.event_bus.list_events("INTERACTION_COMPLETED")) == 4


def test_cockpit_api_rejects_excessive_final_acceptance_stress_cycles(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/api/final-acceptance", json={"stress_cycles": 101})

    assert response.status_code == 422


def test_final_acceptance_script_exists_and_uses_final_report():
    from pathlib import Path

    script_path = Path("scripts/run_final_acceptance.ps1")
    script_text = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "write_final_acceptance_report" in script_text
    assert "LocalRuntime.from_config_file" in script_text
    assert "DUAL_RING_CONFIG_PATH" in script_text
