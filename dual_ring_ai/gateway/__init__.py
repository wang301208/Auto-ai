"""Messaging gateway primitives for platform adapters."""

from .base import (
    BasePlatformAdapter,
    GatewayRunner,
    MessageEvent,
    MessageType,
    PlatformConfig,
    SendResult,
)

__all__ = [
    "BasePlatformAdapter",
    "GatewayRunner",
    "MessageEvent",
    "MessageType",
    "PlatformConfig",
    "SendResult",
]
