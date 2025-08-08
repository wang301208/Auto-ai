# Message Queue

Auto-GPT includes a lightweight publish/subscribe system for agents to exchange events.
It consists of a `MessageQueue` for dispatch and an optional `EventBus`
that persists events to a SQLite database.

## Architecture

```text
Agent -> MessageQueue -> (Redis Pub/Sub | in-process fallback) -> Subscribers
                                  |
                                  -> EventBus (SQLite)
```

* **MessageQueue** – routes messages between agents. If a Redis connection is
  configured it is used for Pub/Sub; otherwise Auto-GPT falls back to an
  internal dispatcher.
* **EventBus** – persists every event in `events.db` inside the agent's workspace
  for later inspection.

## Configuration
No configuration is required to use the in‑process queue. The event database is
created at `<workspace>/events.db` by default.

### Enabling Redis Pub/Sub

To share events between processes, provide Redis connection settings via
environment variables or your configuration file:

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=yourpassword  # optional
```

Run a local Redis instance using Docker:

```bash
docker run -p 6379:6379 redis
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

Auto-GPT defines additional structured event types. For skills, two relevant
events are provided:

* **`SKILL_CREATED`** – emitted when a new skill is registered. The payload
  contains `skill_name`, `version`, optional `description`, `tags`, and
  `parameters` describing the skill.
* **`SKILL_REQUESTED`** – emitted when an agent requests execution of a skill.
  The payload includes `skill_name` as well as optional `request_id`,
  `parameters`, `requester`, and extra `context`.

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

### Publishing skill events

```python
from autogpt.event_bus import SkillCreated, SkillRequested

# Skill registration
queue.publish(
    SkillCreated(
        skill_name="hello_world",
        version="1.0",
        description="Return a friendly greeting",
        tags=["example"],
        parameters={},
        source_agent="librarian",
    )
)

# Skill request
queue.publish(
    SkillRequested(
        skill_name="hello_world",
        request_id="req-1",
        parameters={},
        requester="agent",
        context={"message": "say hi"},
    )
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

