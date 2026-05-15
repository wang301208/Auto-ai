from __future__ import annotations

import time
import json
import threading
from pathlib import Path
from typing import Any, Optional

from autoai.memory.layered.hierarchy import (
    MemoryLayer,
    LayeredMemoryItem,
    LayeredMemoryStore,
    ForgettingCurve,
)


class SensoryMemory(LayeredMemoryStore):
    """L0 传感记忆：实时感知流，TTL=秒级，自动过期。"""

    def __init__(self, config: Any = None, ttl_seconds: float = 5.0):
        super().__init__(MemoryLayer.SENSORY, config)
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

    def put(self, key: str, item: LayeredMemoryItem) -> None:
        with self._lock:
            item.metadata["ttl"] = self.ttl_seconds
            super().put(key, item)

    def get(self, key: str) -> Optional[LayeredMemoryItem]:
        with self._lock:
            item = super().get(key)
            if item and item.age_seconds > self.ttl_seconds:
                self.remove(key)
                return None
            return item

    def prune_expired(self) -> int:
        with self._lock:
            expired = [k for k, v in self._items.items() if v.age_seconds > self.ttl_seconds]
            for k in expired:
                del self._items[k]
            return len(expired)


class WorkingMemory(LayeredMemoryStore):
    """L1 工作记忆：当前任务上下文，任务结束自动清空。"""

    def __init__(self, config: Any = None, max_items: int = 50):
        super().__init__(MemoryLayer.WORKING, config)
        self.max_items = max_items
        self._current_task_id: Optional[str] = None
        self._lock = threading.Lock()

    def set_task_context(self, task_id: str) -> None:
        self._current_task_id = task_id

    def clear_task(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
            self._current_task_id = None
            return count

    def put(self, key: str, item: LayeredMemoryItem) -> None:
        with self._lock:
            if len(self._items) >= self.max_items:
                oldest_key = min(self._items, key=lambda k: self._items[k].timestamp)
                del self._items[oldest_key]
            super().put(key, item)


class ShortTermMemory(LayeredMemoryStore):
    """L2 短期记忆：近期会话，Ebbinghaus衰减，默认7天半衰期。"""

    def __init__(self, config: Any = None, half_life_days: float = 7.0):
        super().__init__(MemoryLayer.SHORT_TERM, config)
        self.half_life_days = half_life_days
        self._decay_rate = 0.693 / (half_life_days * 86400)

    def put(self, key: str, item: LayeredMemoryItem) -> None:
        item.decay_rate = self._decay_rate
        super().put(key, item)


class LongTermMemoryV2(LayeredMemoryStore):
    """L3 长期记忆：跨会话经验，低衰减率，支持持久化。"""

    def __init__(self, config: Any = None, persist_path: Optional[str] = None):
        super().__init__(MemoryLayer.LONG_TERM, config)
        self.persist_path = Path(persist_path) if persist_path else None
        self._lock = threading.Lock()
        if self.persist_path and self.persist_path.exists():
            self._load()

    def put(self, key: str, item: LayeredMemoryItem) -> None:
        with self._lock:
            item.decay_rate = 0.0001
            super().put(key, item)
            if self.persist_path:
                self._save()

    def _save(self) -> None:
        if not self.persist_path:
            return
        data = {}
        for k, v in self._items.items():
            data[k] = {
                "content": v.content,
                "embedding": v.embedding[:50] if v.embedding else [],
                "importance": v.importance,
                "access_count": v.access_count,
                "timestamp": v.timestamp,
                "metadata": v.metadata,
            }
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.persist_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            for k, v in data.items():
                item = LayeredMemoryItem(
                    content=v["content"],
                    embedding=v.get("embedding", []),
                    layer=MemoryLayer.LONG_TERM,
                    importance=v.get("importance", 1.0),
                    access_count=v.get("access_count", 0),
                    timestamp=v.get("timestamp", time.time()),
                    decay_rate=0.0001,
                    metadata=v.get("metadata", {}),
                )
                self._items[k] = item
        except Exception:
            pass


class MetaMemory(LayeredMemoryStore):
    """L4 元记忆：策略/偏好/技能/世界观，Agent可自修改。"""

    def __init__(self, config: Any = None):
        super().__init__(MemoryLayer.META, config)
        self._strategies: dict[str, dict] = {}
        self._preferences: dict[str, Any] = {}
        self._world_model: dict[str, Any] = {}

    def update_strategy(self, name: str, strategy: dict) -> None:
        self._strategies[name] = strategy
        key = f"strategy_{name}"
        item = LayeredMemoryItem(
            content=json.dumps(strategy, ensure_ascii=False),
            layer=MemoryLayer.META,
            importance=0.9,
            decay_rate=0.0001,
            metadata={"type": "strategy", "name": name},
        )
        self.put(key, item)

    def get_strategy(self, name: str) -> Optional[dict]:
        return self._strategies.get(name)

    def update_preference(self, key: str, value: Any) -> None:
        self._preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._preferences.get(key, default)

    def update_world_model(self, aspect: str, model: Any) -> None:
        self._world_model[aspect] = model
        mk = f"world_{aspect}"
        item = LayeredMemoryItem(
            content=json.dumps(model, ensure_ascii=False) if isinstance(model, (dict, list)) else str(model),
            layer=MemoryLayer.META,
            importance=0.95,
            decay_rate=0.00005,
            metadata={"type": "world_model", "aspect": aspect},
        )
        self.put(mk, item)

    def get_world_model(self, aspect: str) -> Optional[Any]:
        return self._world_model.get(aspect)


class SpeciesMemory(LayeredMemoryStore):
    """L5 种族记忆：跨Agent/跨代累积知识，不可删只可追加。"""

    def __init__(self, config: Any = None, persist_path: Optional[str] = None):
        super().__init__(MemoryLayer.SPECIES, config)
        self.persist_path = Path(persist_path) if persist_path else None
        self._lock = threading.Lock()
        self._append_log: list[str] = []
        if self.persist_path and self.persist_path.exists():
            self._load()

    def put(self, key: str, item: LayeredMemoryItem) -> None:
        with self._lock:
            if key in self._items:
                return
            item.layer = MemoryLayer.SPECIES
            item.decay_rate = 0.0
            item.importance = max(item.importance, 0.8)
            super().put(key, item)
            self._append_log.append(f"+{key}@{time.time()}")
            if self.persist_path:
                self._save()

    def remove(self, key: str) -> Optional[LayeredMemoryItem]:
        return None

    def _save(self) -> None:
        if not self.persist_path:
            return
        data = {}
        for k, v in self._items.items():
            data[k] = {
                "content": v.content,
                "embedding": v.embedding[:50] if v.embedding else [],
                "importance": v.importance,
                "access_count": v.access_count,
                "timestamp": v.timestamp,
                "metadata": v.metadata,
            }
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.persist_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            for k, v in data.items():
                item = LayeredMemoryItem(
                    content=v["content"],
                    embedding=v.get("embedding", []),
                    layer=MemoryLayer.SPECIES,
                    importance=v.get("importance", 0.8),
                    access_count=v.get("access_count", 0),
                    timestamp=v.get("timestamp", time.time()),
                    decay_rate=0.0,
                    metadata=v.get("metadata", {}),
                )
                self._items[k] = item
        except Exception:
            pass
