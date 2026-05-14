"""发现和搜索插件规格的库。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from autoai.config import Config
from autoai.memory.vector.utils import get_embedding
from autoai.skills.vector_db import ChromaVectorDB, MemoryVectorDB, VectorDBProvider


# ---------------------------------------------------------------------------
# 数据模型s


Embedding = List[float]


@dataclass
class PluginSpec:
    """带有可选嵌入的插件规格表示。"""

    id: str
    description: str
    tags: List[str]
    spec: Dict
    embedding: Embedding | None = None


class PluginLibrary:
    """持久化并索引插件规格以支持语义搜索。"""

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
        """从``repo_path``加载所有``*.spec.json``文件。"""

        if not self.repo_path.exists():
            return

        for spec_file in self.repo_path.rglob("*.spec.json"):
            try:
                with spec_file.open("r", encoding="utf-8") as f:
                    spec = json.load(f)
            except Exception:
                continue
            plugin_id = spec.get("id") or spec.get("name")
            if not plugin_id:
                continue
            description = spec.get("description", "")
            tags = spec.get("tags", [])
            plugin = PluginSpec(id=plugin_id, description=description, tags=tags, spec=spec)
            text = f"{description}\n{' '.join(tags)}"
            embedding = get_embedding(text, self.config)
            plugin.embedding = list(map(float, embedding))
            self._plugins[plugin_id] = plugin
            self.vector_db.add(
                plugin_id,
                plugin.embedding,
                {"description": description, "tags": tags},
            )

    # ------------------------------------------------------------------
    def reindex(self) -> None:
        """清除并重建内存索引和向量数据库."""

        self._plugins.clear()
        try:
            self.vector_db.clear()
        except Exception:
            self.vector_db = MemoryVectorDB()
        self._load()

    # ------------------------------------------------------------------
    def get_plugin(self, plugin_id: str) -> Optional[PluginSpec]:
        """如存在则按标识符返回插件规格。"""

        return self._plugins.get(plugin_id)

    # ------------------------------------------------------------------
    def list_plugins(self) -> List[PluginSpec]:
        """返回所有已加载的插件规格。"""

        return list(self._plugins.values())

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> List[str]:
        """Search for plugins semantically 匹配 ``query`` and return their IDs."""

        embedding = get_embedding(query, self.config)
        results = self.vector_db.query(list(map(float, embedding)), top_k=top_k)
        return [key for key, _ in results if key in self._plugins]


__all__ = ["PluginSpec", "PluginLibrary"]

