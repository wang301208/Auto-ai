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


def test_terminal_ui_entrypoints_are_retained():
    root = Path(__file__).resolve().parents[1]

    assert (root / "ui-tui" / "package.json").exists()
    assert (root / "ui-tui" / "src" / "entry.tsx").exists()
    assert (root / "tui_gateway" / "entry.py").exists()
