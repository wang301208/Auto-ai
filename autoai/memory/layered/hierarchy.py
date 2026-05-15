from __future__ import annotations

import enum
import math
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)


class MemoryLayer(enum.IntEnum):
    SENSORY = 0
    WORKING = 1
    SHORT_TERM = 2
    LONG_TERM = 3
    META = 4
    SPECIES = 5


@dataclass
class LayeredMemoryItem:
    content: str
    embedding: list[float] = field(default_factory=list)
    layer: MemoryLayer = MemoryLayer.WORKING
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 1.0
    decay_rate: float = 0.01
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    @property
    def weight(self) -> float:
        return self.importance * self.access_count * ForgettingCurve.recall_probability(
            self.age_seconds, self.decay_rate
        )


class ForgettingCurve:
    """基于Ebbinghaus遗忘曲线的记忆衰减模型。"""

    @staticmethod
    def recall_probability(age_seconds: float, decay_rate: float = 0.01, stability: float = 1.0) -> float:
        """R = e^(-decay_rate * age / stability)"""
        return math.exp(-decay_rate * max(0, age_seconds) / stability)

    @staticmethod
    def effective_decay_rate(successes: int, failures: int) -> float:
        """根据记忆检索成功/失败次数动态调整衰减率。"""
        total = successes + failures
        if total == 0:
            return 0.01
        success_rate = successes / total
        return 0.01 * (1.0 + 2.0 * (1.0 - success_rate))

    @staticmethod
    def should_consolidate(item: LayeredMemoryItem, threshold: float = 0.3) -> bool:
        """判断记忆是否需要巩固（权重低于阈值时需要遗忘或巩固）。"""
        return item.weight < threshold and item.importance > 0.5


class LayeredMemoryStore:
    """单层记忆存储的抽象基类。"""

    def __init__(self, layer: MemoryLayer, config: Any = None):
        self.layer = layer
        self.config = config
        self._items: dict[str, LayeredMemoryItem] = {}

    def put(self, key: str, item: LayeredMemoryItem) -> None:
        item.layer = self.layer
        self._items[key] = item

    def get(self, key: str) -> Optional[LayeredMemoryItem]:
        item = self._items.get(key)
        if item:
            item.access_count += 1
        return item

    def remove(self, key: str) -> Optional[LayeredMemoryItem]:
        return self._items.pop(key, None)

    def search(self, query_embedding: list[float], k: int = 5) -> list[tuple[str, LayeredMemoryItem, float]]:
        results = []
        for key, item in self._items.items():
            if not item.embedding or not query_embedding:
                continue
            similarity = self._cosine_similarity(query_embedding, item.embedding)
            weighted = similarity * item.weight
            results.append((key, item, weighted))
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:k]

    def all_items(self) -> dict[str, LayeredMemoryItem]:
        return dict(self._items)

    def size(self) -> int:
        return len(self._items)

    def decay_all(self) -> int:
        """对所有记忆应用遗忘衰减，移除权重趋近零的记忆。返回移除数量。"""
        removed = 0
        expired_keys = []
        for key, item in self._items.items():
            if item.weight < 0.001 and item.layer < MemoryLayer.SPECIES:
                expired_keys.append(key)
        for key in expired_keys:
            del self._items[key]
            removed += 1
        return removed

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class LayeredMemorySystem:
    """六层分层记忆系统：L0传感→L1工作→L2短期→L3长期→L4元→L5种族"""

    def __init__(self, config: Any = None):
        self.config = config
        self.stores: dict[MemoryLayer, LayeredMemoryStore] = {
            layer: LayeredMemoryStore(layer, config) for layer in MemoryLayer
        }
        self._consolidator = MemoryConsolidator(self)
        logger.info("六层分层记忆系统初始化完成: L0传感→L1工作→L2短期→L3长期→L4元→L5种族")

    def store(self, content: str, layer: MemoryLayer, embedding: list[float] | None = None,
              importance: float = 1.0, metadata: dict | None = None, key: str | None = None) -> str:
        if key is None:
            key = f"L{layer.value}_{int(time.time() * 1000)}"
        item = LayeredMemoryItem(
            content=content,
            embedding=embedding or [],
            layer=layer,
            importance=importance,
            metadata=metadata or {},
        )
        self.stores[layer].put(key, item)
        return key

    def retrieve(self, query_embedding: list[float], k: int = 5,
                 layers: Sequence[MemoryLayer] | None = None,
                 min_weight: float = 0.0) -> list[tuple[str, LayeredMemoryItem, float]]:
        target_layers = layers or list(MemoryLayer)
        all_results = []
        for layer in target_layers:
            results = self.stores[layer].search(query_embedding, k)
            all_results.extend(results)
        all_results = [(k_, it, sc) for k_, it, sc in all_results if sc >= min_weight]
        all_results.sort(key=lambda x: x[2], reverse=True)
        return all_results[:k]

    def consolidate(self) -> dict[str, int]:
        """执行记忆巩固：L0→L1→L2→L3→L4→L5"""
        return self._consolidator.run_all()

    def decay(self) -> int:
        """对所有层应用遗忘曲线衰减。"""
        total_removed = 0
        for store in self.stores.values():
            total_removed += store.decay_all()
        if total_removed > 0:
            logger.info(f"遗忘衰减完成，移除{total_removed}条低权重记忆")
        return total_removed

    def get_layer_stats(self) -> dict[str, int]:
        return {f"L{layer.value}_{layer.name}": store.size() for layer, store in self.stores.items()}


