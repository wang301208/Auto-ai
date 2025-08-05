from pathlib import Path

from autogpt.skills.vector_db import FaissVectorDB


def test_faiss_add_query_delete(tmp_path: Path) -> None:
    db = FaissVectorDB(tmp_path)
    db.add("skill1", [1.0, 0.0], {"a": 1})
    db.add("skill2", [0.0, 1.0], {"b": 2})

    res = db.query([1.0, 0.0], top_k=2)
    assert res[0][0] == "skill1"

    # persistence across instances
    db2 = FaissVectorDB(tmp_path)
    emb, meta = db2.get("skill1")
    assert meta["a"] == 1

    db2.delete("skill1")
    assert db2.get("skill1") is None
