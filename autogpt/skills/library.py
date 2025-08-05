from __future__ import annotations  # noqa: F401

"""Skill library for managing and searching tool scripts."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from autogpt.config import Config
from autogpt.memory.vector.utils import get_embedding

from .vector_db import Embedding, MemoryVectorDB, VectorDBProvider


@dataclass
class Skill:
    """Representation of an executable tool script."""

    name: str
    version: str
    code: str
    parameters: Dict
    description: str
    embedding: Embedding | None = None


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
        self.vector_db = vector_db or MemoryVectorDB()
        self._skills: Dict[str, Skill] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        for skill_dir in self.storage_path.iterdir():
            if not skill_dir.is_dir():
                continue
            meta_file = skill_dir / "skill.json"
            code_file = skill_dir / "main.py"
            if not meta_file.exists() or not code_file.exists():
                continue
            with meta_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            with code_file.open("r", encoding="utf-8") as f:
                code = f.read()
            skill = Skill(code=code, **data)
            key = f"{skill.name}_{skill.version}"
            self._skills[key] = skill
            if skill.embedding is not None:
                self.vector_db.add(
                    key,
                    skill.embedding,
                    {"description": skill.description, "parameters": skill.parameters},
                )

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
                    "name": skill.name,
                    "version": skill.version,
                    "parameters": skill.parameters,
                    "description": skill.description,
                    "embedding": skill.embedding,
                },
                f,
                indent=2,
            )
        return skill_dir

    def _git_commit(self, path: Path, message: str) -> None:
        repo = path.resolve()
        while repo != repo.parent and not (repo / ".git").exists():
            repo = repo.parent
        if not (repo / ".git").exists():
            return
        rel = path.resolve().relative_to(repo)
        try:
            subprocess.run(["git", "add", str(rel)], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=repo, check=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def add_skill(
        self, name: str, version: str, code: str, parameters: Dict, description: str
    ) -> Skill:
        """Create and persist a new skill."""

        skill = Skill(name, version, code, parameters, description)
        text = f"{description}\n{code}"
        embedding = get_embedding(text, self.config)
        skill.embedding = list(map(float, embedding))

        key = f"{name}_{version}"
        self._skills[key] = skill
        self.vector_db.add(
            key,
            skill.embedding,
            {"description": description, "parameters": parameters},
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
    ) -> Optional[Skill]:
        key = f"{name}_{version}"
        skill = self._skills.get(key)
        if not skill:
            return None

        if code is not None:
            skill.code = code
        if parameters is not None:
            skill.parameters = parameters
        if description is not None:
            skill.description = description

        text = f"{skill.description}\n{skill.code}"
        embedding = get_embedding(text, self.config)
        skill.embedding = list(map(float, embedding))
        self.vector_db.add(
            key,
            skill.embedding,
            {"description": skill.description, "parameters": skill.parameters},
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
