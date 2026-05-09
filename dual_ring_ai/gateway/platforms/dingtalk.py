"""DingTalk platform adapter skeleton."""

from __future__ import annotations

from typing import Any

from ..base import BasePlatformAdapter, MessageEvent, MessageType, PlatformConfig, SendResult


class DingTalkAdapter(BasePlatformAdapter):
    platform = "dingtalk"
    transport = "stream"

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self.session_webhooks: dict[str, str] = {}

    async def connect(self) -> bool:
        self.connected = bool(self.config.enabled)
        return self.connected

    def normalize_inbound(self, payload: dict[str, Any]) -> MessageEvent:
        chat_id = str(payload.get("conversationId") or payload.get("conversation_id") or "")
        user_id = str(payload.get("senderStaffId") or payload.get("sender_id") or "")
        text_payload = payload.get("text") or {}
        text = text_payload.get("content") if isinstance(text_payload, dict) else payload.get("content")
        session_webhook = str(payload.get("sessionWebhook") or payload.get("session_webhook") or "")
        if chat_id and session_webhook:
            self.session_webhooks[chat_id] = session_webhook
        return MessageEvent(
            platform=self.platform,
            chat_id=chat_id,
            user_id=user_id,
            text=str(text or ""),
            message_type=MessageType.TEXT,
            raw=payload,
            metadata={
                "session_webhook": session_webhook,
                "message_id": payload.get("msgId") or payload.get("msg_id"),
                "is_at": bool(payload.get("isInAtList") or payload.get("is_at")),
            },
            message_id=payload.get("msgId") or payload.get("msg_id"),
        )

    async def send(
        self,
        chat_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        metadata = metadata or {}
        session_webhook = metadata.get("session_webhook") or self.session_webhooks.get(chat_id)
        result = await super().send(
            chat_id,
            content,
            metadata={**metadata, "session_webhook": session_webhook, "format": "markdown"},
        )
        return result

    def is_authorized(self, user_id: str) -> bool:
        allowed = self.config.extra.get("allowed_users") or []
        allow_all = bool(self.config.extra.get("allow_all_users", False))
        if allow_all:
            return True
        if not allowed:
            return False
        return user_id in {str(item) for item in allowed}
