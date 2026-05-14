"""Ollama provider: local model support via Ollama REST API.

Auto-detects local Ollama service at http://localhost:11434.
Supports streaming, multi-modal (llava), and all Ollama models.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from .base_provider import (
    BaseProvider,
    ChatMessage,
    ChatResponse,
    EmbeddingResponse,
    ProviderHealth,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 300.0


class OllamaProvider(BaseProvider):
    """Provider for locally-hosted models via Ollama.

    Features:
      - Auto-detect Ollama service availability
      - List pulled models via /api/tags
      - Chat completion via /api/chat
      - Embedding via /api/embeddings
      - Model pulling via /api/pull (optional)
      - Health check via /api/version
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        default_model: str = "llama3.1:8b",
        embedding_model: str = "nomic-embed-text",
        timeout: float = OLLAMA_TIMEOUT,
        auto_detect: bool = True,
    ) -> None:
        super().__init__(name="ollama", base_url=base_url)
        self.default_model = default_model
        self.embedding_model = embedding_model
        self.timeout = timeout
        self._models_cache: list[str] | None = None
        self._detected = False
        if auto_detect:
            self._detect_service()

    def _detect_service(self) -> None:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/version")
                if resp.status_code == 200:
                    self._detected = True
                    self._health.status = ProviderStatus.AVAILABLE
                    version_info = resp.json()
                    logger.info(
                        "Ollama detected at %s (version: %s)",
                        self.base_url,
                        version_info.get("version", "unknown"),
                    )
                else:
                    self._health.status = ProviderStatus.UNAVAILABLE
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
            logger.debug("Ollama not detected at %s", self.base_url)

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
            result = await self._call_chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
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
            result = await self._call_embedding(text=text, model=model)
            elapsed = (time.monotonic() - start_time) * 1000
            self._health.record_success(elapsed)
            return result
        except Exception as e:
            self._health.record_failure()
            raise

    async def check_health(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/version")
                if resp.status_code == 200:
                    self._health.status = ProviderStatus.AVAILABLE
                    self._detected = True
                else:
                    self._health.status = ProviderStatus.UNAVAILABLE
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
        self._health.last_check_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return self._health

    def list_models(self) -> list[str]:
        if self._models_cache is not None:
            return self._models_cache
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    self._models_cache = sorted(m.get("name", "") for m in data.get("models", []))
                else:
                    self._models_cache = [self.default_model]
        except Exception:
            self._models_cache = [self.default_model]
        return self._models_cache

    async def pull_model(self, model_name: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": False},
                ) as resp:
                    if resp.status_code == 200:
                        self._models_cache = None
                        logger.info("Pulled model: %s", model_name)
                        return True
                    logger.error("Failed to pull model %s: %s", model_name, resp.status_code)
                    return False
        except Exception as e:
            logger.error("Error pulling model %s: %s", model_name, e)
            return False

    def is_model_pulled(self, model_name: str) -> bool:
        return model_name in self.list_models()

    async def _call_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]

        payload: dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return ChatResponse(
            content=content,
            model=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=data,
        )

    async def _call_embedding(
        self,
        text: str,
        model: str,
    ) -> EmbeddingResponse:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()

        embedding = data.get("embedding", [])
        prompt_tokens = data.get("prompt_eval_count", 0)

        return EmbeddingResponse(
            embedding=embedding,
            model=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
        )

    @property
    def is_detected(self) -> bool:
        return self._detected

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
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        payload: dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield StreamingEvent(
                                type=StreamEventType.THINK_TOKEN,
                                content=content,
                                model=model,
                                provider=self.name,
                            )
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    def get_model_info(self, model_name: str) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/show",
                    json={"name": model_name},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None


__all__ = ["OllamaProvider", "DEFAULT_OLLAMA_URL"]
