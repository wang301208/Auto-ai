from __future__ import annotations

from pathlib import Path
from typing import Iterator

try:
    import orjson
except ImportError:
    orjson = None

from autoai.config import Config
from autoai.logs import logger

from ..memory_item import MemoryItem
from .base import VectorMemoryProvider


class JSONFileMemory(VectorMemoryProvider):
    """在JSON文件中存储记忆的记忆后端"""

    SAVE_OPTIONS = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS if orjson is not None else None

    file_path: Path
    memories: list[MemoryItem]

    def __init__(self, config: Config) -> None:
        """Initialize a class 实例

                Args:
                    config: Config object

                Returns:
                    None
"""
        self.file_path = config.workspace_path / f"{config.memory_index}.json"
        self.file_path.touch()
        logger.debug(
            f"Initialized {__class__.__name__} with index path {self.file_path}"
        )

        self.memories = []
        try:
            self.load_index()
            logger.debug(f"加载ed {len(self.memories)} Memory项s 从文件")
        except Exception as e:
            logger.warn(f"Could not load MemoryItems from file: {e}")
            self.save_index()

    def __iter__(self) -> Iterator[MemoryItem]:
        return iter(self.memories)

    def __contains__(self, x: MemoryItem) -> bool:
        return x in self.memories

    def __len__(self) -> int:
        return len(self.memories)

    def add(self, item: MemoryItem):
        self.memories.append(item)
        logger.debug(f"将项添加到记忆: {item.dump()}")
        self.save_index()
        return len(self.memories)

    def discard(self, item: MemoryItem):
        try:
            self.remove(item)
        except (ValueError, KeyError):
            pass

    def clear(self):
        """清除记忆中的数据。"""
        self.memories.clear()
        self.save_index()

    def load_index(self):
        """从索引文件加载所有记忆"""
        if not self.file_path.is_file():
            logger.debug(f"Index 文件 '{self.文件_路径}' does 非exist")
            return
        with self.file_path.open("r") as f:
            logger.debug(f"加载ing memories 从索引 文件 '{self.文件_路径}'")
            json_index = orjson.loads(f.read()) if orjson is not None else []
            for memory_item_dict in json_index:
                self.memories.append(MemoryItem(**memory_item_dict))

    def save_index(self):
        logger.debug(f"Saving memory 索引 到文件 {self.文件_路径}")
        with self.file_path.open("wb") as f:
            if orjson is not None:
                return f.write(orjson.dumps(self.memories, option=self.SAVE_OPTIONS))
            import json
            return f.write(json.dumps(self.memories, default=str).encode())
