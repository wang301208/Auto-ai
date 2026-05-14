"""Unified model routing layer.

Bridges V1 (llm/providers/openai.py), V2 (core/resource/model_providers/), and
TUI Gateway presets into a single ModelRegistry + ModelRouter system.

Providers:
  - BaseProvider: abstract interface for all model providers
  - OpenAIProvider: wraps existing V1 create_chat_completion
  - OllamaProvider: local model support via Ollama API
  - OpenRouterProvider: proxy provider via OpenRouter
  - DeepSeekProvider: DeepSeek API support

Routing:
  - ModelRouter: selects provider+model based on task features, budget, availability
  - RoutingPolicy: configurable routing rules (fallback chains, budget limits)
  - ModelSpec: unified model specification across all providers
"""

from .base_provider import BaseProvider, ProviderHealth
from .model_spec import ModelSpec, ModelCapability, ModelTier
from .model_registry import ModelRegistry
from .model_router import ModelRouter, RoutingPolicy, RoutingDecision, RoutingStrategy
from .openai_provider import OpenAICompatProvider
from .ollama_provider import OllamaProvider
from .streaming import (
    StreamEventType,
    StreamingEvent,
    StreamStats,
    StreamEmitter,
    StreamingChat,
    StreamBuffer,
)

__all__ = [
    "BaseProvider",
    "ProviderHealth",
    "ModelSpec",
    "ModelCapability",
    "ModelTier",
    "ModelRegistry",
    "ModelRouter",
    "RoutingPolicy",
    "RoutingDecision",
    "RoutingStrategy",
    "OpenAICompatProvider",
    "OllamaProvider",
    "StreamEventType",
    "StreamingEvent",
    "StreamStats",
    "StreamEmitter",
    "StreamingChat",
    "StreamBuffer",
]
