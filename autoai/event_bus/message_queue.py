from __future__ import annotations

"""Lightweight publish/subscribe message queue."""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, DefaultDict, Iterable

try:  # pragma: no cover - optional dependency
    from .event_bus import connect as redis_connect
    from .event_bus import publish as redis_publish
    from .event_bus import subscribe as redis_subscribe

    _HAS_REDIS = True
except Exception:  # pragma: no cover - library not available
    redis_connect = redis_publish = redis_subscribe = None  # type: ignore
    _HAS_REDIS = False

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from . import EventBus

from .message_types import EventMessage


class MessageQueue:
    """Publish/subscribe queue preferring Redis, with SQLite fallback."""

    def __init__(self, event_bus: "EventBus" | None = None) -> None:
        self.event_bus = event_bus
        self._handlers: DefaultDict[
            str, list[Callable[[EventMessage], None]]
        ] = defaultdict(list)
        self._redis_available = False

        if _HAS_REDIS:
            try:
                self._redis_available = redis_connect() is not None
            except Exception:
                self._redis_available = False
        if not self._redis_available:
            logging.getLogger(__name__).info(
                "Redis not configured; using in-process message queue."
            )

    # -- 核心 API -----------------------------------------------------
    def publish(self, event: EventMessage) -> None:
        """Publish ``event`` to subscribers and the optional :class:`EventBus`."""

        event_type = event.event_type

        if self._redis_available:
            try:
                redis_publish(event_type, event)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Redis publish failed; falling back to SQLite."
                )
                self._redis_available = False

        if not self._redis_available:
            for handler in list(self._handlers.get(event_type, [])):
                handler(event)

        if self.event_bus:
            self.event_bus.emit(event)

    def subscribe(
        self, event_type: str, handler: Callable[[EventMessage], None]
    ) -> None:
        """Subscribe ``handler`` to events of ``event_type``."""

        if self._redis_available:
            try:
                redis_subscribe(event_type, handler)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Redis subscribe failed; falling back to SQLite."
                )
                self._redis_available = False
                self._handlers[event_type].append(handler)
        else:
            self._handlers[event_type].append(handler)

    # -- Fallback helpers --------------------------------------------
    def get_events(self, limit: int | None = None) -> Iterable[EventMessage]:
        """Retrieve events from the underlying :class:`EventBus`, if any."""

        if not self.event_bus:
            return []
        return self.event_bus.get_events(limit)


__all__ = ["MessageQueue", "EventMessage"]
