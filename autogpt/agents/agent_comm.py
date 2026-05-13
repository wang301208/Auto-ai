"""Inter-agent communication protocol.

Extends the existing MessageQueue with Agent-to-Agent routing:
- Point-to-point messages (send to specific agent)
- Request/Response pattern with correlation IDs and timeout
- Broadcast messages (publish to all agents of a role)
- Channel-based pub/sub for topic-oriented communication

Design principles:
  - Every message has a sender, optional target, and correlation_id
  - Requests block until response or timeout (async-friendly)
  - Broadcasts are non-blocking
  - All communication is auditable through the existing EventBus
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, DefaultDict

from ..event_bus.message_types import EventMessage
from ..event_bus.message_queue import MessageQueue

logger = logging.getLogger(__name__)


class AgentMessageType(Enum):
    DIRECT = "direct"
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    """A structured message between agents."""

    message_type: AgentMessageType
    sender_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    target_id: str | None = None
    target_role: str | None = None
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ttl_seconds: float | None = None
    priority: int = 0

    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        created = datetime.fromisoformat(self.timestamp)
        elapsed = (datetime.utcnow() - created).total_seconds()
        return elapsed > self.ttl_seconds

    def to_event(self) -> EventMessage:
        return EventMessage(
            event_type=f"agent.{self.message_type.value}",
            payload={
                "sender_id": self.sender_id,
                "target_id": self.target_id,
                "target_role": self.target_role,
                "correlation_id": self.correlation_id,
                "priority": self.priority,
                "data": self.payload,
            },
            source_agent=self.sender_id,
            timestamp=self.timestamp,
        )

    @classmethod
    def from_event(cls, event: EventMessage) -> AgentMessage | None:
        if not event.event_type.startswith("agent."):
            return None
        payload = event.payload if isinstance(event.payload, dict) else {}
        type_str = event.event_type.split(".", 1)[1]
        try:
            msg_type = AgentMessageType(type_str)
        except ValueError:
            return None
        return cls(
            message_type=msg_type,
            sender_id=payload.get("sender_id", event.source_agent or ""),
            payload=payload.get("data", {}),
            target_id=payload.get("target_id"),
            target_role=payload.get("target_role"),
            correlation_id=payload.get("correlation_id", ""),
            timestamp=event.timestamp,
            priority=payload.get("priority", 0),
        )


@dataclass
class AgentMailbox:
    """Inbox for a single agent with priority ordering."""

    agent_id: str
    role: str = ""
    _inbox: list[AgentMessage] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def deliver(self, message: AgentMessage) -> None:
        with self._lock:
            if message.is_expired():
                return
            self._inbox.append(message)
            self._inbox.sort(key=lambda m: -m.priority)

    def receive(self) -> AgentMessage | None:
        with self._lock:
            while self._inbox:
                msg = self._inbox.pop(0)
                if not msg.is_expired():
                    return msg
            return None

    def receive_all(self) -> list[AgentMessage]:
        with self._lock:
            valid = [m for m in self._inbox if not m.is_expired()]
            self._inbox.clear()
            return valid

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for m in self._inbox if not m.is_expired())


class AgentChannel:
    """Topic-based communication channel for group messaging."""

    def __init__(self, channel_id: str) -> None:
        self.channel_id = channel_id
        self._subscribers: dict[str, Callable[[AgentMessage], None]] = {}
        self._lock = threading.Lock()

    def subscribe(self, agent_id: str, handler: Callable[[AgentMessage], None]) -> None:
        with self._lock:
            self._subscribers[agent_id] = handler

    def unsubscribe(self, agent_id: str) -> None:
        with self._lock:
            self._subscribers.pop(agent_id, None)

    def publish(self, message: AgentMessage) -> int:
        delivered = 0
        with self._lock:
            for agent_id, handler in list(self._subscribers.items()):
                if agent_id != message.sender_id:
                    try:
                        handler(message)
                        delivered += 1
                    except Exception:
                        logger.warning(
                            "Channel %s: handler error for agent %s",
                            self.channel_id,
                            agent_id,
                        )
        return delivered

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


class AgentCommunicationBus:
    """Central communication hub for multi-agent coordination.

    Manages:
      - Agent mailboxes (point-to-point)
      - Request/response tracking (correlation ID matching)
      - Channels (topic-based pub/sub)
      - Role-based routing (broadcast to role)
      - Integration with the existing MessageQueue/EventBus
    """

    def __init__(self, message_queue: MessageQueue | None = None) -> None:
        self.mq = message_queue
        self._mailboxes: dict[str, AgentMailbox] = {}
        self._channels: dict[str, AgentChannel] = {}
        self._pending_requests: dict[str, asyncio.Future[AgentMessage]] = {}
        self._lock = threading.Lock()
        self._stats = {
            "direct_sent": 0,
            "broadcast_sent": 0,
            "requests_sent": 0,
            "responses_sent": 0,
            "requests_timed_out": 0,
        }

    def register_agent(self, agent_id: str, role: str = "") -> AgentMailbox:
        with self._lock:
            if agent_id in self._mailboxes:
                return self._mailboxes[agent_id]
            mailbox = AgentMailbox(agent_id=agent_id, role=role)
            self._mailboxes[agent_id] = mailbox
            return mailbox

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._mailboxes.pop(agent_id, None)
            for channel in self._channels.values():
                channel.unsubscribe(agent_id)

    def send(self, message: AgentMessage) -> bool:
        """Send a direct point-to-point message."""
        if message.target_id is None:
            logger.warning("Direct message without target_id: %s", message.correlation_id)
            return False

        with self._lock:
            mailbox = self._mailboxes.get(message.target_id)

        if mailbox is None:
            logger.warning("Target agent not registered: %s", message.target_id)
            return False

        mailbox.deliver(message)
        self._publish_to_mq(message)
        self._stats["direct_sent"] += 1
        return True

    def broadcast(
        self,
        sender_id: str,
        payload: dict[str, Any],
        target_role: str | None = None,
        priority: int = 0,
        ttl_seconds: float | None = None,
    ) -> int:
        """Broadcast a message to all agents or agents of a specific role."""
        message = AgentMessage(
            message_type=AgentMessageType.BROADCAST,
            sender_id=sender_id,
            payload=payload,
            target_role=target_role,
            priority=priority,
            ttl_seconds=ttl_seconds,
        )

        delivered = 0
        with self._lock:
            for mailbox in self._mailboxes.values():
                if mailbox.agent_id == sender_id:
                    continue
                if target_role and mailbox.role != target_role:
                    continue
                mailbox.deliver(message)
                delivered += 1

        self._publish_to_mq(message)
        self._stats["broadcast_sent"] += 1
        return delivered

    async def request(
        self,
        sender_id: str,
        target_id: str,
        payload: dict[str, Any],
        timeout_seconds: float = 30.0,
        priority: int = 0,
    ) -> AgentMessage:
        """Send a request and wait for the response.

        Raises asyncio.TimeoutError if no response within timeout.
        """
        correlation_id = uuid.uuid4().hex[:16]
        message = AgentMessage(
            message_type=AgentMessageType.REQUEST,
            sender_id=sender_id,
            target_id=target_id,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority,
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future[AgentMessage] = loop.create_future()

        with self._lock:
            self._pending_requests[correlation_id] = future

        self.send(message)
        self._stats["requests_sent"] += 1

        try:
            return await asyncio.wait_for(future, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            with self._lock:
                self._pending_requests.pop(correlation_id, None)
            self._stats["requests_timed_out"] += 1
            raise

    def respond(
        self,
        request: AgentMessage,
        sender_id: str,
        payload: dict[str, Any],
    ) -> bool:
        """Send a response to a previous request."""
        if request.target_id is None:
            request_target = request.sender_id
        else:
            request_target = request.sender_id

        response = AgentMessage(
            message_type=AgentMessageType.RESPONSE,
            sender_id=sender_id,
            target_id=request_target,
            payload=payload,
            correlation_id=request.correlation_id,
        )

        with self._lock:
            future = self._pending_requests.pop(request.correlation_id, None)

        if future is not None and not future.done():
            future.set_result(response)

        result = self.send(response)
        self._stats["responses_sent"] += 1
        return result

    def create_channel(self, channel_id: str) -> AgentChannel:
        with self._lock:
            if channel_id not in self._channels:
                self._channels[channel_id] = AgentChannel(channel_id)
            return self._channels[channel_id]

    def join_channel(self, channel_id: str, agent_id: str, handler: Callable[[AgentMessage], None] | None = None) -> None:
        channel = self.create_channel(channel_id)
        with self._lock:
            mailbox = self._mailboxes.get(agent_id)
        if handler is None and mailbox is not None:
            handler = mailbox.deliver
        if handler is not None:
            channel.subscribe(agent_id, handler)

    def leave_channel(self, channel_id: str, agent_id: str) -> None:
        with self._lock:
            channel = self._channels.get(channel_id)
        if channel is not None:
            channel.unsubscribe(agent_id)

    def publish_to_channel(
        self,
        channel_id: str,
        sender_id: str,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> int:
        with self._lock:
            channel = self._channels.get(channel_id)
        if channel is None:
            return 0
        message = AgentMessage(
            message_type=AgentMessageType.BROADCAST,
            sender_id=sender_id,
            payload=payload,
            priority=priority,
        )
        delivered = channel.publish(message)
        self._publish_to_mq(message)
        return delivered

    def receive(self, agent_id: str) -> AgentMessage | None:
        with self._lock:
            mailbox = self._mailboxes.get(agent_id)
        if mailbox is None:
            return None
        return mailbox.receive()

    def receive_all(self, agent_id: str) -> list[AgentMessage]:
        with self._lock:
            mailbox = self._mailboxes.get(agent_id)
        if mailbox is None:
            return []
        return mailbox.receive_all()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            mailbox_info = {
                aid: {"role": m.role, "pending": m.pending_count}
                for aid, m in self._mailboxes.items()
            }
            channel_info = {
                cid: ch.subscriber_count
                for cid, ch in self._channels.items()
            }
        return {
            **self._stats,
            "registered_agents": len(self._mailboxes),
            "active_channels": len(self._channels),
            "pending_requests": len(self._pending_requests),
            "mailboxes": mailbox_info,
            "channels": channel_info,
        }

    def _publish_to_mq(self, message: AgentMessage) -> None:
        if self.mq is not None:
            try:
                self.mq.publish(message.to_event())
            except Exception:
                pass


__all__ = [
    "AgentMessage",
    "AgentMessageType",
    "AgentMailbox",
    "AgentChannel",
    "AgentCommunicationBus",
]
