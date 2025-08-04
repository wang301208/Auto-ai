"""Tests for :mod:`autogpt.skills.library`."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest

from autogpt.config import Config


def make_embedding_map() -> Dict[str, List[float]]:
    return {
        "description1\ncode1": [1.0, 0.0, 0.0],
        "description2\ncode2": [0.0, 1.0, 0.0],
        "description1": [1.0, 0.0, 0.0],
        "description2": [0.0, 1.0, 0.0],
    }


def test_skill_library_save_and_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from types import ModuleType

    # Stub out the heavy ``autogpt.memory.vector`` package to avoid optional deps
    repo_root = next(Path(p) for p in sys.path if p.endswith("AutoGPT-0.4.7"))
    vector_pkg = ModuleType("autogpt.memory.vector")
    vector_pkg.__path__ = [str(repo_root / "autogpt" / "memory" / "vector")]
    sys.modules.setdefault("autogpt.memory.vector", vector_pkg)

    from autogpt.skills.library import SkillLibrary  # imported after stubbing
    from autogpt.skills.vector_db import MemoryVectorDB

    config = Config()
    storage = tmp_path / "skills.json"
    vector_db = MemoryVectorDB()

    embeddings = make_embedding_map()

    def fake_get_embedding(text: str, _config: Config) -> List[float]:
        return embeddings[text]

    monkeypatch.setattr(
        "autogpt.skills.library.get_embedding", fake_get_embedding
    )

    library = SkillLibrary(config, storage_path=storage, vector_db=vector_db)

    library.add_skill("skill1", "code1", {"a": 1}, "description1")
    library.add_skill("skill2", "code2", {"b": 2}, "description2")

    # Ensure skills are persisted and retrievable
    assert storage.exists()
    assert library.get_skill("skill1")

    # Reload from disk to verify save/load cycle
    new_library = SkillLibrary(config, storage_path=storage, vector_db=MemoryVectorDB())

    results = new_library.search("description1", top_k=1)
    assert results and results[0].name == "skill1"

