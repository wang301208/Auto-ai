import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

# Avoid importing autoai.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autoai.agents")
agents_pkg.__path__ = ["autoai/agents"]
sys.modules.setdefault("autoai.agents", agents_pkg)

dep = importlib.import_module("autoai.agents.archaeologist_dependency")


def test_analyze_dependency_uses_new_version(tmp_path: Path) -> None:
    src = tmp_path / "mod.py"
    src.write_text("import sample_dep\nsample_dep.old_func()\n")

    called: list[str | None] = []

    def fake_fetch(package: str, version: str | None) -> str:
        called.append(version)
        if version == "2.0":
            return "old_func removed"
        return ""

    with (
        patch.object(dep.metadata, "version", return_value="1.0"),
        patch.object(dep, "fetch_release_notes", side_effect=fake_fetch),
    ):
        result = dep.analyze_dependency("sample_dep", src, new_version="2.0")

    assert called == ["2.0"]
    assert result["version"] == "1.0"
    assert result["new_version"] == "2.0"
    assert any("sample_dep 2.0" in f for f in result["findings"])
