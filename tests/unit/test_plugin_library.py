"""Tests for :mod:`autoai.plugins.library`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

from autoai.config import Config


def _make_embedding_map() -> Dict[str, List[float]]:
    return {
        "desc1\ntag1": [1.0, 0.0, 0.0],
        "desc2\ntag2": [0.0, 1.0, 0.0],
        "desc1": [1.0, 0.0, 0.0],
        "desc2": [0.0, 1.0, 0.0],
        "tag1": [1.0, 0.0, 0.0],
        "tag2": [0.0, 1.0, 0.0],
    }


def test_plugin_library_load_and_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from types import ModuleType

    # Stub out heavy optional dependencies used by get_embedding
    repo_root = next(Path(p) for p in sys.path if p.endswith("AutoAI-0.4.7"))
    vector_pkg = ModuleType("autoai.memory.vector")
    vector_pkg.__path__ = [str(repo_root / "autoai" / "memory" / "vector")]
    sys.modules.setdefault("autoai.memory.vector", vector_pkg)
    sys.modules.setdefault("spacy", ModuleType("spacy"))

    from autoai.plugins.library import PluginLibrary
    from autoai.skills.vector_db import MemoryVectorDB

    config = Config()
    repo = tmp_path / "plugin_repo"
    repo.mkdir()

    (repo / "p1.spec.json").write_text(
        json.dumps({"name": "p1", "description": "desc1", "tags": ["tag1"]})
    )
    (repo / "p2.spec.json").write_text(
        json.dumps({"name": "p2", "description": "desc2", "tags": ["tag2"]})
    )

    embeddings = _make_embedding_map()

    def fake_get_embedding(text: str, _config: Config) -> List[float]:
        return embeddings[text]

    monkeypatch.setattr("autoai.plugins.library.get_embedding", fake_get_embedding)

    library = PluginLibrary(config, repo, vector_db=MemoryVectorDB())

    p1 = library.get_plugin("p1")
    assert p1 and p1.description == "desc1"

    results = library.search("desc1", top_k=1)
    assert results == ["p1"]

    tag_results = library.search("tag2", top_k=1)
    assert tag_results == ["p2"]

