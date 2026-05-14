"""OpenAI-compatible provider implementation.

Wraps the existing V1 create_chat_completion / create_embedding into the
unified BaseProvider interface. Also serves as base for any OpenAI-compatible
API (OpenRouter, DeepSeek, Azure, etc.).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .base_provider import (
    BaseProvider,
    ChatMessage,
    ChatResponse,
    EmbeddingResponse,
    ProviderHealth,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class OpenAICompatProvider(BaseProvider):
    """Provider for OpenAI and any OpenAI-compatible API.

    For non-OpenAI providers (OpenRouter, DeepSeek, etc.), simply pass
    the appropriate base_url and api_key.
    """

    def __init__(
        self,
        name: str = "openai",
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        api_type: str = "openai",
        api_version: str | None = None,
        deployment_id: str | None = None,
        organization: str | None = None,
        default_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-ada-002",
        timeout: float = 120.0,
    ) -> None:
        super().__init__(name=name, base_url=base_url, api_key=api_key)
        self.api_type = api_type
        self.api_version = api_version
        self.deployment_id = deployment_id
        self.organization = organization
        self.default_model = default_model
        self.embedding_model = embedding_model
        self.timeout = timeout
        self._models_cache: list[str] | None = None

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        functions: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        model = model or self.default_model
        start_time = time.monotonic()
        try:
            result = await self._call_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                **kwargs,
            )
            elapsed = (time.monotonic() - start_time) * 1000
            self._health.record_success(elapsed)
            return result
        except Exception as e:
            self._health.record_failure()
            raise

    async def embed(
        self,
        text: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        model = model or self.embedding_model
        start_time = time.monotonic()
        try:
            result = await self._call_embedding(text=text, model=model, **kwargs)
            elapsed = (time.monotonic() - start_time) * 1000
            self._health.record_success(elapsed)
            return result
        except Exception as e:
            self._health.record_failure()
            raise

    async def check_health(self) -> ProviderHealth:
        try:
            client = self._get_async_client()
            await client.models.list(limit=1)
            self._health.status = ProviderStatus.AVAILABLE
        except Exception as e:
            self._health.status = ProviderStatus.UNAVAILABLE
            logger.warning("Provider %s health check failed: %s", self.name, e)
        self._health.last_check_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return self._health

    def list_models(self) -> list[str]:
        if self._models_cache is not None:
            return self._models_cache
        try:
            client = self._get_sync_client()
            models_resp = client.models.list()
            self._models_cache = sorted(
                m.id for m in models_resp.data if "gpt" in m.id or "embed" in m.id
            )
        except Exception as e:
            logger.warning("Failed to list models for %s: %s", self.name, e)
            self._models_cache = [self.default_model]
        return self._models_cache

    async def _call_chat_completion(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        functions: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        client = self._get_async_client()
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]

        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temperature,
        }
        if max_tokens:
            create_kwargs["max_tokens"] = max_tokens
        if functions:
            create_kwargs["functions"] = functions

        create_kwargs.update(kwargs)

        response = await client.chat.completions.create(**create_kwargs)
        choice = response.choices[0]

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        return ChatResponse(
            content=choice.message.content or "",
            model=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=response,
        )

    async def _call_embedding(
        self,
        text: str,
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        client = self._get_async_client()
        response = await client.embeddings.create(input=text, model=model, **kwargs)
        data = response.data[0]

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0

        return EmbeddingResponse(
            embedding=data.embedding,
            model=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
        )

    def _get_async_client(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required for OpenAICompatProvider")

        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url and self.api_type != "azure":
            kwargs["base_url"] = self.base_url
        if self.organization:
            kwargs["organization"] = self.organization

        if self.api_type == "azure":
            from openai import AsyncAzureOpenAI
            azure_kwargs: dict[str, Any] = {"timeout": self.timeout}
            if self.api_key:
                azure_kwargs["api_key"] = self.api_key
            if self.api_version:
                azure_kwargs["api_version"] = self.api_version
            if self.base_url:
                azure_kwargs["azure_endpoint"] = self.base_url
            return AsyncAzureOpenAI(**azure_kwargs)

        return AsyncOpenAI(**kwargs)

    def _get_sync_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required for OpenAICompatProvider")

        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url and self.api_type != "azure":
            kwargs["base_url"] = self.base_url
        if self.organization:
            kwargs["organization"] = self.organization

        if self.api_type == "azure":
            from openai import AzureOpenAI
            azure_kwargs: dict[str, Any] = {"timeout": self.timeout}
            if self.api_key:
                azure_kwargs["api_key"] = self.api_key
            if self.api_version:
                azure_kwargs["api_version"] = self.api_version
            if self.base_url:
                azure_kwargs["azure_endpoint"] = self.base_url
            return AzureOpenAI(**azure_kwargs)

        return OpenAI(**kwargs)

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        from .streaming import StreamingEvent, StreamEventType
        model = model or self.default_model
        client = self._get_async_client()
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            create_kwargs["max_tokens"] = max_tokens
        create_kwargs.update(kwargs)

        stream = await client.chat.completions.create(**create_kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield StreamingEvent(
                    type=StreamEventType.THINK_TOKEN,
                    content=delta.content,
                    model=model,
                    provider=self.name,
                )

    @classmethod
    def from_config(cls, config: Any) -> OpenAICompatProvider:
        return cls(
            name="openai",
            api_key=getattr(config, "openai_api_key", "") or "",
            base_url=getattr(config, "openai_api_base", "") or "https://api.openai.com/v1",
            api_type=getattr(config, "openai_api_type", "openai") or "openai",
            api_version=getattr(config, "openai_api_version", None),
            organization=getattr(config, "openai_organization", None),
            default_model=getattr(config, "smart_llm", "gpt-4o-mini"),
            embedding_model=getattr(config, "embedding_model", "text-embedding-ada-002"),
        )

    @classmethod
    def from_preset(cls, preset: dict[str, Any], api_key: str = "") -> OpenAICompatProvider:
        return cls(
            name=preset.get("slug", "custom"),
            base_url=preset.get("base_url", "https://api.openai.com/v1"),
            api_key=api_key,
            default_model=preset.get("models", ["gpt-4o-mini"])[0],
        )


__all__ = ["OpenAICompatProvider"]
