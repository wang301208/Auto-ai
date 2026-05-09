import json

from fastapi.testclient import TestClient


def test_runtime_writes_preflight_report_with_required_sections(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    report_path = runtime.write_preflight_report()

    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_path.name == "preflight_report.json"
    assert payload["summary"]["status"] in {"ready", "attention_required"}
    assert "runtime" in payload["checks"]
    assert "adapters" in payload["checks"]
    assert "security" in payload["checks"]
    assert "blueprints" in payload["checks"]
    assert payload["checks"]["security"]["network"] is True
    assert payload["checks"]["security"]["shell"] is True
    assert payload["checks"]["adapters"]["docker_sandbox"]["status"] in {
        "completed",
        "failed",
        "unavailable",
    }


def test_cockpit_api_exposes_preflight_report_without_web_frontend(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.post("/preflight")
    page = client.get("/")

    assert response.status_code == 200
    assert response.json()["summary"]["status"] in {"ready", "attention_required"}
    assert page.status_code == 404


def test_cockpit_api_exposes_prefixed_api_routes(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    response = client.get("/api/status")

    assert response.status_code == 200
    assert "services" in response.json()


def test_cockpit_root_does_not_serve_react_dist(tmp_path, monkeypatch):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<div id=\"root\"></div>", encoding="utf-8")

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path / "runtime"))
    client = TestClient(create_cockpit_app(runtime))

    response = client.get("/")

    assert response.status_code == 404


def test_cockpit_api_skips_malformed_algorithm_proposal_files(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    proposal_dir = tmp_path / "workspace" / "algorithm_research_proposals"
    proposal_dir.mkdir(parents=True)
    (proposal_dir / "broken.json").write_text("{", encoding="utf-8")
    (proposal_dir / "valid.json").write_text(
        json.dumps({"proposal_id": "proposal_1"}),
        encoding="utf-8",
    )
    client = TestClient(create_cockpit_app(runtime))

    response = client.get("/api/algorithm-proposals")

    assert response.status_code == 200
    assert response.json() == [{"proposal_id": "proposal_1"}]


def test_start_runtime_script_loads_full_config_and_writes_preflight():
    script_text = (
        __import__("pathlib")
        .Path("scripts/start_local_autonomous_runtime.ps1")
        .read_text(encoding="utf-8")
    )

    assert "LocalRuntime.from_config_file" in script_text
    assert "write_preflight_report" in script_text
    assert "DUAL_RING_CONFIG_PATH" in script_text


def test_cockpit_script_passes_config_path_to_server():
    script_text = (
        __import__("pathlib")
        .Path("scripts/start_cockpit_api.ps1")
        .read_text(encoding="utf-8")
    )

    assert "DUAL_RING_CONFIG_PATH" in script_text
    assert "dual_ring_ai.dashboard.cockpit_server:app" in script_text
