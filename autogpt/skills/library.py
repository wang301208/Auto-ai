from __future__ import annotations  # noqa: F401

"""Skill library for managing and searching tool scripts."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from autogpt.config import Config
from autogpt.memory.vector.utils import get_embedding

from .vector_db import Embedding, MemoryVectorDB, VectorDBProvider


@dataclass
class Skill:
    """Representation of an executable tool script."""

    name: str
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
        self.storage_path = storage_path or Path("data/skills.json")
        self.vector_db = vector_db or MemoryVectorDB()
        self._skills: Dict[str, Skill] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        with self.storage_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            skill = Skill(**item)
            self._skills[skill.name] = skill
            if skill.embedding is not None:
                self.vector_db.add(
                    skill.name,
                    skill.embedding,
                    {"description": skill.description, "parameters": skill.parameters},
                )

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self._skills.values()], f, indent=2)

    # ------------------------------------------------------------------
    def add_skill(
        self, name: str, code: str, parameters: Dict, description: str
    ) -> Skill:
        """Create and persist a new skill."""

        skill = Skill(name, code, parameters, description)
        text = f"{description}\n{code}"
        embedding = get_embedding(text, self.config)
        skill.embedding = list(map(float, embedding))

        self._skills[name] = skill
        self.vector_db.add(
            name,
            skill.embedding,
            {"description": description, "parameters": parameters},
        )
        self._save()
        return skill

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def update_skill(
        self,
        name: str,
        code: str | None = None,
        parameters: Dict | None = None,
        description: str | None = None,
    ) -> Optional[Skill]:
        skill = self._skills.get(name)
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
            name,
            skill.embedding,
            {"description": skill.description, "parameters": skill.parameters},
        )
        self._save()
        return skill

    def delete_skill(self, name: str) -> None:
        if name in self._skills:
            del self._skills[name]
            self.vector_db.delete(name)
            self._save()

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def search(self, query: str, top_k: int = 5) -> List[Skill]:
        """Search for skills semantically matching ``query``."""

        embedding = get_embedding(query, self.config)
        results = self.vector_db.query(list(map(float, embedding)), top_k=top_k)
        return [self._skills[key] for key, _ in results if key in self._skills]
