"""Unified model specification across all providers."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ModelCapability(enum.Flag):
    CHAT = enum.auto()
    COMPLETION = enum.auto()
    EMBEDDING = enum.auto()
    FUNCTION_CALLING = enum.auto()
    VISION = enum.auto()
    STREAMING = enum.auto()
    REASONING = enum.auto()


class ModelTier(enum.Enum):
    FAST = "fast"
    BALANCED = "balanced"
    SMART = "smart"
    EMBEDDING = "embedding"


@dataclass
class ModelSpec:
    model_id: str
    provider_name: str
    display_name: str = ""
    tier: ModelTier = ModelTier.BALANCED
    capabilities: ModelCapability = ModelCapability.CHAT
    max_context_tokens: int = 4096
    max_output_tokens: int = 2048
    prompt_token_cost_per_1k: float = 0.0
    completion_token_cost_per_1k: float = 0.0
    supports_streaming: bool = False
    supports_functions: bool = False
    supports_vision: bool = False
    is_local: bool = False
    degradation_target: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cost_per_1k_output(self) -> float:
        return self.completion_token_cost_per_1k

    @property
    def cost_per_1k_input(self) -> float:
        return self.prompt_token_cost_per_1k

    @property
    def is_free(self) -> bool:
        return self.prompt_token_cost_per_1k == 0 and self.completion_token_cost_per_1k == 0

    def has_capability(self, cap: ModelCapability) -> bool:
        return bool(self.capabilities & cap)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "tier": self.tier.value,
            "capabilities": self.capabilities.value,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "prompt_token_cost_per_1k": self.prompt_token_cost_per_1k,
            "completion_token_cost_per_1k": self.completion_token_cost_per_1k,
            "is_local": self.is_local,
            "degradation_target": self.degradation_target,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModelSpec:
        caps = d.get("capabilities", 1)
        if isinstance(caps, int):
            caps = ModelCapability(caps)
        tier = d.get("tier", "balanced")
        if isinstance(tier, str):
            tier = ModelTier(tier)
        return cls(
            model_id=d["model_id"],
            provider_name=d["provider_name"],
            display_name=d.get("display_name", d["model_id"]),
            tier=tier,
            capabilities=caps,
            max_context_tokens=d.get("max_context_tokens", 4096),
            max_output_tokens=d.get("max_output_tokens", 2048),
            prompt_token_cost_per_1k=d.get("prompt_token_cost_per_1k", 0.0),
            completion_token_cost_per_1k=d.get("completion_token_cost_per_1k", 0.0),
            is_local=d.get("is_local", False),
            degradation_target=d.get("degradation_target"),
        )


def _caps(*flags: ModelCapability) -> int:
    result = flags[0]
    for f in flags[1:]:
        result = result | f
    return result.value


BUILTIN_MODEL_SPECS: list[dict[str, Any]] = [
    {
        "model_id": "gpt-4o",
        "provider_name": "openai",
        "display_name": "GPT-4o",
        "tier": "smart",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING, ModelCapability.VISION),
        "max_context_tokens": 128000,
        "max_output_tokens": 16384,
        "prompt_token_cost_per_1k": 0.0025,
        "completion_token_cost_per_1k": 0.01,
        "supports_functions": True,
        "supports_streaming": True,
        "supports_vision": True,
        "degradation_target": "gpt-4o-mini",
    },
    {
        "model_id": "gpt-4o-mini",
        "provider_name": "openai",
        "display_name": "GPT-4o Mini",
        "tier": "fast",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING),
        "max_context_tokens": 128000,
        "max_output_tokens": 16384,
        "prompt_token_cost_per_1k": 0.00015,
        "completion_token_cost_per_1k": 0.0006,
        "supports_functions": True,
        "supports_streaming": True,
        "degradation_target": "gpt-3.5-turbo",
    },
    {
        "model_id": "gpt-3.5-turbo",
        "provider_name": "openai",
        "display_name": "GPT-3.5 Turbo",
        "tier": "fast",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING),
        "max_context_tokens": 16384,
        "max_output_tokens": 4096,
        "prompt_token_cost_per_1k": 0.0005,
        "completion_token_cost_per_1k": 0.0015,
        "supports_functions": True,
        "supports_streaming": True,
    },
    {
        "model_id": "text-embedding-ada-002",
        "provider_name": "openai",
        "display_name": "Ada Embedding V2",
        "tier": "embedding",
        "capabilities": ModelCapability.EMBEDDING.value,
        "max_context_tokens": 8192,
        "prompt_token_cost_per_1k": 0.0001,
    },
    {
        "model_id": "deepseek-chat",
        "provider_name": "deepseek",
        "display_name": "DeepSeek Chat",
        "tier": "balanced",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING),
        "max_context_tokens": 65536,
        "max_output_tokens": 8192,
        "prompt_token_cost_per_1k": 0.00014,
        "completion_token_cost_per_1k": 0.00028,
        "supports_functions": True,
        "supports_streaming": True,
    },
    {
        "model_id": "deepseek-reasoner",
        "provider_name": "deepseek",
        "display_name": "DeepSeek Reasoner",
        "tier": "smart",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.REASONING, ModelCapability.STREAMING),
        "max_context_tokens": 65536,
        "max_output_tokens": 8192,
        "prompt_token_cost_per_1k": 0.00055,
        "completion_token_cost_per_1k": 0.00219,
        "supports_streaming": True,
        "degradation_target": "deepseek-chat",
    },
    {
        "model_id": "claude-3-5-sonnet-latest",
        "provider_name": "anthropic",
        "display_name": "Claude 3.5 Sonnet",
        "tier": "smart",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING, ModelCapability.VISION),
        "max_context_tokens": 200000,
        "max_output_tokens": 8192,
        "prompt_token_cost_per_1k": 0.003,
        "completion_token_cost_per_1k": 0.015,
        "supports_functions": True,
        "supports_streaming": True,
        "supports_vision": True,
        "degradation_target": "deepseek-chat",
    },
    {
        "model_id": "llama3.1:8b",
        "provider_name": "ollama",
        "display_name": "Llama 3.1 8B (Local)",
        "tier": "fast",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.STREAMING),
        "max_context_tokens": 8192,
        "max_output_tokens": 4096,
        "is_local": True,
        "supports_streaming": True,
    },
    {
        "model_id": "qwen2.5:14b",
        "provider_name": "ollama",
        "display_name": "Qwen 2.5 14B (Local)",
        "tier": "balanced",
        "capabilities": _caps(ModelCapability.CHAT, ModelCapability.STREAMING),
        "max_context_tokens": 32768,
        "max_output_tokens": 8192,
        "is_local": True,
        "supports_streaming": True,
    },
]


__all__ = [
    "ModelCapability",
    "ModelTier",
    "ModelSpec",
    "BUILTIN_MODEL_SPECS",
]
