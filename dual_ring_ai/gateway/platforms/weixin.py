"""Personal Weixin/WeChat adapter skeleton using iLink-style long polling."""

from __future__ import annotations

from typing import Any

from ..base import BasePlatformAdapter, MessageEvent, MessageType, PlatformConfig, SendResult


class WeixinAdapter(BasePlatformAdapter):
    platform = "weixin"
    transport = "long_poll"

    async def connect(self) -> bool:
        self.connected = bool(self.config.enabled)
        return self.connected

    def normalize_inbound(self, payload: dict[str, Any]) -> MessageEvent:
        chat_id = str(payload.get("chat_id") or payload.get("from_user") or payload.get("peer_id") or "")
        user_id = str(payload.get("from_user") or payload.get("sender") or "")
        return MessageEvent(
            platform=self.platform,
            chat_id=chat_id,
            user_id=user_id,
            text=str(payload.get("content") or payload.get("text") or ""),
            message_type=self._message_type(str(payload.get("msg_type") or payload.get("type") or "text")),
            raw=payload,
            metadata={
                "context_token": payload.get("context_token"),
                "message_id": payload.get("msg_id") or payload.get("message_id"),
            },
            message_id=payload.get("msg_id") or payload.get("message_id"),
        )

    async def send(
        self,
        chat_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        return await super().send(
            chat_id,
            content,
            metadata={**(metadata or {}), "transport": self.transport},
        )

    def is_authorized(self, user_id: str) -> bool:
        policy = str(self.config.extra.get("dm_policy") or "open")
        if policy == "disabled":
            return False
        allowed = self.config.extra.get("allow_from") or self.config.extra.get("allowed_users") or []
        if policy == "allowlist":
            return user_id in {str(item) for item in allowed}
        return True

    @staticmethod
    def _message_type(value: str) -> MessageType:
        if value in {"image", "pic"}:
            return MessageType.IMAGE
        if value in {"file", "document"}:
            return MessageType.FILE
        if value in {"voice", "audio"}:
            return MessageType.AUDIO
        if value in {"video"}:
            return MessageType.VIDEO
        return MessageType.TEXT
