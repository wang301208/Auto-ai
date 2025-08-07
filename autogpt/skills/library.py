from __future__ import annotations  # noqa: F401

"""Skill library for managing and searching tool scripts."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional

from autogpt.config import Config
from autogpt.memory.vector.utils import get_embedding

from .vector_db import (
    ChromaVectorDB,
    Embedding,
    FaissVectorDB,
    MemoryVectorDB,
    VectorDBProvider,
)


@dataclass
class SkillMetadata:
    """Metadata describing a skill."""

    skill_name: str
    version: str
    description: str
    tags: List[str]
    parameters: Dict
    dependencies_file: str | None = None
    entry_point: str | None = None
    return_type: str | None = None
    author_agent: str | None = None
    creation_timestamp: str | None = None
    approved_by: str | None = None
    approval_timestamp: str | None = None


@dataclass
class Skill:
    """Representation of an executable tool script with metadata."""

    metadata: SkillMetadata
    code: str
    embedding: Embedding | None = None

    @property
    def name(self) -> str:  # pragma: no cover - simple delegation
        return self.metadata.skill_name

    @property
    def version(self) -> str:  # pragma: no cover - simple delegation
        return self.metadata.version

    @property
    def description(self) -> str:  # pragma: no cover - simple delegation
        return self.metadata.description

    @property
    def tags(self) -> List[str]:  # pragma: no cover - simple delegation
        return self.metadata.tags

    @property
    def parameters(self) -> Dict:  # pragma: no cover - simple delegation
        return self.metadata.parameters


class SkillLibrary:
    """Persist and index skills for semantic search."""

    def __init__(
        self,
        config: Config,
        storage_path: Path | None = None,
        vector_db: VectorDBProvider | None = None,
    ) -> None:
        self.config = config
        self.storage_path = storage_path or Path("skill_library")
        if vector_db is not None:
            self.vector_db = vector_db
        else:
            provider = getattr(config, "skill_db_provider", "memory").lower()
            if provider == "chroma":
                persist = self.storage_path / "chroma"
                self.vector_db = ChromaVectorDB(persist)
            elif provider == "faiss":
                persist = self.storage_path / "faiss"
                self.vector_db = FaissVectorDB(persist)
            else:
                self.vector_db = MemoryVectorDB()
        self._skills: Dict[str, Skill] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return

        # Walk the entire storage path looking for skill definitions
        for meta_file in self.storage_path.rglob("skill.json"):
            skill_dir = meta_file.parent
            if not skill_dir.is_dir():
                continue
            code_file = skill_dir / "main.py"
            if not code_file.exists():
                continue

            with meta_file.open("r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
            metadata = SkillMetadata(**metadata_dict)
            with code_file.open("r", encoding="utf-8") as f:
                code = f.read()
            skill = Skill(metadata=metadata, code=code)

            key = f"{skill.name}_{skill.version}"
            text = f"{skill.description}\n{' '.join(skill.tags)}"
            embedding = get_embedding(text, self.config)
            skill.embedding = list(map(float, embedding))
            self._skills[key] = skill
            self.vector_db.add(
                key,
                skill.embedding,
                {
                    "description": skill.description,
                    "tags": skill.tags,
                    "parameters": skill.parameters,
                },
            )

    def reindex(self) -> None:
        """Clear and rebuild the in-memory index and vector database."""

        self._skills.clear()
        try:
            self.vector_db.clear()
        except Exception:
            try:
                self.vector_db = type(self.vector_db)()
            except Exception:
                self.vector_db = MemoryVectorDB()
        self._load()

    def _skill_dir(self, name: str, version: str) -> Path:
        return self.storage_path / f"{name}_{version}"

    def _write_skill(self, skill: Skill) -> Path:
        skill_dir = self._skill_dir(skill.name, skill.version)
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "main.py").write_text(skill.code, encoding="utf-8")
        (skill_dir / "test_main.py").touch()
        (skill_dir / "requirements.txt").touch()
        with (skill_dir / "skill.json").open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "skill_name": skill.name,
                    "version": skill.version,
                    "description": skill.description,
                    "tags": skill.tags,
                    "parameters": skill.parameters,
                    "dependencies_file": skill.metadata.dependencies_file,
                    "entry_point": skill.metadata.entry_point,
                    "return_type": skill.metadata.return_type,
                    "author_agent": skill.metadata.author_agent,
                    "creation_timestamp": skill.metadata.creation_timestamp,
                    "approved_by": skill.metadata.approved_by,
                    "approval_timestamp": skill.metadata.approval_timestamp,
                },
                f,
                indent=2,
            )
        return skill_dir

    def _git_commit(
        self, path: Path, message: str, branch_name: str | None = None
    ) -> None:
        repo = path.resolve()
        while repo != repo.parent and not (repo / ".git").exists():
            repo = repo.parent
        if not (repo / ".git").exists():
            return
        rel = path.resolve().relative_to(repo)
        try:
            subprocess.run(["git", "add", str(rel)], cwd=repo, check=True)
            commit_proc = subprocess.run(
                ["git", "commit", "-m", message], cwd=repo, check=False
            )
            if commit_proc.returncode != 0:
                return
            if branch_name is None:
                branch_name = getattr(self.config, "git_branch", None)
            if branch_name is None:
                branch_name = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            from autogpt.commands.git_operations import git_push

            agent = SimpleNamespace(config=self.config)
            result = git_push(str(repo), branch_name, agent)
            if isinstance(result, str) and result.startswith("Error"):
                print(result)
        except Exception as e:
            print(f"Error: {e}")

    # ------------------------------------------------------------------
    def add_skill(
        self,
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
    ) -> Skill:
        """Create and persist a new skill."""

        metadata = SkillMetadata(
            name,
            version,
            description,
            tags,
            parameters,
            dependencies_file,
            entry_point,
            return_type,
            author_agent,
            creation_timestamp,
            approved_by,
            approval_timestamp,
        )
        skill = Skill(metadata=metadata, code=code)
        text = f"{description}\n{' '.join(tags)}"
        embedding = get_embedding(text, self.config)
        skill.embedding = list(map(float, embedding))

        key = f"{name}_{version}"
        self._skills[key] = skill
        self.vector_db.add(
            key,
            skill.embedding,
            {"description": description, "tags": tags, "parameters": parameters},
        )
        skill_dir = self._write_skill(skill)
        self._git_commit(skill_dir, f"Add skill {name} {version}")
        return skill

    def get_skill(self, name: str, version: str) -> Optional[Skill]:
        return self._skills.get(f"{name}_{version}")

    def update_skill(
        self,
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
    ) -> Optional[Skill]:
        key = f"{name}_{version}"
        skill = self._skills.get(key)
        if not skill:
            return None

        if code is not None:
            skill.code = code
        if parameters is not None:
            skill.metadata.parameters = parameters
        if description is not None:
            skill.metadata.description = description
        if tags is not None:
            skill.metadata.tags = tags
        if dependencies_file is not None:
            skill.metadata.dependencies_file = dependencies_file
        if entry_point is not None:
            skill.metadata.entry_point = entry_point
        if return_type is not None:
            skill.metadata.return_type = return_type
        if author_agent is not None:
            skill.metadata.author_agent = author_agent
        if creation_timestamp is not None:
            skill.metadata.creation_timestamp = creation_timestamp
        if approved_by is not None:
            skill.metadata.approved_by = approved_by
        if approval_timestamp is not None:
            skill.metadata.approval_timestamp = approval_timestamp

        text = f"{skill.description}\n{' '.join(skill.tags)}"
        embedding = get_embedding(text, self.config)
        skill.embedding = list(map(float, embedding))
        self.vector_db.add(
            key,
            skill.embedding,
            {
                "description": skill.description,
                "tags": skill.tags,
                "parameters": skill.parameters,
            },
        )
        skill_dir = self._write_skill(skill)
        self._git_commit(skill_dir, f"Update skill {name} {version}")
        return skill

    def delete_skill(self, name: str, version: str) -> None:
        key = f"{name}_{version}"
        if key in self._skills:
            del self._skills[key]
            self.vector_db.delete(key)
            skill_dir = self._skill_dir(name, version)
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
                self._git_commit(skill_dir, f"Delete skill {name} {version}")

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def search(self, query: str, top_k: int = 5) -> List[Skill]:
        """Search for skills semantically matching ``query``."""

        embedding = get_embedding(query, self.config)
        results = self.vector_db.query(list(map(float, embedding)), top_k=top_k)
        return [self._skills[key] for key, _ in results if key in self._skills]
