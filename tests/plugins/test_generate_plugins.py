import json
from pathlib import Path
from types import SimpleNamespace

from scripts.generate_plugins import generate_plugins, AUTO_HEADER, llm_generate


def test_generate_plugins(tmp_path):
    stubs = tmp_path / "plugins" / "stubs"
    stubs.mkdir(parents=True)
    spec = {"name": "sample", "description": "sample plugin"}
    (stubs / "sample.spec.json").write_text(json.dumps(spec))

    generate_plugins(tmp_path)

    plugin_file = tmp_path / "plugins" / "sample.py"
    assert plugin_file.exists()
    content = plugin_file.read_text()
    assert AUTO_HEADER.strip() in content


def test_llm_generate_uses_chat_completions(mocker, monkeypatch):
    spec = {"name": "sample"}
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="result"))]
    )
    mock_create = mocker.Mock(return_value=mock_response)
    mocker.patch("scripts.generate_plugins.openai.chat.completions.create", mock_create)
    assert llm_generate(spec) == "result"
    mock_create.assert_called_once()
