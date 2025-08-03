from pathlib import Path

from autogpt.event_bus import EventBus


def test_event_bus_emit_and_read(tmp_path: Path) -> None:
    bus = EventBus(tmp_path / "events.db")
    bus.emit("test", {"foo": "bar"})
    events = list(bus.get_events())
    assert len(events) == 1
    assert events[0]["event_type"] == "test"
    assert events[0]["payload"]["foo"] == "bar"
