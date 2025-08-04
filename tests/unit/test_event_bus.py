from pathlib import Path

import pytest

from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    DiagnosisComplete,
    EventBus,
    EventMessage,
    MessageQueue,
)


@pytest.fixture
def event_bus(tmp_path: Path) -> EventBus:
    """Event bus backed by a temporary SQLite database."""
    return EventBus(tmp_path / "events.db")


@pytest.fixture
def message_queue(event_bus: EventBus, monkeypatch: pytest.MonkeyPatch) -> MessageQueue:
    """Message queue using the fallback implementation without external backend."""

    # Ensure tests do not depend on the optional `pubsub` package
    monkeypatch.setattr("autogpt.event_bus.message_queue._HAS_PUBSUB", False)
    return MessageQueue(event_bus)


def test_event_bus_emit_and_read(event_bus: EventBus) -> None:
    event_bus.emit(
        EventMessage(event_type="test", payload={"foo": "bar"}, source_agent="test")
    )
    events = list(event_bus.get_events())
    assert len(events) == 1
    assert events[0].event_type == "test"
    assert isinstance(events[0].payload, dict)
    assert events[0].payload["foo"] == "bar"
    assert events[0].source_agent == "test"


def test_message_queue_diagnosis_complete(message_queue: MessageQueue) -> None:
    received: list[DiagnosisComplete] = []
    message_queue.subscribe(DIAGNOSIS_COMPLETE, lambda msg: received.append(msg))

    event = DiagnosisComplete(
        summary="Diagnostics complete",
        actionable_recommendations="Fix it",
        source_agent="archaeologist",
    )
    message_queue.publish(event)

    assert len(received) == 1
    assert isinstance(received[0], DiagnosisComplete)
    assert received[0].summary == "Diagnostics complete"

    events = list(message_queue.get_events())
    assert len(events) == 1
    assert isinstance(events[0], DiagnosisComplete)
    assert events[0].summary == "Diagnostics complete"


def test_message_queue_publish_from_multiple_sources(
    message_queue: MessageQueue,
) -> None:
    received: list[EventMessage] = []

    message_queue.subscribe("test_event", lambda msg: received.append(msg))

    message_queue.publish(
        EventMessage(
            event_type="test_event",
            payload={"value": 1},
            source_agent="agent-1",
        )
    )
    message_queue.publish(
        EventMessage(
            event_type="test_event",
            payload={"value": 2},
            source_agent="agent-2",
        )
    )

    assert len(received) == 2
    assert {e.source_agent for e in received} == {"agent-1", "agent-2"}

    events = list(message_queue.get_events())
    assert len(events) == 2


def test_message_queue_backend_failure(
    message_queue: MessageQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[EventMessage] = []
    message_queue.subscribe("boom", lambda msg: received.append(msg))

    def failing_emit(event: EventMessage) -> None:
        raise RuntimeError("backend failure")

    monkeypatch.setattr(message_queue.event_bus, "emit", failing_emit)

    with pytest.raises(RuntimeError):
        message_queue.publish(EventMessage(event_type="boom", payload=None))

    # Subscriber was still notified before the failure
    assert len(received) == 1


def test_event_bus_handles_malformed_payload(event_bus: EventBus) -> None:
    cur = event_bus.connection.cursor()
    cur.execute(
        "INSERT INTO events(timestamp, event_type, payload, source_agent) VALUES (?, ?, ?, ?)",
        ("ts", "malformed", "{not json", "agent"),
    )
    event_bus.connection.commit()

    events = list(event_bus.get_events())
    assert len(events) == 1
    assert events[0].payload == "{not json"
