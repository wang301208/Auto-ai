from __future__ import annotations

import time
from typing import Any, Optional
from dataclasses import dataclass, field


class GCounter:
    """增长计数器CRDT：只增不减，合并取max。"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._counts: dict[str, int] = {}

    def increment(self, amount: int = 1) -> None:
        self._counts[self.node_id] = self._counts.get(self.node_id, 0) + amount

    @property
    def value(self) -> int:
        return sum(self._counts.values())

    def merge(self, other: GCounter) -> None:
        for node, count in other._counts.items():
            self._counts[node] = max(self._counts.get(node, 0), count)

    def to_dict(self) -> dict:
        return {"type": "gcounter", "counts": dict(self._counts)}

    @classmethod
    def from_dict(cls, data: dict, node_id: str) -> GCounter:
        gc = cls(node_id)
        gc._counts = data.get("counts", {})
        return gc


class PNCounter:
    """正负计数器CRDT：支持增减，合并取max。"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._positive = GCounter(node_id)
        self._negative = GCounter(node_id)

    def increment(self, amount: int = 1) -> None:
        self._positive.increment(amount)

    def decrement(self, amount: int = 1) -> None:
        self._negative.increment(amount)

    @property
    def value(self) -> int:
        return self._positive.value - self._negative.value

    def merge(self, other: PNCounter) -> None:
        self._positive.merge(other._positive)
        self._negative.merge(other._negative)


class ORSet:
    """观察移除集CRDT：支持添加和移除，无冲突合并。"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._elements: dict[Any, set[str]] = {}
        self._tombstones: set[Any] = set()

    def add(self, element: Any, tag: str | None = None) -> None:
        unique_tag = tag or f"{self.node_id}:{time.time_ns()}"
        if element not in self._elements:
            self._elements[element] = set()
        self._elements[element].add(unique_tag)
        self._tombstones.discard(element)

    def remove(self, element: Any) -> None:
        if element in self._elements:
            self._tombstones.add(element)
            del self._elements[element]

    def contains(self, element: Any) -> bool:
        return element in self._elements and element not in self._tombstones

    @property
    def value(self) -> set:
        return {e for e in self._elements if e not in self._tombstones}

    def merge(self, other: ORSet) -> None:
        for element, tags in other._elements.items():
            if element not in self._tombstones:
                if element not in self._elements:
                    self._elements[element] = set()
                self._elements[element].update(tags)
        self._tombstones.update(other._tombstones)
        for tomb in self._tombstones:
            self._elements.pop(tomb, None)


@dataclass
class LWWRegisterValue:
    value: Any
    timestamp: float
    node_id: str


class LWWRegister:
    """最后写入胜出寄存器CRDT：时间戳决胜。"""

    def __init__(self, node_id: str, initial: Any = None):
        self.node_id = node_id
        self._data: Optional[LWWRegisterValue] = None
        if initial is not None:
            self.set(initial)

    def set(self, value: Any) -> None:
        self._data = LWWRegisterValue(
            value=value,
            timestamp=time.time(),
            node_id=self.node_id,
        )

    @property
    def value(self) -> Any:
        return self._data.value if self._data else None

    @property
    def timestamp(self) -> float:
        return self._data.timestamp if self._data else 0.0

    def merge(self, other: LWWRegister) -> None:
        if other._data is None:
            return
        if self._data is None or other._data.timestamp > self._data.timestamp:
            self._data = other._data
        elif other._data.timestamp == self._data.timestamp:
            if other._data.node_id > (self._data.node_id or ""):
                self._data = other._data


class CRDTMap:
    """CRDT Map：基于LWWRegister的Map，支持无冲突分布式状态同步。"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._registers: dict[str, LWWRegister] = {}

    def set(self, key: str, value: Any) -> None:
        if key not in self._registers:
            self._registers[key] = LWWRegister(self.node_id)
        self._registers[key].set(value)

    def get(self, key: str, default: Any = None) -> Any:
        reg = self._registers.get(key)
        if reg and reg.value is not None:
            return reg.value
        return default

    def remove(self, key: str) -> None:
        self._registers.pop(key, None)

    def keys(self) -> list[str]:
        return list(self._registers.keys())

    @property
    def value(self) -> dict:
        return {k: v.value for k, v in self._registers.items() if v.value is not None}

    def merge(self, other: CRDTMap) -> None:
        for key, register in other._registers.items():
            if key not in self._registers:
                self._registers[key] = LWWRegister(self.node_id)
            self._registers[key].merge(register)

    def to_dict(self) -> dict:
        result = {}
        for key, reg in self._registers.items():
            if reg._data:
                result[key] = {
                    "value": reg._data.value,
                    "timestamp": reg._data.timestamp,
                    "node_id": reg._data.node_id,
                }
        return result

    @classmethod
    def from_dict(cls, data: dict, node_id: str) -> CRDTMap:
        cm = cls(node_id)
        for key, entry in data.items():
            reg = LWWRegister(node_id)
            reg._data = LWWRegisterValue(
                value=entry["value"],
                timestamp=entry["timestamp"],
                node_id=entry.get("node_id", node_id),
            )
            cm._registers[key] = reg
        return cm
