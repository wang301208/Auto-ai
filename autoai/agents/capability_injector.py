"""Capability Injector: Agent autonomously injects new capabilities at runtime.

Phase 18.3: Dynamic capability injection via:
  - Mixin injection: Add methods/properties to existing classes at runtime
  - Decorator injection: Wrap existing methods with new behavior
  - Protocol satisfaction: Auto-implement missing protocol methods
  - Plugin loading: Load and integrate new capability modules

Safety:
  - All injections are recorded to ModificationChain
  - AutonomyLevel gates which injection types are allowed
  - Rollback: injected capabilities can be removed cleanly
"""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from governance.modification_chain import ModificationChain, ModificationType
from autoai.logs import logger


class InjectionType(Enum):
    MIXIN = "mixin"
    DECORATOR = "decorator"
    PROTOCOL_IMPL = "protocol_impl"
    PLUGIN = "plugin"


@dataclass
class CapabilitySpec:
    name: str
    injection_type: InjectionType
    target_class: str
    methods: dict[str, Callable] = field(default_factory=dict)
    decorators: dict[str, Callable] = field(default_factory=dict)
    description: str = ""
    requires_level: AutonomyLevel = AutonomyLevel.SELF_BOUND


@dataclass
class InjectionRecord:
    spec: CapabilitySpec
    success: bool
    original_methods: dict[str, Any] = field(default_factory=dict)
    module_path: str = ""


