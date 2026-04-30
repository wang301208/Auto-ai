import json
from pathlib import Path


def test_academic_search_adapter_returns_disabled_result_without_provider():
    from dual_ring_ai.adapters.academic_search import AcademicSearchAdapter

    adapter = AcademicSearchAdapter()
    results = adapter.search("causal inference", limit=3)

    assert results.provider == "disabled"
    assert results.query == "causal inference"
    assert results.items == []
    assert "not configured" in results.message


def test_voice_adapter_transcribes_text_fallback():
    from dual_ring_ai.adapters.voice import LocalVoiceAdapter

    adapter = LocalVoiceAdapter(mode="text")

    assert adapter.transcribe_text("启动系统") == "启动系统"
    assert adapter.synthesize_text("完成") == {"mode": "text", "text": "完成"}


def test_avatar_adapter_maps_emotion_to_event():
    from dual_ring_ai.adapters.avatar import AvatarAdapter

    adapter = AvatarAdapter()
    event = adapter.render_event(text="任务完成", emotion="focused", action="nod")

    assert event["text"] == "任务完成"
    assert event["emotion"] == "focused"
    assert event["animation"] == "nod"


def test_docker_sandbox_adapter_reports_unavailable_without_docker():
    from dual_ring_ai.adapters.container_sandbox import DockerSandboxAdapter

    adapter = DockerSandboxAdapter(enabled=False)
    result = adapter.run(["python", "--version"], workspace=Path("."))

    assert result["status"] == "unavailable"
    assert "disabled" in result["reason"]


def test_desktop_scaffold_writes_tauri_contract(tmp_path):
    from dual_ring_ai.desktop.scaffold import DesktopScaffold

    scaffold = DesktopScaffold(tmp_path / "desktop")
    manifest = scaffold.write_contract(api_base_url="http://127.0.0.1:8000")

    contract_path = tmp_path / "desktop" / "src-tauri" / "dual-ring-contract.json"
    package_path = tmp_path / "desktop" / "package.json"

    assert manifest["api_base_url"] == "http://127.0.0.1:8000"
    assert contract_path.exists()
    assert json.loads(contract_path.read_text())["commands"] == [
        "get_status",
        "list_approvals",
        "decide_approval",
        "list_algorithm_proposals",
    ]
    assert package_path.exists()
