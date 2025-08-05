"""Tests for the SkillLibrary acting as a skill repository."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from autogpt.config import Config
from autogpt.skills.vector_db import VectorDBProvider


class DummyVectorDB(VectorDBProvider):
    """Minimal vector DB storing embeddings in memory."""

    def __init__(self) -> None:
        self.store: Dict[str, Tuple[List[float], Dict]] = {}

    def add(
        self, key: str, embedding: List[float], metadata: Dict | None = None
    ) -> None:
        self.store[key] = (embedding, metadata or {})

    def delete(self, key: str) -> None:
        self.store.pop(key, None)

    def query(self, embedding: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        results: List[Tuple[str, float]] = []
        for key, (vec, _) in self.store.items():
            score = sum(a * b for a, b in zip(vec, embedding))
            results.append((key, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get(self, key: str) -> Tuple[List[float], Dict] | None:
        return self.store.get(key)


def make_embedding_map() -> Dict[str, List[float]]:
    return {
        "description1\ntag1": [1.0, 0.0, 0.0],
        "description2\ntag2": [0.0, 1.0, 0.0],
        "description1": [1.0, 0.0, 0.0],
        "description2": [0.0, 1.0, 0.0],
        "tag1": [1.0, 0.0, 0.0],
        "tag2": [0.0, 1.0, 0.0],
    }


def test_repository_saves_structure_and_parses_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    from types import ModuleType

    # Stub out heavy optional dependencies
    repo_root = next(Path(p) for p in sys.path if p.endswith("AutoGPT-0.4.7"))
    vector_pkg = ModuleType("autogpt.memory.vector")
    vector_pkg.__path__ = [str(repo_root / "autogpt" / "memory" / "vector")]
    sys.modules.setdefault("autogpt.memory.vector", vector_pkg)
    sys.modules.setdefault("spacy", ModuleType("spacy"))

    from autogpt.skills.library import SkillLibrary

    monkeypatch.setattr(SkillLibrary, "_git_commit", lambda *_, **__: None)

    embeddings = make_embedding_map()

    def fake_get_embedding(text: str, _config: Config) -> List[float]:
        return embeddings[text]

    monkeypatch.setattr("autogpt.skills.library.get_embedding", fake_get_embedding)

    config = Config()
    storage = tmp_path / "skills"
    library = SkillLibrary(config, storage_path=storage, vector_db=DummyVectorDB())

    library.add_skill(
        "skill1", "1.0", "print('hi')", {"a": 1}, "description1", ["tag1"]
    )

    skill_dir = storage / "skill1_1.0"
    assert skill_dir.exists()
    assert (skill_dir / "main.py").exists()
    assert (skill_dir / "test_main.py").exists()
    assert (skill_dir / "requirements.txt").exists()
    assert (skill_dir / "skill.json").exists()

    with (skill_dir / "skill.json").open() as f:
        meta = json.load(f)
    assert meta == {
        "skill_name": "skill1",
        "version": "1.0",
        "description": "description1",
        "tags": ["tag1"],
        "parameters": {"a": 1},
    }

    # Reload repository to ensure metadata is parsed from disk
    new_library = SkillLibrary(config, storage_path=storage, vector_db=DummyVectorDB())
    skill = new_library.get_skill("skill1", "1.0")
    assert skill and skill.description == "description1"
    assert skill.tags == ["tag1"]


def test_repository_search_by_description_and_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    from types import ModuleType

    repo_root = next(Path(p) for p in sys.path if p.endswith("AutoGPT-0.4.7"))
    vector_pkg = ModuleType("autogpt.memory.vector")
    vector_pkg.__path__ = [str(repo_root / "autogpt" / "memory" / "vector")]
    sys.modules.setdefault("autogpt.memory.vector", vector_pkg)
    sys.modules.setdefault("spacy", ModuleType("spacy"))

    from autogpt.skills.library import SkillLibrary

    monkeypatch.setattr(SkillLibrary, "_git_commit", lambda *_, **__: None)

    embeddings = make_embedding_map()

    def fake_get_embedding(text: str, _config: Config) -> List[float]:
        return embeddings[text]

    monkeypatch.setattr("autogpt.skills.library.get_embedding", fake_get_embedding)

    config = Config()
    storage = tmp_path / "skills"
    library = SkillLibrary(config, storage_path=storage, vector_db=DummyVectorDB())

    library.add_skill("skill1", "1.0", "code1", {}, "description1", ["tag1"])
    library.add_skill("skill2", "1.0", "code2", {}, "description2", ["tag2"])

    results = library.search("description1", top_k=1)
    assert results and results[0].name == "skill1"

    tag_results = library.search("tag2", top_k=1)
    assert tag_results and tag_results[0].name == "skill2"
