"""Tests for :mod:`autogpt.skills.library`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

from autogpt.config import Config


def make_embedding_map() -> Dict[str, List[float]]:
    return {
        "description1\ntag1": [1.0, 0.0, 0.0],
        "description2\ntag2": [0.0, 1.0, 0.0],
        "description1": [1.0, 0.0, 0.0],
        "description2": [0.0, 1.0, 0.0],
        "tag1": [1.0, 0.0, 0.0],
        "tag2": [0.0, 1.0, 0.0],
    }


def test_skill_library_save_and_search(
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

    from autogpt.skills.library import SkillLibrary  # imported after stubbing
    from autogpt.skills.vector_db import MemoryVectorDB

    config = Config()
    storage = tmp_path / "skill_library"
    vector_db = MemoryVectorDB()

    embeddings = make_embedding_map()

    def fake_get_embedding(text: str, _config: Config) -> List[float]:
        return embeddings[text]

    monkeypatch.setattr("autogpt.skills.library.get_embedding", fake_get_embedding)

    library = SkillLibrary(config, storage_path=storage, vector_db=vector_db)

    library.add_skill(
        "skill1",
        "1.0",
        "code1",
        {"a": 1},
        "description1",
        ["tag1"],
        dependencies_file="reqs1.txt",
        entry_point="main:run",
        return_type="int",
        author_agent="agent1",
        creation_timestamp="2024-01-01T00:00:00Z",
    )
    library.add_skill("skill2", "1.0", "code2", {"b": 2}, "description2", ["tag2"])

    # Ensure skills are persisted and retrievable
    assert storage.exists()
    assert (storage / "skill1_1.0" / "main.py").exists()
    with (storage / "skill1_1.0" / "skill.json").open() as f:
        meta = json.load(f)
    assert meta["skill_name"] == "skill1"
    assert meta["tags"] == ["tag1"]
    assert meta["dependencies_file"] == "reqs1.txt"
    assert meta["entry_point"] == "main:run"
    assert meta["return_type"] == "int"
    assert meta["author_agent"] == "agent1"
    assert meta["creation_timestamp"] == "2024-01-01T00:00:00Z"
    skill1 = library.get_skill("skill1", "1.0")
    assert skill1
    assert skill1.metadata.entry_point == "main:run"

    # Reload from disk to verify save/load cycle
    new_library = SkillLibrary(config, storage_path=storage, vector_db=MemoryVectorDB())
    reloaded = new_library.get_skill("skill1", "1.0")
    assert reloaded and reloaded.metadata.author_agent == "agent1"

    results = new_library.search("description1", top_k=1)
    assert results and results[0].name == "skill1"

    tag_results = new_library.search("tag2", top_k=1)
    assert tag_results and tag_results[0].name == "skill2"


def test_skill_library_reindex_and_nested_loading(
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
    from autogpt.skills.vector_db import MemoryVectorDB

    config = Config()
    storage = tmp_path / "skill_library"
    vector_db = MemoryVectorDB()

    embeddings = make_embedding_map()

    def fake_get_embedding(text: str, _config: Config) -> List[float]:
        return embeddings[text]

    monkeypatch.setattr("autogpt.skills.library.get_embedding", fake_get_embedding)

    nested_dir = storage / "nested" / "skill3_1.0"
    nested_dir.mkdir(parents=True)
    (nested_dir / "main.py").write_text("code3")
    (nested_dir / "skill.json").write_text(
        json.dumps(
            {
                "skill_name": "skill3",
                "version": "1.0",
                "description": "description1",
                "tags": ["tag1"],
                "parameters": {},
                "author_agent": "author3",
            }
        )
    )

    library = SkillLibrary(config, storage_path=storage, vector_db=vector_db)
    assert library.get_skill("skill3", "1.0")

    new_dir = storage / "nested2" / "skill4_1.0"
    new_dir.mkdir(parents=True)
    (new_dir / "main.py").write_text("code4")
    (new_dir / "skill.json").write_text(
        json.dumps(
            {
                "skill_name": "skill4",
                "version": "1.0",
                "description": "description2",
                "tags": ["tag2"],
                "parameters": {},
                "creation_timestamp": "2024-02-02T00:00:00Z",
            }
        )
    )

    library.reindex()
    skill4 = library.get_skill("skill4", "1.0")
    assert skill4 and skill4.metadata.creation_timestamp == "2024-02-02T00:00:00Z"
    results = library.search("description2", top_k=1)
    assert results and results[0].name == "skill4"
