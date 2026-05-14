"""制品缓存工具。"""

from __future__ import annotations

import json
import sqlite3
import time
import difflib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

Embedding = List[float]


@dataclass
class Artifact:
    """存储制品的表示。"""

    task_signature: str
    artifact_type: str
    content: str
    metadata: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    embedding: Optional[Embedding] = None


class CacheBackend:
    """抽象缓存后端。"""

    def save(self, artifact: Artifact) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def load_all(self) -> Iterable[Artifact]:  # pragma: no cover - interface
        raise NotImplementedError

    def delete(self, artifact: Artifact) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class DiskCacheBackend(CacheBackend):
    """将制品作为JSON文件持久化到磁盘。"""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # Internal -----------------------------------------------------------------
    def _artifact_path(self, artifact: Artifact) -> Path:
        safe_ts = int(artifact.timestamp * 1000)
        fname = f"{safe_ts}_{artifact.artifact_type}.json"
        return self.storage_dir / fname

    # Cache后端end methods ------------------------------------------------------
    def save(self, artifact: Artifact) -> None:
        path = self._artifact_path(artifact)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(artifact), f, indent=2)

    def load_all(self) -> Iterable[Artifact]:
        for file in self.storage_dir.glob("*.json"):
            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            yield Artifact(**data)

    def delete(self, artifact: Artifact) -> None:
        path = self._artifact_path(artifact)
        if path.exists():
            path.unlink()


class SQLiteCacheBackend(CacheBackend):
    """在SQLite数据库中存储制品。"""

    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                task_signature TEXT,
                artifact_type TEXT,
                content TEXT,
                metadata TEXT,
                timestamp REAL,
                embedding TEXT
            )
            """
        )
        self.conn.commit()

    def save(self, artifact: Artifact) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?)",
            (
                artifact.task_signature,
                artifact.artifact_type,
                artifact.content,
                json.dumps(artifact.metadata),
                artifact.timestamp,
                json.dumps(artifact.embedding),
            ),
        )
        self.conn.commit()

    def load_all(self) -> Iterable[Artifact]:
        cur = self.conn.cursor()
        for row in cur.execute(
            "SELECT task_signature, artifact_type, content, metadata, timestamp, embedding FROM artifacts"
        ):
            yield Artifact(
                task_signature=row[0],
                artifact_type=row[1],
                content=row[2],
                metadata=json.loads(row[3] or "{}"),
                timestamp=row[4],
                embedding=json.loads(row[5]) if row[5] else None,
            )

    def delete(self, artifact: Artifact) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM artifacts WHERE task_signature=? AND timestamp=?",
            (artifact.task_signature, artifact.timestamp),
        )
        self.conn.commit()


@dataclass
class RetentionPolicy:
    """存储制品的保留策略。"""

    max_entries: Optional[int] = None
    max_age_seconds: Optional[int] = None


class CacheManager:
    """用于存储和检索制品的高级缓存接口。"""

    def __init__(
        self,
        backend: CacheBackend,
        retention: RetentionPolicy | None = None,
        embedding_func: Callable[[str], Embedding] | None = None,
    ) -> None:
        self.backend = backend
        self.retention = retention or RetentionPolicy()
        self.embedding_func = embedding_func
        # 缓存 in 内存
        self._artifacts: List[Artifact] = list(self.backend.load_all())
        self._prune()

    # Public API ----------------------------------------------------------------
    def store(
        self,
        task_signature: str,
        artifact_type: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> Artifact:
        embedding = (
            self.embedding_func(task_signature) if self.embedding_func else None
        )
        artifact = Artifact(
            task_signature=task_signature,
            artifact_type=artifact_type,
            content=content,
            metadata=metadata,
            embedding=embedding,
        )
        self.backend.save(artifact)
        self._artifacts.append(artifact)
        self._prune()
        return artifact

    def lookup_by_signature(self, task_signature: str) -> List[Artifact]:
        """Return all artifacts 匹配 ``task_signature``."""

        return [a for a in self._artifacts if a.task_signature == task_signature]

    def lookup_by_similarity(self, query: str, top_k: int = 5) -> List[Artifact]:
        """返回与``query``最相似的制品。"""

        results: List[Tuple[float, Artifact]] = []
        if self.embedding_func:
            q_emb = self.embedding_func(query)
        else:
            q_emb = None

        for art in self._artifacts:
            if q_emb is not None and art.embedding is not None:
                score = self._cosine_sim(q_emb, art.embedding)
            else:
                score = difflib.SequenceMatcher(None, query, art.task_signature).ratio()
            results.append((score, art))

        results.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in results[:top_k]]

    # Internal -----------------------------------------------------------------
    def _prune(self) -> None:
        """应用保留策略。"""

        if self.retention.max_entries is None and self.retention.max_age_seconds is None:
            return

        now = time.time()
        # 移除 old entries by age
        if self.retention.max_age_seconds is not None:
            cutoff = now - self.retention.max_age_seconds
            remaining: List[Artifact] = []
            for art in sorted(self._artifacts, key=lambda a: a.timestamp):
                if art.timestamp >= cutoff:
                    remaining.append(art)
                else:
                    self.backend.delete(art)
            self._artifacts = remaining

        # 移除 extra entries by count
        if (
            self.retention.max_entries is not None
            and len(self._artifacts) > self.retention.max_entries
        ):
            # 移除 oldest
            self._artifacts.sort(key=lambda a: a.timestamp, reverse=True)
            for art in self._artifacts[self.retention.max_entries :]:
                self.backend.delete(art)
            self._artifacts = self._artifacts[: self.retention.max_entries]

    @staticmethod
    def _cosine_sim(a: Embedding, b: Embedding) -> float:
        import math

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
