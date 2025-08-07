import json
from pathlib import Path

import pytest

from autogpt.plugins.loader import PluginMetaValidationError, load_plugin_meta


def test_load_plugin_meta_success(tmp_path: Path) -> None:
    src_file = tmp_path / "dummy.py"
    src_file.write_text("print('ok')")
    spec = {
        "name": "demo",
        "description": "demo plugin",
        "instructions": "do things",
        "underlying_library": {
            "name": "lib",
            "version": "0.1",
            "repo_url": "https://example.com/lib",
            "local_source_path": src_file.name,
        },
        "source_code_access_policy": "ALLOWED_FOR_READ_ONLY",
    }
    spec_file = tmp_path / "plugin.json"
    spec_file.write_text(json.dumps(spec))
    meta = load_plugin_meta(spec_file)
    assert meta.name == "demo"
    assert meta.underlying_library.local_source_path == str(src_file.resolve())


def test_load_plugin_meta_missing_field(tmp_path: Path) -> None:
    spec = {
        "name": "demo",
        "description": "demo plugin",
        "instructions": "do things",
        "source_code_access_policy": "ALLOWED_FOR_READ_ONLY",
    }
    spec_file = tmp_path / "plugin.json"
    spec_file.write_text(json.dumps(spec))
    with pytest.raises(PluginMetaValidationError):
        load_plugin_meta(spec_file)


def test_load_plugin_meta_invalid_policy(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    src.write_text("# test")
    spec = {
        "name": "demo",
        "description": "demo plugin",
        "instructions": "do things",
        "underlying_library": {
            "name": "lib",
            "version": "0.1",
            "repo_url": "https://example.com/lib",
            "local_source_path": src.name,
        },
        "source_code_access_policy": "UNKNOWN",
    }
    spec_file = tmp_path / "plugin.json"
    spec_file.write_text(json.dumps(spec))
    with pytest.raises(PluginMetaValidationError):
        load_plugin_meta(spec_file)


def test_load_plugin_meta_missing_local_source_path(tmp_path: Path) -> None:
    spec = {
        "name": "demo",
        "description": "demo plugin",
        "instructions": "do things",
        "underlying_library": {
            "name": "lib",
            "version": "0.1",
            "repo_url": "https://example.com/lib",
            "local_source_path": "missing.py",
        },
        "source_code_access_policy": "ALLOWED_FOR_READ_ONLY",
    }
    spec_file = tmp_path / "plugin.json"
    spec_file.write_text(json.dumps(spec))
    with pytest.raises(PluginMetaValidationError):
        load_plugin_meta(spec_file)