class MemoryConsolidator:
    """记忆巩固引擎：负责记忆在各层之间的转移、压缩与提炼。"""

    def __init__(self, system: LayeredMemorySystem):
        self.system = system
        self._llm_summarize = None

    def set_llm_summarizer(self, fn):
        self._llm_summarize = fn

    def run_all(self) -> dict[str, int]:
        stats = {}
        stats["sensory_to_working"] = self._consolidate_layer(
            MemoryLayer.SENSORY, MemoryLayer.WORKING, max_items=100
        )
        stats["working_to_short"] = self._consolidate_layer(
            MemoryLayer.WORKING, MemoryLayer.SHORT_TERM, max_items=50, min_age=60.0
        )
        stats["short_to_long"] = self._consolidate_long_term()
        stats["long_to_meta"] = self._consolidate_meta()
        stats["meta_to_species"] = self._consolidate_species()
        return stats

    def _consolidate_layer(self, src: MemoryLayer, dst: MemoryLayer,
                           max_items: int = 50, min_age: float = 0.0) -> int:
        src_store = self.system.stores[src]
        dst_store = self.system.stores[dst]
        candidates = []
        for key, item in src_store.all_items().items():
            if item.age_seconds >= min_age and item.importance > 0.3:
                candidates.append((key, item))
        candidates.sort(key=lambda x: x[1].weight, reverse=True)
        moved = 0
        for key, item in candidates[:max_items]:
            summary = self._summarize(item.content) if self._llm_summarize else item.content
            new_item = LayeredMemoryItem(
                content=summary,
                embedding=item.embedding,
                layer=dst,
                importance=item.importance * 1.1,
                access_count=item.access_count,
                decay_rate=item.decay_rate * 0.5,
                metadata={**item.metadata, "consolidated_from": src.name},
            )
            dst_store.put(key, new_item)
            src_store.remove(key)
            moved += 1
        return moved

    def _consolidate_long_term(self) -> int:
        src_store = self.system.stores[MemoryLayer.SHORT_TERM]
        dst_store = self.system.stores[MemoryLayer.LONG_TERM]
        moved = 0
        for key, item in list(src_store.all_items().items()):
            if item.access_count >= 3 and item.importance >= 0.6:
                dst_store.put(key, item)
                src_store.remove(key)
                moved += 1
        return moved

    def _consolidate_meta(self) -> int:
        src_store = self.system.stores[MemoryLayer.LONG_TERM]
        dst_store = self.system.stores[MemoryLayer.META]
        pattern_groups: dict[str, list[LayeredMemoryItem]] = {}
        for key, item in src_store.all_items().items():
            category = item.metadata.get("category", "general")
            pattern_groups.setdefault(category, []).append(item)
        promoted = 0
        for category, items in pattern_groups.items():
            if len(items) >= 5:
                combined = "; ".join(it.content[:200] for it in items[:10])
                rule = self._extract_pattern(combined) if self._llm_summarize else f"模式({category}): {len(items)}条经验归纳"
                meta_key = f"meta_{category}_{int(time.time())}"
                meta_item = LayeredMemoryItem(
                    content=rule,
                    layer=MemoryLayer.META,
                    importance=0.9,
                    decay_rate=0.001,
                    metadata={"category": category, "source_count": len(items)},
                )
                dst_store.put(meta_key, meta_item)
                promoted += 1
        return promoted

    def _consolidate_species(self) -> int:
        src_store = self.system.stores[MemoryLayer.META]
        dst_store = self.system.stores[MemoryLayer.SPECIES]
        promoted = 0
        for key, item in list(src_store.all_items().items()):
            if item.access_count >= 10 and item.importance >= 0.85:
                species_key = f"species_{key}"
                dst_store.put(species_key, item)
                promoted += 1
        return promoted

    def _summarize(self, content: str) -> str:
        if self._llm_summarize:
            try:
                return self._llm_summarize(content)
            except Exception:
                pass
        return content[:500]

    def _extract_pattern(self, combined: str) -> str:
        if self._llm_summarize:
            try:
                prompt = f"从以下经验中提炼一个通用策略规则：\n{combined}\n\n策略规则："
                return self._llm_summarize(prompt)
            except Exception:
                pass
        return combined[:300]
