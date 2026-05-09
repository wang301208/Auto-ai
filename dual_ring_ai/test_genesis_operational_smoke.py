import json

from fastapi.testclient import TestClient


def test_runtime_runs_operational_smoke_cycles_and_writes_report(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    report = runtime.run_operational_smoke(cycles=2)
    report_path = runtime.write_operational_smoke_report(cycles=2)
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["summary"]["cycles"] == 2
    assert report["summary"]["status"] == "passed"
    assert [cycle["cycle"] for cycle in report["cycles"]] == [1, 2]
    assert all(cycle["interaction"]["avatar_event"]["animation"] for cycle in report["cycles"])
    assert report_path.name == "operational_smoke_report.json"
    assert saved["summary"]["cycles"] == 2


def test_cockpit_api_runs_operational_smoke(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/operational-smoke", json={"cycles": 2})

    assert response.status_code == 200
    assert response.json()["summary"]["status"] == "passed"
    assert response.json()["summary"]["cycles"] == 2


def test_cockpit_api_writes_same_operational_smoke_report_it_returns(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/api/operational-smoke", json={"cycles": 1})
    saved = json.loads((tmp_path / "operational_smoke_report.json").read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert response.json() == saved
    assert len(runtime.event_bus.list_events("INTERACTION_COMPLETED")) == 1


def test_cockpit_api_rejects_excessive_operational_smoke_cycles(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/api/operational-smoke", json={"cycles": 101})

    assert response.status_code == 422


def test_operational_smoke_script_exists_and_uses_config_loader():
    from pathlib import Path

    script_path = Path("scripts/run_local_operational_smoke.ps1")
    script_text = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "LocalRuntime.from_config_file" in script_text
    assert "write_operational_smoke_report" in script_text
    assert "DUAL_RING_CONFIG_PATH" in script_text
