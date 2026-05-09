"""Shared messaging gateway abstractions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    TEXT = "text"
    COMMAND = "command"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class MessageEvent:
    platform: str
    chat_id: str
    user_id: str
    text: str
    message_type: MessageType = MessageType.TEXT
    raw: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    message_id: str | None = None


@dataclass
class SendResult:
    status: str
    platform: str
    chat_id: str
    message_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "platform": self.platform,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "error": self.error,
        }


@dataclass
class PlatformConfig:
    name: str
    enabled: bool = False
    token: str | None = None
    api_key: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BasePlatformAdapter:
    """Base class for chat platform adapters."""

    platform: str = "base"
    transport: str = "memory"

    def __init__(self, config: PlatformConfig) -> None:
        self.config = config
        self.name = config.name
        self.runner: GatewayRunner | None = None
        self.connected = False
        self.sent_messages: list[dict[str, Any]] = []

    async def connect(self) -> bool:
        self.connected = bool(self.config.enabled)
        return self.connected

    async def disconnect(self) -> None:
        self.connected = False

    async def receive(self, event: MessageEvent | dict[str, Any]) -> dict[str, Any]:
        normalized = event if isinstance(event, MessageEvent) else self.normalize_inbound(event)
        if not self.is_authorized(normalized.user_id):
            return SendResult(
                status="unauthorized",
                platform=self.platform,
                chat_id=normalized.chat_id,
                error="sender is not authorized",
            ).to_dict()
        if self.runner is None:
            raise RuntimeError(f"{self.platform} adapter is not registered with a gateway runner")
        return await self.runner.handle_event(normalized)

    def normalize_inbound(self, payload: dict[str, Any]) -> MessageEvent:
        raise NotImplementedError

    async def send(
        self,
        chat_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        message_id = f"{self.platform}_{len(self.sent_messages) + 1}"
        self.sent_messages.append(
            {
                "platform": self.platform,
                "chat_id": chat_id,
                "content": content,
                "metadata": metadata or {},
                "message_id": message_id,
            }
        )
        return SendResult(
            status="sent",
            platform=self.platform,
            chat_id=chat_id,
            message_id=message_id,
        )

    def is_authorized(self, user_id: str) -> bool:
        allowed = self.config.extra.get("allowed_users") or self.config.extra.get("allow_from")
        if not allowed:
            return True
        return user_id in {str(item) for item in allowed}


class GatewayRunner:
    """Route normalized platform messages into the local runtime."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.adapters: dict[str, BasePlatformAdapter] = {}
        self.history: list[dict[str, Any]] = []
        self._locks: dict[str, asyncio.Lock] = {}

    def register(self, adapter: BasePlatformAdapter) -> None:
        adapter.runner = self
        self.adapters[adapter.platform] = adapter

    async def handle_event(self, event: MessageEvent) -> dict[str, Any]:
        adapter = self.adapters.get(event.platform)
        if adapter is None:
            raise ValueError(f"platform adapter not registered: {event.platform}")
        lock = self._locks.setdefault(f"{event.platform}:{event.chat_id}", asyncio.Lock())
        async with lock:
            response = self.runtime.handle_interaction(event.text)
            text = str(response.get("response_text", ""))
            result = await adapter.send(event.chat_id, text, metadata=event.metadata)
            self.history.append(
                {
                    "event": event,
                    "response": response,
                    "send_result": result.to_dict(),
                }
            )
            return result.to_dict()
