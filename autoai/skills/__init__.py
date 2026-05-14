from __future__ import annotations

"""Public API for the skills module."""

from pathlib import Path
from typing import Dict, List, Optional

from autoai.config import ConfigBuilder

from .librarian import LibrarianAgent
from .library import Skill, SkillLibrary
from .vector_db import ChromaVectorDB, MemoryVectorDB, VectorDBProvider

_default_library: SkillLibrary | None = None


def get_library() -> SkillLibrary:
    """返回默认的 :class:`SkillLibrary` 实例."""

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
    dependencies_file: str | None = None,
    entry_point: str | None = None,
    return_type: str | None = None,
    author_agent: str | None = None,
    creation_timestamp: str | None = None,
    approved_by: str | None = None,
    approval_timestamp: str | None = None,
    repo_path: str | Path | None = None,
) -> Skill:
    """向库中添加新技能."""

    return get_library().add_skill(
        name,
        version,
        code,
        parameters,
        description,
        tags,
        dependencies_file,
        entry_point,
        return_type,
        author_agent,
        creation_timestamp,
        approved_by,
        approval_timestamp,
        repo_path,
    )


def get(name: str, version: str) -> Optional[Skill]:
    """按名称/版本返回技能（如存在）."""

    return get_library().get_skill(name, version)


def update(
    name: str,
    version: str,
    code: str | None = None,
    parameters: Dict | None = None,
    description: str | None = None,
    tags: List[str] | None = None,
    dependencies_file: str | None = None,
    entry_point: str | None = None,
    return_type: str | None = None,
    author_agent: str | None = None,
    creation_timestamp: str | None = None,
    approved_by: str | None = None,
    approval_timestamp: str | None = None,
    repo_path: str | Path | None = None,
) -> Optional[Skill]:
    """更新现有技能."""

    return get_library().update_skill(
        name,
        version,
        code,
        parameters,
        description,
        tags,
        dependencies_file,
        entry_point,
        return_type,
        author_agent,
        creation_timestamp,
        approved_by,
        approval_timestamp,
        repo_path,
    )


def delete(name: str, version: str, repo_path: str | Path | None = None) -> None:
    """从库中移除技能."""

    get_library().delete_skill(name, version, repo_path=repo_path)


def reindex() -> None:
    """从磁盘重建技能库索引."""

    get_library().reindex()


def list_skills() -> List[Skill]:
    """返回所有存储的技能."""

    return get_library().list_skills()


def search(query: str, top_k: int = 5) -> List[Skill]:
    """语义搜索匹配的技能 ``query``."""

    return get_library().search(query, top_k=top_k)


__all__ = [
    "Skill",
    "SkillLibrary",
    "LibrarianAgent",
    "VectorDBProvider",
    "MemoryVectorDB",
    "ChromaVectorDB",
    "get_library",
    "add",
    "get",
    "update",
    "delete",
    "reindex",
    "list_skills",
    "search",
]
