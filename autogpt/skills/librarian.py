from __future__ import annotations

"""Agent wrapper around :class:`SkillLibrary` for managing skills."""

from dataclasses import asdict
from pathlib import Path
from typing import List

from autogpt.config import Config

from .library import SkillLibrary, SkillMetadata


class LibrarianAgent:
    """High level interface for managing the skill library."""

    def __init__(self, config: Config | None = None) -> None:
        self.skill_library = SkillLibrary(config or Config())

    # ------------------------------------------------------------------
    def find_skill(self, query: str, top_k: int = 3) -> List[dict]:
        """Search for skills matching ``query`` and return their metadata."""

        skills = self.skill_library.search(query, top_k=top_k)
        return [asdict(skill.metadata) for skill in skills]

    # ------------------------------------------------------------------
    def add_skill(self, skill_metadata: dict, skill_code_path: str) -> bool:
        """Add a new skill to the library.

        Parameters
        ----------
        skill_metadata: dict
            Metadata describing the skill. Must conform to :class:`SkillMetadata`.
        skill_code_path: str
            Path to the Python file containing the skill's code.
        """

        try:
            metadata = SkillMetadata(**skill_metadata)
        except TypeError:
            return False

        try:
            code = Path(skill_code_path).read_text(encoding="utf-8")
        except OSError:
            return False

        try:
            self.skill_library.add_skill(
                name=metadata.skill_name,
                version=metadata.version,
                code=code,
                parameters=metadata.parameters,
                description=metadata.description,
                tags=metadata.tags,
            )
            return True
        except Exception:
            return False
