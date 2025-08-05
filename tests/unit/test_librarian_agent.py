from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from autogpt.config import Config
from autogpt.skills import library as library_module
from autogpt.skills.librarian import LibrarianAgent
from autogpt.telemetry import telemetry


def _setup_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LibrarianAgent:
    monkeypatch.setattr(
        "autogpt.skills.library.get_embedding", lambda _text, _config: [0.1, 0.2, 0.3]
    )
    monkeypatch.setattr(
        "autogpt.skills.librarian.SkillLibrary",
        lambda config: library_module.SkillLibrary(config, storage_path=tmp_path),
    )
    return LibrarianAgent(Config())


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


def test_add_skill_invalid_metadata_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()
    metadata.pop("skill_name")

    with caplog.at_level("ERROR"):
        with pytest.raises(ValueError):
            agent.add_skill(metadata, str(code_file))
    assert any("Invalid skill metadata" in rec.title for rec in caplog.records)


def test_add_skill_missing_code_path_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)

    metadata = _metadata()
    missing_path = tmp_path / "missing.py"

    with caplog.at_level("ERROR"):
        with pytest.raises(FileNotFoundError):
            agent.add_skill(metadata, str(missing_path))
    assert any("Skill code path is not a file" in rec.title for rec in caplog.records)


def test_find_skill_caches_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()
    assert agent.add_skill(metadata, str(code_file)) is True

    call_count = 0
    original_search = library_module.SkillLibrary.search

    def counting_search(
        self: library_module.SkillLibrary, query: str, top_k: int = 3
    ) -> list:
        nonlocal call_count
        call_count += 1
        return original_search(self, query, top_k=top_k)

    monkeypatch.setattr(library_module.SkillLibrary, "search", counting_search)

    agent.find_skill("Test skill")
    agent.find_skill("Test skill")

    assert call_count == 1


def test_find_skill_skips_missing_required_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)

    valid_meta = library_module.SkillMetadata(**_metadata())
    invalid_meta = {"skill_name": "bad", "version": "1.0"}

    skills = [
        SimpleNamespace(metadata=valid_meta),
        SimpleNamespace(metadata=invalid_meta),
    ]

    monkeypatch.setattr(
        library_module.SkillLibrary, "search", lambda self, q, top_k=3: skills
    )

    results = agent.find_skill("Test skill")

    assert results == [asdict(valid_meta)]


def test_find_skill_skips_non_mapping_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)

    valid_meta = library_module.SkillMetadata(**_metadata())
    skills = [
        SimpleNamespace(metadata=valid_meta),
        SimpleNamespace(metadata=object()),
    ]

    monkeypatch.setattr(
        library_module.SkillLibrary, "search", lambda self, q, top_k=3: skills
    )

    results = agent.find_skill("Test skill")

    assert results == [asdict(valid_meta)]


def test_find_skill_records_telemetry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()
    assert agent.add_skill(metadata, str(code_file)) is True

    telemetry.reset()

    # Successful search
    agent.find_skill("Test skill")

    # Failed search: force library search to return no results
    monkeypatch.setattr(
        library_module.SkillLibrary, "search", lambda self, q, top_k=3: []
    )
    agent.find_skill("Missing skill")

    counts = telemetry.get_counts()
    assert counts.get("find_skill.success", 0) == 1
    assert counts.get("find_skill.failure", 0) == 1
