"""Feishu/Lark platform adapter skeleton.

This mirrors Hermes' gateway shape: WebSocket is the preferred transport,
webhook is available for deployments with a public HTTP endpoint, and inbound
vendor payloads are normalized to MessageEvent before entering the runtime.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import BasePlatformAdapter, MessageEvent, MessageType, PlatformConfig


class FeishuAdapter(BasePlatformAdapter):
    platform = "feishu"

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self.connection_mode = str(
            config.extra.get("connection_mode")
            or config.extra.get("mode")
            or "websocket"
        )
        self.transport = self.connection_mode

    async def connect(self) -> bool:
        if self.connection_mode not in {"websocket", "webhook"}:
            raise ValueError("Feishu connection_mode must be websocket or webhook")
        self.connected = bool(self.config.enabled)
        return self.connected

    def normalize_inbound(self, payload: dict[str, Any]) -> MessageEvent:
        event = payload.get("event", payload)
        message = event.get("message", {})
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {}) if isinstance(sender, dict) else {}
        user_id = (
            sender_id.get("open_id")
            or sender_id.get("user_id")
            or event.get("open_id")
            or event.get("user_id")
            or ""
        )
        content = self._parse_content(message.get("content", ""))
        return MessageEvent(
            platform=self.platform,
            chat_id=str(message.get("chat_id") or event.get("chat_id") or ""),
            user_id=str(user_id),
            text=content,
            message_type=self._message_type(str(message.get("message_type", "text"))),
            raw=payload,
            metadata={
                "message_id": message.get("message_id"),
                "root_id": message.get("root_id"),
                "connection_mode": self.connection_mode,
            },
            message_id=message.get("message_id"),
        )

    def is_authorized(self, user_id: str) -> bool:
        allowed = self.config.extra.get("allowed_users") or []
        if not allowed:
            return True
        return user_id in {str(item) for item in allowed}

    @staticmethod
    def _parse_content(content: Any) -> str:
        if isinstance(content, dict):
            return str(content.get("text") or content.get("content") or "")
        if not isinstance(content, str):
            return str(content or "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content
        if isinstance(parsed, dict):
            return str(parsed.get("text") or parsed.get("content") or content)
        return content

    @staticmethod
    def _message_type(value: str) -> MessageType:
        if value in {"image"}:
            return MessageType.IMAGE
        if value in {"file", "media"}:
            return MessageType.FILE
        if value in {"audio"}:
            return MessageType.AUDIO
        return MessageType.TEXT
