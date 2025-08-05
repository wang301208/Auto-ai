from __future__ import annotations

import importlib.util
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType


def _load_main() -> ModuleType:
    spec: ModuleSpec | None = importlib.util.spec_from_file_location(
        "main", Path(__file__).parent / "main.py"
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_returns_hello_world() -> None:
    main = _load_main()
    assert main.run() == "Hello, world!"
