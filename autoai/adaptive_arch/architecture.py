from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    LOADED = "loaded"
    ACTIVE = "active"
    STANDBY = "standby"
    UNLOADED = "unloaded"
    FAILED = "failed"


@dataclass
class Component:
    name: str
    state: ComponentState = ComponentState.UNLOADED
    priority: float = 0.5
    memory_mb: float = 10.0
    cpu_weight: float = 1.0
    loaded_at: float = 0.0
    error_count: int = 0

    @property
    def is_available(self) -> bool:
        return self.state in (ComponentState.ACTIVE, ComponentState.STANDBY)

    @property
    def is_critical(self) -> bool:
        return self.priority >= 0.8


@dataclass
class Topology:
    connections: dict[str, list[str]] = field(default_factory=dict)

    def connect(self, source: str, target: str) -> None:
        self.connections.setdefault(source, []).append(target)

    def disconnect(self, source: str, target: str) -> None:
        if source in self.connections:
            self.connections[source] = [t for t in self.connections[source] if t != target]

    def get_downstream(self, component: str) -> list[str]:
        return self.connections.get(component, [])

    def get_upstream(self, component: str) -> list[str]:
        return [s for s, targets in self.connections.items() if component in targets]

    def remove_component(self, component: str) -> None:
        self.connections.pop(component, None)
        for key in self.connections:
            self.connections[key] = [t for t in self.connections[key] if t != component]


class AdaptiveArchitecture:
    """自适应架构: 运行时组件管理。"""

    def __init__(self, memory_limit_mb: float = 512.0):
        self._memory_limit = memory_limit_mb
        self._components: dict[str, Component] = {}
        self._topology = Topology()
        self._load_hooks: dict[str, Callable] = {}
        self._used_memory = 0.0

    def register_component(self, name: str, priority: float = 0.5,
                           memory_mb: float = 10.0, cpu_weight: float = 1.0) -> Component:
        comp = Component(name=name, priority=priority, memory_mb=memory_mb, cpu_weight=cpu_weight)
        self._components[name] = comp
        return comp

    def load(self, name: str) -> bool:
        comp = self._components.get(name)
        if comp is None:
            return False
        if comp.state == ComponentState.ACTIVE:
            return True
        if self._used_memory + comp.memory_mb > self._memory_limit:
            if not self._try_free_memory(comp.memory_mb, comp.priority):
                logger.warning(f"内存不足，无法加载{name}")
                return False
        comp.state = ComponentState.ACTIVE
        comp.loaded_at = time.time()
        self._used_memory += comp.memory_mb
        hook = self._load_hooks.get(name)
        if hook:
            try:
                hook()
            except Exception as e:
                comp.state = ComponentState.FAILED
                comp.error_count += 1
                logger.error(f"组件{name}加载钩子失败: {e}")
                return False
        logger.info(f"组件加载: {name} (priority={comp.priority})")
        return True

    def unload(self, name: str) -> bool:
        comp = self._components.get(name)
        if comp is None or comp.state != ComponentState.ACTIVE:
            return False
        if comp.is_critical:
            logger.warning(f"拒绝卸载关键组件: {name}")
            return False
        comp.state = ComponentState.UNLOADED
        self._used_memory = max(0, self._used_memory - comp.memory_mb)
        self._topology.remove_component(name)
        logger.info(f"组件卸载: {name}")
        return True

    def _try_free_memory(self, needed_mb: float, min_priority: float) -> bool:
        candidates = [
            c for c in self._components.values()
            if c.state == ComponentState.ACTIVE and c.priority < min_priority
        ]
        candidates.sort(key=lambda c: c.priority)
        freed = 0.0
        for c in candidates:
            if freed >= needed_mb:
                break
            self.unload(c.name)
            freed += c.memory_mb
        return freed >= needed_mb

    def degrade(self, target_components: list[str] | None = None) -> list[str]:
        """优雅降级: 按优先级从低到高卸载非必要组件。"""
        target_components = target_components or []
        unloaded = []
        active = [c for c in self._components.values() if c.state == ComponentState.ACTIVE]
        active.sort(key=lambda c: c.priority)
        for c in active:
            if target_components and c.name not in target_components:
                continue
            if self.unload(c.name):
                unloaded.append(c.name)
        return unloaded

    def get_architecture_status(self) -> dict[str, Any]:
        return {
            "memory_used_mb": self._used_memory,
            "memory_limit_mb": self._memory_limit,
            "memory_utilization": self._used_memory / self._memory_limit if self._memory_limit > 0 else 0,
            "components": {
                name: {"state": comp.state.value, "priority": comp.priority}
                for name, comp in self._components.items()
            },
            "topology_connections": sum(len(v) for v in self._topology.connections.values()),
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_components": len(self._components),
            "active_components": sum(1 for c in self._components.values() if c.state == ComponentState.ACTIVE),
            "memory_utilization": self._used_memory / self._memory_limit if self._memory_limit > 0 else 0,
        }
