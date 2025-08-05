import json
from pathlib import Path

import chromadb
import numpy as np


class _FakeCollection:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.file = self.path / "data.json"
        if self.file.exists():
            data = json.loads(self.file.read_text())
            self.embeddings = data.get("embeddings", {})
            self.metadatas = data.get("metadatas", {})
        else:
            self.embeddings = {}
            self.metadatas = {}

    def _save(self) -> None:
        self.file.write_text(
            json.dumps({"embeddings": self.embeddings, "metadatas": self.metadatas})
        )

    def add(self, ids, embeddings, metadatas=None):
        for i, emb in zip(ids, embeddings):
            self.embeddings[i] = emb
        for i, meta in zip(ids, metadatas or [{}] * len(ids)):
            self.metadatas[i] = meta
        self._save()

    def delete(self, ids):
        for i in ids:
            self.embeddings.pop(i, None)
            self.metadatas.pop(i, None)
        self._save()

    def get(self, ids=None, include=None):
        if ids is None:
            ids = list(self.embeddings.keys())
        found_ids = [i for i in ids if i in self.embeddings]
        embeddings = [self.embeddings[i] for i in found_ids]
        metadatas = [self.metadatas[i] for i in found_ids]
        return {"ids": found_ids, "embeddings": embeddings, "metadatas": metadatas}

    def query(self, query_embeddings, n_results=5, include=None):
        q = np.array(query_embeddings[0])
        ids = list(self.embeddings.keys())
        embs = [np.array(self.embeddings[i]) for i in ids]
        sims = [
            float(np.dot(q, e) / (np.linalg.norm(q) * np.linalg.norm(e) + 1e-10))
            for e in embs
        ]
        order = np.argsort(sims)[::-1][:n_results]
        result_ids = [ids[i] for i in order]
        dists = [1 - sims[i] for i in order]
        return {"ids": [result_ids], "distances": [dists]}


class _FakeClient:
    def __init__(self, path: str):
        self.path = Path(path)
        self.collections = {}

    def get_or_create_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = _FakeCollection(self.path / name)
        return self.collections[name]


chromadb.PersistentClient = _FakeClient

from autogpt.skills.vector_db import ChromaVectorDB


def test_chroma_add_query_delete(tmp_path: Path) -> None:
    db = ChromaVectorDB(tmp_path)
    db.add("skill1", [1.0, 0.0], {"a": 1})
    db.add("skill2", [0.0, 1.0], {"b": 2})

    results = db.query([1.0, 0.0], top_k=2)
    assert results[0][0] == "skill1"

    # persistence across instances
    db2 = ChromaVectorDB(tmp_path)
    emb, meta = db2.get("skill1")
    assert meta["a"] == 1

    db2.delete("skill1")
    assert db2.get("skill1") is None
