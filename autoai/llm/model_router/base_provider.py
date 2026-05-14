"""Abstract base provider interface for the unified model routing layer."""

from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Coroutine


class ProviderStatus(enum.Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderHealth:
    status: ProviderStatus = ProviderStatus.AVAILABLE
    latency_ms: float = 0.0
    last_check_at: str = ""
    error_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.error_count + self.success_count
        return self.success_count / total if total > 0 else 1.0

    def record_success(self, latency_ms: float) -> None:
        self.success_count += 1
        self.latency_ms = latency_ms
        self.last_check_at = datetime.now(timezone.utc).isoformat()
        if self.status == ProviderStatus.DEGRADED and self.success_rate > 0.9:
            self.status = ProviderStatus.AVAILABLE

    def record_failure(self) -> None:
        self.error_count += 1
        self.last_check_at = datetime.now(timezone.utc).isoformat()
        if self.success_rate < 0.5:
            self.status = ProviderStatus.DEGRADED
        if self.error_count > 10 and self.success_rate < 0.1:
            self.status = ProviderStatus.UNAVAILABLE


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    raw_response: Any = None


@dataclass
class EmbeddingResponse:
    embedding: list[float]
    model: str
    provider: str
    prompt_tokens: int = 0
    total_cost: float = 0.0


class BaseProvider(abc.ABC):
    """Abstract base class for all model providers.

    Subclasses must implement:
      - async chat() -> ChatResponse
      - async embed() -> EmbeddingResponse
      - async check_health() -> ProviderHealth
      - list_models() -> list[str]
    """

    def __init__(self, name: str, base_url: str = "", api_key: str = "") -> None:
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self._health = ProviderHealth()

    @property
    def health(self) -> ProviderHealth:
        return self._health

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        functions: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        ...

    @abc.abstractmethod
    async def embed(
        self,
        text: str,
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        ...

    @abc.abstractmethod
    async def check_health(self) -> ProviderHealth:
        ...

    @abc.abstractmethod
    def list_models(self) -> list[str]:
        ...

    @property
    def is_available(self) -> bool:
        return self._health.status != ProviderStatus.UNAVAILABLE

    def get_model_info(self, model_name: str) -> dict[str, Any] | None:
        return None

    async def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4


__all__ = [
    "ProviderStatus",
    "ProviderHealth",
    "ChatMessage",
    "ChatResponse",
    "EmbeddingResponse",
    "BaseProvider",
]
