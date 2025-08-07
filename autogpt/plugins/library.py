"""Library for discovering and searching plugin specifications."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from autogpt.config import Config
from autogpt.memory.vector.utils import get_embedding
from autogpt.skills.vector_db import ChromaVectorDB, MemoryVectorDB, VectorDBProvider


# ---------------------------------------------------------------------------
# Data models


Embedding = List[float]


@dataclass
class PluginSpec:
    """Representation of a plugin specification with optional embedding."""

    name: str
    description: str
    tags: List[str]
    spec: Dict
    embedding: Embedding | None = None


class PluginLibrary:
    """Persist and index plugin specifications for semantic search."""

    def __init__(
        self,
        config: Config,
        repo_path: Path,
        vector_db: VectorDBProvider | None = None,
    ) -> None:
        self.config = config
        self.repo_path = Path(repo_path)
        if vector_db is not None:
            self.vector_db = vector_db
        else:
            persist = self.repo_path / "chroma"
            self.vector_db = ChromaVectorDB(persist, collection_name="plugins")
        self._plugins: Dict[str, PluginSpec] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        """Load all ``*.spec.json`` files from ``repo_path``."""

        if not self.repo_path.exists():
            return

        for spec_file in self.repo_path.rglob("*.spec.json"):
            try:
                with spec_file.open("r", encoding="utf-8") as f:
                    spec = json.load(f)
            except Exception:
                continue
            name = spec.get("name")
            if not name:
                continue
            description = spec.get("description", "")
            tags = spec.get("tags", [])
            plugin = PluginSpec(name=name, description=description, tags=tags, spec=spec)
            text = f"{description}\n{' '.join(tags)}"
            embedding = get_embedding(text, self.config)
            plugin.embedding = list(map(float, embedding))
            self._plugins[name] = plugin
            self.vector_db.add(
                name,
                plugin.embedding,
                {"description": description, "tags": tags},
            )

    # ------------------------------------------------------------------
    def reindex(self) -> None:
        """Clear and rebuild the in-memory index and vector database."""

        self._plugins.clear()
        try:
            self.vector_db.clear()
        except Exception:
            self.vector_db = MemoryVectorDB()
        self._load()

    # ------------------------------------------------------------------
    def get_plugin(self, name: str) -> Optional[PluginSpec]:
        """Return plugin specification by name if present."""

        return self._plugins.get(name)

    # ------------------------------------------------------------------
    def list_plugins(self) -> List[PluginSpec]:
        """Return all loaded plugin specifications."""

        return list(self._plugins.values())

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> List[PluginSpec]:
        """Search for plugins semantically matching ``query``."""

        embedding = get_embedding(query, self.config)
        results = self.vector_db.query(list(map(float, embedding)), top_k=top_k)
        return [self._plugins[key] for key, _ in results if key in self._plugins]


__all__ = ["PluginSpec", "PluginLibrary"]

