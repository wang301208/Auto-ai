from pathlib import Path

from autogpt.event_bus import EventBus, EventMessage


def test_event_bus_emit_and_read(tmp_path: Path) -> None:
    bus = EventBus(tmp_path / "events.db")
    bus.emit(
        EventMessage(event_type="test", payload={"foo": "bar"}, source_agent="test")
    )
    events = list(bus.get_events())
    assert len(events) == 1
    assert events[0].event_type == "test"
    assert isinstance(events[0].payload, dict)
    assert events[0].payload["foo"] == "bar"
    assert events[0].source_agent == "test"
