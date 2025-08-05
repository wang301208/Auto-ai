from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from autogpt.config import Config
from autogpt.skills.librarian import LibrarianAgent
from autogpt.skills.library import SkillMetadata


def _setup_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LibrarianAgent:
    agent = LibrarianAgent(Config())
    agent.skill_library.storage_path = tmp_path
    monkeypatch.setattr(
        "autogpt.skills.library.get_embedding", lambda _text, _config: [0.1, 0.2, 0.3]
    )
    return agent


def _metadata() -> dict:
    return {
        "skill_name": "test_skill",
        "version": "1.0",
        "description": "Test skill",
        "tags": ["test"],
        "parameters": {"param": "value"},
        "dependencies_file": "requirements.txt",
        "entry_point": "main:run",
        "return_type": "str",
        "author_agent": "tester",
        "creation_timestamp": "2024-01-01T00:00:00Z",
    }


def test_add_and_find_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()

    assert agent.add_skill(metadata, str(code_file)) is True

    results = agent.find_skill("Test skill")
    assert results == [metadata]


def test_add_skill_invalid_metadata_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()
    metadata.pop("skill_name")

    assert agent.add_skill(metadata, str(code_file)) is False


def test_add_skill_missing_code_path_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)

    metadata = _metadata()
    missing_path = tmp_path / "missing.py"

    assert agent.add_skill(metadata, str(missing_path)) is False


def test_find_skill_uses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()
    assert agent.add_skill(metadata, str(code_file)) is True

    calls = 0

    def fake_search(query: str, top_k: int = 3):
        nonlocal calls
        calls += 1
        return [SimpleNamespace(metadata=SkillMetadata(**metadata))]

    monkeypatch.setattr(agent.skill_library, "search", fake_search)

    res1 = agent.find_skill("Test skill")
    res2 = agent.find_skill("Test skill")

    assert res1 == res2 == [metadata]
    assert calls == 1
