from __future__ import annotations

"""Agent wrapper around :class:`SkillLibrary` for managing skills."""

import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from autogpt.config import Config
from autogpt.logs import logger

from .library import SkillLibrary, SkillMetadata


class LibrarianAgent:
    """High level interface for managing the skill library."""

    def __init__(self, config: Config | None = None) -> None:
        self.skill_library = SkillLibrary(config or Config())
        # Cache search results to avoid redundant library queries for repeated
        # requests. This keeps ``find_skill`` simple and synchronous while
        # still improving performance for common lookups.
        self._search_cache: Dict[Tuple[str, int], List[dict]] = {}

    # ------------------------------------------------------------------
    def find_skill(self, query: str, top_k: int = 3) -> List[dict]:
        """Search for skills matching ``query`` and return their metadata.

        Results are cached by ``query``/``top_k`` combination so repeated
        invocations avoid hitting the underlying :class:`SkillLibrary`.
        """

        cache_key = (query, top_k)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        skills = self.skill_library.search(query, top_k=top_k)
        top_metadata = asdict(skills[0].metadata) if skills else None
        logger.debug(f"Skill search query: {query}, top result: {top_metadata}")
        results = [asdict(skill.metadata) for skill in skills]
        self._search_cache[cache_key] = results
        return results

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
            # Provided metadata does not match the expected schema
            return False

        source = Path(skill_code_path)
        if not source.is_file():
            return False

        # Copy the code into the skill library directory
        dest_dir = (
            self.skill_library.storage_path
            / f"{metadata.skill_name}_{metadata.version}"
        )
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / "main.py"
            shutil.copy2(source, dest_file)
            code = dest_file.read_text(encoding="utf-8")
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
                dependencies_file=metadata.dependencies_file,
                entry_point=metadata.entry_point,
                return_type=metadata.return_type,
                author_agent=metadata.author_agent,
                creation_timestamp=metadata.creation_timestamp,
            )
            return True
        except Exception:
            return False
