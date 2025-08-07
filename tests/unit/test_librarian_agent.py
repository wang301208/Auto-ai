from __future__ import annotations

import json
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
        "approved_by": "qa_tester",
        "approval_timestamp": "2024-01-02T00:00:00Z",
    }


def _create_plugin_spec(tmp_path: Path, name: str, policy: str) -> tuple[Path, Path]:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    source_file = plugin_dir / f"{name}.py"
    source_file.write_text("print('hi')\n")

    meta = {
        "name": name,
        "description": "Test plugin",
        "instructions": "",
        "underlying_library": {
            "name": "lib",
            "version": "0.1",
            "repo_url": "https://example.com/lib",
            "local_source_path": source_file.name,
        },
        "source_code_access_policy": policy,
    }
    (plugin_dir / f"{name}.json").write_text(json.dumps(meta))
    return plugin_dir, source_file


def test_add_and_find_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _setup_agent(tmp_path, monkeypatch)
    code_file = tmp_path / "skill.py"
    code_file.write_text("def run():\n    return 'hello'\n")

    metadata = _metadata()

    assert agent.add_skill(metadata, str(code_file)) is True

    results = agent.find_skill("Test skill")
    assert results == [metadata]

    skill_json = (
        tmp_path / f"{metadata['skill_name']}_{metadata['version']}" / "skill.json"
    )
    saved = json.loads(skill_json.read_text(encoding="utf-8"))
    assert saved["approved_by"] == metadata["approved_by"]
    assert saved["approval_timestamp"] == metadata["approval_timestamp"]


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


def test_get_source_code_path_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_dir, source_file = _create_plugin_spec(
        tmp_path, "allowed", "ALLOWED_FOR_READ_ONLY"
    )
    agent = _setup_agent(tmp_path, monkeypatch)
    agent.skill_library.config.plugins_dir = str(plugin_dir)

    telemetry.reset()
    path = agent.get_source_code_path("allowed")
    assert path == str(source_file)
    assert telemetry.get_counts().get("get_source_code_path.denied", 0) == 0


def test_get_source_code_path_restricted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    plugin_dir, _ = _create_plugin_spec(tmp_path, "restricted", "RESTRICTED")
    agent = _setup_agent(tmp_path, monkeypatch)
    agent.skill_library.config.plugins_dir = str(plugin_dir)

    telemetry.reset()
    with caplog.at_level("WARNING"):
        path = agent.get_source_code_path("restricted")
    assert path is None
    assert any(
        "Access to source code for plugin" in rec.message for rec in caplog.records
    )
    assert telemetry.get_counts().get("get_source_code_path.denied", 0) == 1
