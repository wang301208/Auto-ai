from __future__ import annotations

"""Lightweight publish/subscribe message queue with optional backend."""

from collections import defaultdict
from typing import TYPE_CHECKING, Callable, DefaultDict, Iterable

try:  # pragma: no cover - optional dependency
    from pubsub import pub

    _HAS_PUBSUB = True
except Exception:  # pragma: no cover - library not available
    pub = None
    _HAS_PUBSUB = False

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from . import EventBus

from .message_types import EventMessage


class MessageQueue:
    """Publish/subscribe queue with graceful fallback."""

    def __init__(self, event_bus: "EventBus" | None = None) -> None:
        self.event_bus = event_bus
        self._handlers: DefaultDict[
            str, list[Callable[[EventMessage], None]]
        ] = defaultdict(list)

    # -- Core API -----------------------------------------------------
    def publish(self, event: EventMessage) -> None:
        """Publish ``event`` to subscribers and the optional :class:`EventBus`."""

        event_type = event.event_type

        if _HAS_PUBSUB:
            pub.sendMessage(event_type, message=event)
        else:
            for handler in list(self._handlers.get(event_type, [])):
                handler(event)

        if self.event_bus:
            self.event_bus.emit(event)

    def subscribe(
        self, event_type: str, handler: Callable[[EventMessage], None]
    ) -> None:
        """Subscribe ``handler`` to events of ``event_type``."""

        if _HAS_PUBSUB:
            pub.subscribe(lambda message=None: handler(message), event_type)
        else:
            self._handlers[event_type].append(handler)

    # -- Fallback helpers --------------------------------------------
    def get_events(self, limit: int | None = None) -> Iterable[EventMessage]:
        """Retrieve events from the underlying :class:`EventBus`, if any."""

        if not self.event_bus:
            return []
        return self.event_bus.get_events(limit)


__all__ = ["MessageQueue", "EventMessage"]
