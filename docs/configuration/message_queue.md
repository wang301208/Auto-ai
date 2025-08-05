# Message Queue

Auto-GPT includes a lightweight publish/subscribe system for agents to exchange events.
It consists of a `MessageQueue` for in-memory dispatch and an optional `EventBus`
that persists events to a SQLite database.

## Architecture

```text
Agent -> MessageQueue -> (PyPubSub backend | in-process fallback) -> Subscribers
                                  |
                                  -> EventBus (SQLite)
```

* **MessageQueue** – routes messages between agents. If the optional
  [PyPubSub](https://github.com/schollii/pypubsub) package is installed, it is
  used as a backend; otherwise Auto-GPT falls back to an internal dispatcher.
* **EventBus** – persists every event in `events.db` inside the agent's workspace
  for later inspection.

## Configuration

No configuration is required to use the built‑in queue. Installing PyPubSub
enables cross-module communication through a shared bus. The event database is
created at `<workspace>/events.db` by default.

### Installing the default backend (PyPubSub)

Install the optional dependency to enable the PyPubSub backend:

```bash
pip install agpt[pubsub]  # or: pip install pypubsub
```

Once installed, Auto‑GPT will automatically use PyPubSub when creating a
`MessageQueue`.

### Alternative brokers

You can run an external message broker and provide your own backend
integration. Example commands to start common brokers locally:

```bash
# Redis
docker run -p 6379:6379 redis

# RabbitMQ
docker run -p 5672:5672 rabbitmq
```

## Message format

Events use the `EventMessage` dataclass:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class EventMessage:
    event_type: str
    payload: dict[str, Any] | str | None = None
    source_agent: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

A standard message therefore contains:

```json
{
  "event_type": "status",
  "payload": {"msg": "hi"},
  "source_agent": "agent",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## Examples

### Publishing an event

```python
from autogpt.event_bus import EventBus, EventMessage, MessageQueue

bus = EventBus("events.db")
queue = MessageQueue(bus)

queue.publish(
    EventMessage(event_type="status", payload={"msg": "hi"}, source_agent="agent"),
)
```

### Subscribing to events

```python
from autogpt.event_bus import EventMessage


def handle_status(event: EventMessage) -> None:
    print(event.payload)

queue.subscribe("status", handle_status)
```

### Reading persisted events

```python
for event in queue.get_events():
    print(event)
```

