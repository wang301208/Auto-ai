import sys
import zipfile
from pathlib import Path

import pytest

from autogpt.core.plugin.simple import SimplePluginService


def test_load_from_file_path_directory(tmp_path):
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("class DirPlugin:\n    pass\n")

    plugin_route = f"{pkg_dir}:mypkg.DirPlugin"
    plugin_class = SimplePluginService.load_from_file_path(plugin_route)
    assert plugin_class.__name__ == "DirPlugin"


def test_load_from_file_path_zip(tmp_path):
    pkg_dir = tmp_path / "zip_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("class ZipPlugin:\n    pass\n")
    zip_path = tmp_path / "zip_pkg.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(pkg_dir / "__init__.py", arcname="zip_pkg/__init__.py")

    plugin_route = f"{zip_path}:zip_pkg.ZipPlugin"
    plugin_class = SimplePluginService.load_from_file_path(plugin_route)
    assert plugin_class.__name__ == "ZipPlugin"


def test_resolve_name_to_path_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_file = plugins_dir / "foo.py"
    plugin_file.write_text("")

    resolved = SimplePluginService.resolve_name_to_path("foo", "file")
    assert Path(resolved) == plugin_file


def test_resolve_name_to_path_import(tmp_path):
    pkg_root = tmp_path / "autogpt_plugins"
    pkg_root.mkdir()
    (pkg_root / "__init__.py").write_text("")
    (pkg_root / "bar.py").write_text("")

    sys.path.insert(0, str(tmp_path))
    try:
        resolved = SimplePluginService.resolve_name_to_path("bar", "import")
        assert resolved == "autogpt_plugins.bar"
    finally:
        sys.path.pop(0)
