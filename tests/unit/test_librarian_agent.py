from __future__ import annotations

import json
from pathlib import Path

import pytest

from autogpt.config import Config
from autogpt.skills.librarian import LibrarianAgent


def test_add_skill_persists_full_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = LibrarianAgent(Config())
    agent.skill_library.storage_path = tmp_path
    monkeypatch.setattr(
        "autogpt.skills.library.get_embedding",
        lambda _text, _config: [0.0, 0.0, 0.0],
    )

    code_file = tmp_path / "skill.py"
    code_file.write_text(
        """def run():
    return 'hello'
"""
    )

    metadata = {
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

    assert agent.add_skill(metadata, str(code_file))

    skill_json = tmp_path / "test_skill_1.0" / "skill.json"
    with skill_json.open("r", encoding="utf-8") as f:
        stored = json.load(f)

    assert stored == metadata
