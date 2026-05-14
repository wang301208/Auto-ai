"""模型注册表：管理ModelSpec条目及其关联的提供者。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base_provider import BaseProvider
from .model_spec import BUILTIN_MODEL_SPECS, ModelSpec

logger = logging.getLogger(__name__)


class ModelRegistry:
    """模型规格和提供者的中央注册表.

        Responsibilities:
          - 注册/注销ModelSpec条目
          - Register/unregister provider 实例s
          - 按ID、层级、能力、提供者查找模型
          - 从YAML/JSON配置文件加载模型规格
          - 将V1 Config.fast_llm/smart_llm桥接到ModelSpec
"""

    def __init__(self) -> None:
        self._models: dict[str, ModelSpec] = {}
        self._providers: dict[str, BaseProvider] = {}
        self._alias_map: dict[str, str] = {}

    def register_model(self, spec: ModelSpec) -> None:
        self._models[spec.model_id] = spec

    def register_models(self, specs: list[ModelSpec]) -> None:
        for spec in specs:
            self.register_model(spec)

    def unregister_model(self, model_id: str) -> None:
        self._models.pop(model_id, None)
        aliases_to_remove = [a for a, m in self._alias_map.items() if m == model_id]
        for a in aliases_to_remove:
            del self._alias_map[a]

    def add_alias(self, alias: str, model_id: str) -> None:
        self._alias_map[alias] = model_id

    def register_provider(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def unregister_provider(self, name: str) -> None:
        self._providers.pop(name, None)

    def get_model(self, model_id: str) -> ModelSpec | None:
        resolved = self._alias_map.get(model_id, model_id)
        return self._models.get(resolved)

    def get_provider(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def get_provider_for_model(self, model_id: str) -> BaseProvider | None:
        spec = self.get_model(model_id)
        if spec:
            return self._providers.get(spec.provider_name)
        return None

    def list_models(
        self,
        provider: str | None = None,
        tier: str | None = None,
        capability: Any = None,
        local_only: bool = False,
        free_only: bool = False,
    ) -> list[ModelSpec]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider_name == provider]
        if tier:
            models = [m for m in models if m.tier.value == tier]
        if capability is not None:
            models = [m for m in models if m.has_capability(capability)]
        if local_only:
            models = [m for m in models if m.is_local]
        if free_only:
            models = [m for m in models if m.is_free]
        return models

    def get_fallback_chain(self, model_id: str) -> list[str]:
        chain = [model_id]
        current = self.get_model(model_id)
        visited = {model_id}
        while current and current.degradation_target:
            target = current.degradation_target
            if target in visited:
                break
            visited.add(target)
            chain.append(target)
            current = self.get_model(target)
        return chain

    def load_builtin_specs(self) -> None:
        for spec_dict in BUILTIN_MODEL_SPECS:
            spec = ModelSpec.from_dict(spec_dict)
            self.register_model(spec)

    def load_from_file(self, path: str | Path) -> int:
        path = Path(path)
        if not path.exists():
            logger.warning("模型配置文件未找到: %s", path)
            return 0
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix in (".yaml", ".yml"):
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    logger.error("PyYAML未安装，无法加载YAML配置")
                    return 0
            else:
                data = json.load(f)
        models_data = data.get("models", [])
        count = 0
        for m in models_data:
            try:
                spec = ModelSpec.from_dict(m)
                self.register_model(spec)
                count += 1
            except Exception as e:
                logger.warning("无法加载模型规格 %s: %s", m.get("model_id", "?"), e)
        aliases = data.get("aliases", {})
        for alias, target in aliases.items():
            self.add_alias(alias, target)
        return count

    def resolve_model(self, model_id_or_alias: str) -> ModelSpec | None:
        return self.get_model(model_id_or_alias)

    @property
    def model_count(self) -> int:
        return len(self._models)

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    def summary(self) -> dict[str, Any]:
        by_provider: dict[str, int] = {}
        by_tier: dict[str, int] = {}
        for m in self._models.values():
            by_provider[m.provider_name] = by_provider.get(m.provider_name, 0) + 1
            by_tier[m.tier.value] = by_tier.get(m.tier.value, 0) + 1
        return {
            "total_models": self.model_count,
            "total_providers": self.provider_count,
            "by_provider": by_provider,
            "by_tier": by_tier,
            "aliases": len(self._alias_map),
        }


__all__ = ["ModelRegistry"]
