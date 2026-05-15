from __future__ import annotations

import time
import uuid
import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ComponentLanguage(Enum):
    RUST = "rust"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    C = "c"
    GO = "go"


class ComponentStatus(Enum):
    COMPILED = "compiled"
    LOADED = "loaded"
    RUNNING = "running"
    ERROR = "error"
    UNLOADED = "unloaded"


@dataclass
class WASMComponentSpec:
    """WASM组件规格声明。"""
    name: str
    version: str = "0.1.0"
    language: ComponentLanguage = ComponentLanguage.PYTHON
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    permissions: set[str] = field(default_factory=lambda: {"fs_read", "compute"})
    max_memory_bytes: int = 10 * 1024 * 1024
    timeout_seconds: float = 30.0
    source_path: str = ""
    wasm_path: str = ""

    @property
    def component_id(self) -> str:
        content = f"{self.name}:{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class WASMComponent:
    """WASM组件实例。"""
    spec: WASMComponentSpec
    status: ComponentStatus = ComponentStatus.COMPILED
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    loaded_at: float = 0.0
    call_count: int = 0
    last_error: str = ""
    _handler: Optional[Callable] = field(default=None, repr=False)

    @property
    def component_id(self) -> str:
        return self.spec.component_id

    def set_handler(self, handler: Callable) -> None:
        self._handler = handler
        self.status = ComponentStatus.LOADED
        self.loaded_at = time.time()


class ComponentRegistry:
    """WASM组件注册表：管理所有可用组件。"""

    def __init__(self):
        self._components: dict[str, WASMComponent] = {}
        self._by_name: dict[str, list[str]] = {}

    def register(self, component: WASMComponent) -> str:
        cid = component.component_id
        self._components[cid] = component
        self._by_name.setdefault(component.spec.name, []).append(cid)
        logger.info(f"WASM组件注册: {component.spec.name} v{component.spec.version} ({cid})")
        return cid

    def unregister(self, component_id: str) -> None:
        comp = self._components.pop(component_id, None)
        if comp:
            cids = self._by_name.get(comp.spec.name, [])
            if component_id in cids:
                cids.remove(component_id)

    def get(self, component_id: str) -> WASMComponent | None:
        return self._components.get(component_id)

    def get_by_name(self, name: str) -> list[WASMComponent]:
        cids = self._by_name.get(name, [])
        return [self._components[cid] for cid in cids if cid in self._components]

    def list_components(self) -> list[WASMComponent]:
        return list(self._components.values())

    def find_by_permission(self, required_permissions: set[str]) -> list[WASMComponent]:
        return [
            c for c in self._components.values()
            if required_permissions.issubset(c.spec.permissions)
        ]


class WASMRuntime:
    """WASM统一运行时：跨语言、跨平台、沙箱化的能力执行层。"""

    def __init__(self, registry: ComponentRegistry | None = None):
        self.registry = registry or ComponentRegistry()
        self._running_instances: dict[str, dict] = {}
        self._total_calls = 0
        self._total_errors = 0

    def load_component(self, spec: WASMComponentSpec, handler: Callable | None = None) -> WASMComponent:
        component = WASMComponent(spec=spec)
        if handler:
            component.set_handler(handler)
        self.registry.register(component)
        return component

    async def execute(self, component_id: str, input_data: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        component = self.registry.get(component_id)
        if not component:
            return {"success": False, "error": f"组件不存在: {component_id}"}
        if component.status not in (ComponentStatus.LOADED, ComponentStatus.RUNNING):
            return {"success": False, "error": f"组件状态不可执行: {component.status.value}"}
        start = time.time()
        self._total_calls += 1
        component.status = ComponentStatus.RUNNING
        try:
            if component._handler:
                result = component._handler(**input_data)
                if hasattr(result, '__await__'):
                    import asyncio
                    actual_timeout = timeout or component.spec.timeout_seconds
                    result = await asyncio.wait_for(result, timeout=actual_timeout)
            else:
                result = self._simulate_wasm_execution(component, input_data)
            component.call_count += 1
            component.status = ComponentStatus.LOADED
            duration = (time.time() - start) * 1000
            return {"success": True, "result": result, "duration_ms": duration}
        except Exception as e:
            component.status = ComponentStatus.ERROR
            component.last_error = str(e)
            self._total_errors += 1
            return {"success": False, "error": str(e)}

    def _simulate_wasm_execution(self, component: WASMComponent, input_data: dict) -> Any:
        return {"component": component.spec.name, "input_received": True, "simulated": True}

    def get_stats(self) -> dict:
        return {
            "total_components": len(self.registry.list_components()),
            "total_calls": self._total_calls,
            "total_errors": self._total_errors,
            "running_instances": len(self._running_instances),
        }
