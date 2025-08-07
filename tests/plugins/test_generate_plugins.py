import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture


def test_generate_plugins(tmp_path: Path) -> None:
    from scripts.generate_plugins import AUTO_HEADER, generate_plugins

    stubs = tmp_path / "plugins" / "stubs"
    stubs.mkdir(parents=True)
    spec_file = stubs / "sample.spec.json"
    spec = {
        "name": "sample",
        "description": "sample plugin",
        "instructions": "Return the input text",
        "underlying_library": {
            "name": "python",
            "version": "3.11",
            "repo_url": "https://github.com/python/cpython",
            "local_source_path": spec_file.name,
        },
        "source_code_access_policy": "ALLOWED_FOR_READ_ONLY",
    }
    spec_file.write_text(json.dumps(spec))

    generate_plugins(tmp_path)

    plugin_file = tmp_path / "plugins" / "sample.py"
    assert plugin_file.exists()
    content = plugin_file.read_text()
    assert AUTO_HEADER.strip() in content


def test_llm_generate_uses_chat_completions(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = {"name": "sample"}
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    import scripts.generate_plugins as gp

    importlib.reload(gp)
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="result"))]
    )
    mock_create = mocker.Mock(return_value=mock_response)
    mocker.patch(
        "scripts.generate_plugins.openai_client.chat.completions.create", mock_create
    )
    assert gp.llm_generate(spec) == "result"
    mock_create.assert_called_once()
