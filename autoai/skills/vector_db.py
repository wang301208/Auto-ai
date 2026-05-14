from __future__ import annotations  # noqa: F401

"""Vector database provider abstraction for skill embeddings."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import chromadb
except ImportError:
    chromadb = None  # type: ignore[assignment]
try:
    import faiss
except ImportError:
    faiss = None  # type: ignore[assignment]
import json
try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

Embedding = List[float]


class VectorDBProvider(ABC):
    """向量数据库的抽象接口."""

    @abstractmethod
    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        """存储带有可选元数据的嵌入."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """从索引中移除嵌入."""

    @abstractmethod
    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        """返回给定嵌入最相似的``top_k``个键。"""

    @abstractmethod
    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        """返回存储的嵌入和元数据 for ``key`` if present."""

    def clear(self) -> None:  # pragma: no cover - optional method
        """从数据库中移除所有条目."""
        raise NotImplementedError


class MemoryVectorDB(VectorDBProvider):
    """简单的内存向量数据库实现."""

    def __init__(self, *_args, **_kwargs) -> None:
        self._index: Dict[str, Tuple[Embedding, Dict]] = {}

    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        self._index[key] = (embedding, metadata or {})

    def delete(self, key: str) -> None:
        self._index.pop(key, None)

    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        if not self._index:
            return []

        query_vec = np.array(embedding)
        results: List[Tuple[str, float]] = []
        for key, (vec, _) in self._index.items():
            stored_vec = np.array(vec)
            # cosine similarity
            score = float(
                np.dot(query_vec, stored_vec)
                / (np.linalg.norm(query_vec) * np.linalg.norm(stored_vec) + 1e-10)
            )
            results.append((key, score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        return self._index.get(key)

    def clear(self) -> None:
        self._index.clear()


class ChromaVectorDB(VectorDBProvider):
    """使用持久化ChromaDB集合的`VectorDBProvider`。"""

    def __init__(self, persist_path: Path, collection_name: str = "skills") -> None:
        self.persist_path = Path(persist_path)
        self._client = chromadb.PersistentClient(path=str(self.persist_path))
        self._collection = self._client.get_or_create_collection(collection_name)

    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        # chromadb doesn't overwrite existing ids on add, so 删除 first
        try:
            self._collection.delete(ids=[key])
        except Exception:
            pass
        self._collection.add(
            ids=[key], embeddings=[embedding], metadatas=[metadata or {}]
        )

    def delete(self, key: str) -> None:
        self._collection.delete(ids=[key])

    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        if top_k <= 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        dists = result.get("distances", [[]])[0]
        scores = [1.0 / (1.0 + d) for d in dists]
        return list(zip(ids, scores))

    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        result = self._collection.get(ids=[key], include=["embeddings", "metadatas"])
        if not result.get("ids"):
            return None
        embedding = result["embeddings"][0]
        metadata = result["metadatas"][0]
        return embedding, metadata

    def clear(self) -> None:
        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)


class FaissVectorDB(VectorDBProvider):
    """由FAISS索引和JSON元数据存储支持的`VectorDBProvider`。"""

    def __init__(self, persist_path: Path) -> None:
        self.persist_path = Path(persist_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.data_file = self.persist_path / "data.json"
        if self.data_file.exists():
            with self.data_file.open("r", encoding="utf-8") as f:
                self._data: Dict[str, Dict] = json.load(f)
        else:
            self._data = {}
        self._rebuild_index()

    # 内部 helpers -------------------------------------------------
    def _save(self) -> None:
        with self.data_file.open("w", encoding="utf-8") as f:
            json.dump(self._data, f)

    def _rebuild_index(self) -> None:
        if self._data:
            dim = len(next(iter(self._data.values()))["embedding"])
            self._index = faiss.IndexFlatIP(dim)
            embeddings = [v["embedding"] for v in self._data.values()]
            emb_array = np.array(embeddings, dtype="float32")
            faiss.normalize_L2(emb_array)
            self._index.add(emb_array)
            self._keys = list(self._data.keys())
        else:
            self._index = None
            self._keys = []

    # VectorDBProvider API ---------------------------------------------
    def add(self, key: str, embedding: Embedding, metadata: Dict | None = None) -> None:
        self._data[key] = {
            "embedding": list(map(float, embedding)),
            "metadata": metadata or {},
        }
        self._save()
        self._rebuild_index()

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._save()
            self._rebuild_index()

    def query(self, embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        if not self._index or not self._keys or top_k <= 0:
            return []
        vec = np.array([embedding], dtype="float32")
        faiss.normalize_L2(vec)
        scores, idxs = self._index.search(vec, top_k)
        results: List[Tuple[str, float]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if 0 <= idx < len(self._keys):
                results.append((self._keys[idx], float(score)))
        return results

    def get(self, key: str) -> Tuple[Embedding, Dict] | None:
        item = self._data.get(key)
        if item is None:
            return None
        return item["embedding"], item["metadata"]

    def clear(self) -> None:
        self._data.clear()
        self._save()
        self._rebuild_index()