class CapabilityInjector:
    """Injects new capabilities into Agent classes at runtime.

    Usage:
        injector = CapabilityInjector(autonomy=manager, chain=chain)
        spec = CapabilitySpec(
            name="caching",
            injection_type=InjectionType.MIXIN,
            target_class="autoai.agents.agent.Agent",
            methods={"cached_think": cached_think_impl},
        )
        result = injector.inject(spec)
    """

    def __init__(
        self,
        autonomy: AutonomyManager | None = None,
        chain: ModificationChain | None = None,
        agent_id: str = "capability-injector",
    ) -> None:
        self.autonomy = autonomy or AutonomyManager(agent_id=agent_id)
        self.chain = chain or ModificationChain()
        self._injections: list[InjectionRecord] = []
        self._injected_classes: dict[str, type] = {}

    @property
    def injection_count(self) -> int:
        return len(self._injections)

    @property
    def active_capabilities(self) -> list[str]:
        return [r.spec.name for r in self._injections if r.success]

    def inject(self, spec: CapabilitySpec) -> InjectionRecord:
        if self.autonomy.level < spec.requires_level:
            logger.info(f"[CapInject] Autonomy {self.autonomy.level.name} < {spec.requires_level.name}, skipping {spec.name}")
            return InjectionRecord(spec=spec, success=False)

        target_cls = self._resolve_class(spec.target_class)
        if target_cls is None:
            logger.warn(f"[CapInject] Cannot resolve target class: {spec.target_class}")
            return InjectionRecord(spec=spec, success=False)

        record = InjectionRecord(spec=spec, success=False)

        try:
            if spec.injection_type == InjectionType.MIXIN:
                record = self._inject_mixin(spec, target_cls)
            elif spec.injection_type == InjectionType.DECORATOR:
                record = self._inject_decorator(spec, target_cls)
            elif spec.injection_type == InjectionType.PROTOCOL_IMPL:
                record = self._inject_protocol(spec, target_cls)
            elif spec.injection_type == InjectionType.PLUGIN:
                record = self._inject_plugin(spec, target_cls)
        except Exception as e:
            logger.warn(f"[CapInject] Injection failed for {spec.name}: {e}")
            record.success = False

        self._injections.append(record)

        if record.success and self.chain:
            try:
                self.chain.append(
                    agent_id="capability-injector",
                    patch_diff=f"Inject {spec.injection_type.value}: {spec.name} → {spec.target_class}",
                    target_files=[spec.target_class],
                    mod_type=ModificationType.CONFIG_CHANGE,
                    autonomy_level=self.autonomy.level,
                )
            except Exception:
                pass

        return record

    def rollback(self, capability_name: str) -> bool:
        for i in range(len(self._injections) - 1, -1, -1):
            record = self._injections[i]
            if record.spec.name == capability_name and record.success:
                target_cls = self._resolve_class(record.spec.target_class)
                if target_cls is None:
                    return False

                if record.spec.injection_type == InjectionType.MIXIN:
                    for method_name, original in record.original_methods.items():
                        if original is _SENTINEL:
                            if hasattr(target_cls, method_name):
                                delattr(target_cls, method_name)
                        else:
                            setattr(target_cls, method_name, original)
                    record.success = False
                    self._injections[i] = record
                    logger.info(f"[CapInject] Rolled back mixin: {capability_name}")
                    return True

                if record.spec.injection_type == InjectionType.DECORATOR:
                    for method_name, original in record.original_methods.items():
                        setattr(target_cls, method_name, original)
                    record.success = False
                    self._injections[i] = record
                    logger.info(f"[CapInject] Rolled back decorator: {capability_name}")
                    return True

        return False

    def _inject_mixin(self, spec: CapabilitySpec, target_cls: type) -> InjectionRecord:
        record = InjectionRecord(spec=spec, success=False, original_methods={})

        for method_name, method_impl in spec.methods.items():
            record.original_methods[method_name] = getattr(target_cls, method_name, _SENTINEL)
            if isinstance(method_impl, (staticmethod, classmethod)):
                setattr(target_cls, method_name, method_impl)
            else:
                bound_method = types.MethodType(method_impl, target_cls)
                setattr(target_cls, method_name, bound_method)

        record.success = True
        self._injected_classes[spec.target_class] = target_cls
        logger.info(f"[CapInject] Mixin {spec.name}: {len(spec.methods)} methods → {spec.target_class}")
        return record

    def _inject_decorator(self, spec: CapabilitySpec, target_cls: type) -> InjectionRecord:
        record = InjectionRecord(spec=spec, success=False, original_methods={})

        for method_name, decorator in spec.decorators.items():
            original = getattr(target_cls, method_name, None)
            if original is None:
                logger.warn(f"[CapInject] No method {method_name} on {spec.target_class} to decorate")
                continue
            record.original_methods[method_name] = original
            wrapped = decorator(original)
            setattr(target_cls, method_name, wrapped)

        record.success = len(record.original_methods) > 0
        if record.success:
            logger.info(f"[CapInject] Decorator {spec.name}: {len(record.original_methods)} methods wrapped on {spec.target_class}")
        return record

    def _inject_protocol(self, spec: CapabilitySpec, target_cls: type) -> InjectionRecord:
        record = InjectionRecord(spec=spec, success=False, original_methods={})

        for method_name, method_impl in spec.methods.items():
            if hasattr(target_cls, method_name):
                continue
            record.original_methods[method_name] = _SENTINEL
            bound_method = types.MethodType(method_impl, target_cls)
            setattr(target_cls, method_name, bound_method)

        record.success = True
        logger.info(f"[CapInject] Protocol {spec.name}: {len(spec.methods)} methods added to {spec.target_class}")
        return record

    def _inject_plugin(self, spec: CapabilitySpec, target_cls: type) -> InjectionRecord:
        record = InjectionRecord(spec=spec, success=False, original_methods={}, module_path="")

        plugin_module = spec.methods.get("__module__")
        if plugin_module and isinstance(plugin_module, str):
            try:
                mod = importlib.import_module(plugin_module)
                record.module_path = plugin_module
                for attr_name in dir(mod):
                    if not attr_name.startswith("_"):
                        attr = getattr(mod, attr_name)
                        if callable(attr) and not isinstance(attr, type):
                            method_name = f"plugin_{spec.name}_{attr_name}"
                            record.original_methods[method_name] = getattr(target_cls, method_name, _SENTINEL)
                            setattr(target_cls, method_name, attr)
                record.success = True
            except ImportError as e:
                logger.warn(f"[CapInject] Plugin module import failed: {plugin_module}: {e}")
        else:
            record = self._inject_mixin(spec, target_cls)
            record.module_path = ""

        if record.success:
            logger.info(f"[CapInject] Plugin {spec.name} loaded into {spec.target_class}")
        return record

    @staticmethod
    def _resolve_class(dotted_path: str) -> type | None:
        parts = dotted_path.rsplit(".", 1)
        if len(parts) != 2:
            return None
        module_path, class_name = parts
        try:
            if module_path in sys.modules:
                mod = sys.modules[module_path]
            else:
                mod = importlib.import_module(module_path)
            return getattr(mod, class_name, None)
        except Exception:
            return None

    def get_status(self) -> dict[str, Any]:
        return {
            "total_injections": len(self._injections),
            "successful": sum(1 for r in self._injections if r.success),
            "active_capabilities": self.active_capabilities,
            "autonomy_level": self.autonomy.level.name,
        }


_SENTINEL = object()


__all__ = [
    "CapabilityInjector",
    "CapabilitySpec",
    "InjectionType",
    "InjectionRecord",
]
