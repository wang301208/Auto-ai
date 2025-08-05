from __future__ import annotations

"""Public API for the skills module."""

from pathlib import Path
from typing import Dict, List, Optional

from autogpt.config import ConfigBuilder

from .library import Skill, SkillLibrary
from .vector_db import MemoryVectorDB, VectorDBProvider

_default_library: SkillLibrary | None = None


def get_library() -> SkillLibrary:
    """Return a default :class:`SkillLibrary` instance."""

    global _default_library
    if _default_library is None:
        config = ConfigBuilder.build_config_from_env(Path.cwd())
        _default_library = SkillLibrary(config)
    return _default_library


def add(
    name: str,
    version: str,
    code: str,
    parameters: Dict,
    description: str,
    tags: List[str],
) -> Skill:
    """Add a new skill to the library."""

    return get_library().add_skill(name, version, code, parameters, description, tags)


def get(name: str, version: str) -> Optional[Skill]:
    """Return a skill by name/version if it exists."""

    return get_library().get_skill(name, version)


def update(
    name: str,
    version: str,
    code: str | None = None,
    parameters: Dict | None = None,
    description: str | None = None,
    tags: List[str] | None = None,
) -> Optional[Skill]:
    """Update an existing skill."""

    return get_library().update_skill(name, version, code, parameters, description, tags)


def delete(name: str, version: str) -> None:
    """Remove a skill from the library."""

    get_library().delete_skill(name, version)


def list_skills() -> List[Skill]:
    """Return all stored skills."""

    return get_library().list_skills()


def search(query: str, top_k: int = 5) -> List[Skill]:
    """Search for skills semantically matching ``query``."""

    return get_library().search(query, top_k=top_k)


__all__ = [
    "Skill",
    "SkillLibrary",
    "VectorDBProvider",
    "MemoryVectorDB",
    "get_library",
    "add",
    "get",
    "update",
    "delete",
    "list_skills",
    "search",
]
