"""Initialize a knowledge database from plugin and skill metadata.

This script scans plugin and skill repositories for metadata files,
computes embeddings for their descriptions and tags, and stores them in a
persistent Chroma vector database collection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from autoai.config import Config
from autoai.memory.vector.utils import get_embedding
from autoai.skills.vector_db import ChromaVectorDB


def _collect_metadata_files(repo: Path, pattern: str) -> Iterable[Path]:
    """Yield metadata files under ``repo`` matching ``pattern``."""
    if not repo.exists():
        return []
    return repo.rglob(pattern)


def _embed_and_store(
    files: Iterable[Path], item_type: str, db: ChromaVectorDB, config: Config
) -> None:
    """Compute embeddings for metadata files and store them in ``db``.

    Args:
        files: Iterable of file paths to process.
        item_type: Either ``"plugin"`` or ``"skill"``.
        db: The vector database to store embeddings in.
        config: Config object used for embedding generation.
    """
    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as err:
            print(f"Failed to read {file_path}: {err}")
            continue

        name = data.get("name") or data.get("skill_name") or file_path.stem
        description = data.get("description", "")
        tags = data.get("tags") or []
        tags_text = " ".join(tags) if isinstance(tags, list) else str(tags)
        text = "\n".join(filter(None, [description, tags_text]))
        if not text:
            continue

        try:
            embedding = get_embedding(text, config)
        except Exception as err:
            print(f"Failed to embed {file_path}: {err}")
            continue

        key = f"{item_type}:{name}"
        metadata = {
            "type": item_type,
            "name": name,
            "path": str(file_path),
            "description": description,
            "tags": tags,
        }
        db.add(key, embedding, metadata)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize a Chroma knowledge database from metadata"
    )
    parser.add_argument(
        "--plugin-repo",
        type=Path,
        default=Path("plugins"),
        help="Path to the plugin repository",
    )
    parser.add_argument(
        "--skill-repo",
        type=Path,
        default=Path("skill_library"),
        help="Path to the skill repository",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=Path("data/knowledge_db"),
        help="Directory for Chroma persistence",
    )
    parser.add_argument(
        "--collection-name",
        default="knowledge",
        help="Chroma collection name",
    )
    args = parser.parse_args()

    config = Config()
    db = ChromaVectorDB(args.persist_dir, collection_name=args.collection_name)

    plugin_files = _collect_metadata_files(args.plugin_repo, "*.spec.json")
    _embed_and_store(plugin_files, "plugin", db, config)

    skill_files = _collect_metadata_files(args.skill_repo, "skill.json")
    _embed_and_store(skill_files, "skill", db, config)


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
