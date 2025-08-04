from pathlib import Path

from autogpt.event_bus import EventBus, MessageQueue
from autogpt.self_improve import PluginTodoQueue


def test_plugin_todo_queue(tmp_path: Path) -> None:
    event_bus = EventBus(tmp_path / "events.db")
    message_queue = MessageQueue(event_bus)
    queue_file = tmp_path / "todo_queue.json"
    queue = PluginTodoQueue(queue_file, message_queue)

    gap = "test-gap"
    context = "some context"
    goal = "some goal"

    # below threshold: nothing enqueued, no events
    queue.record_failure(gap, context, goal)
    queue.record_failure(gap, context, goal)
    assert list(queue.pending()) == []
    assert list(event_bus.get_events()) == []

    # reaching threshold enqueues item and emits event
    queue.record_failure(gap, context, goal)
    pending = list(queue.pending())
    assert len(pending) == 1
    todo = pending[0]
    assert todo.gap == gap
    assert todo.context == context
    assert todo.goal == goal

    events = [e for e in event_bus.get_events() if e["event_type"] == "plugin_gap"]
    assert len(events) == 1
    assert events[0]["payload"] == {"gap": gap, "context": context, "goal": goal}

    # queue persists after reload
    reloaded = PluginTodoQueue(queue_file)
    reloaded_pending = list(reloaded.pending())
    assert len(reloaded_pending) == 1
    reloaded_todo = reloaded_pending[0]
    assert reloaded_todo.gap == gap
    assert reloaded_todo.context == context
    assert reloaded_todo.goal == goal


def test_plugin_todo_queue_ignores_duplicates(tmp_path: Path) -> None:
    queue_file = tmp_path / "todo_queue.json"
    queue = PluginTodoQueue(queue_file)

    gap = "dup-gap"
    context = "ctx"
    goal = "goal"

    for _ in range(3):
        queue.record_failure(gap, context, goal)

    assert len(list(queue.pending())) == 1

    # Threshold reached again with same data; should not enqueue duplicate
    for _ in range(3):
        queue.record_failure(gap, context, goal)

    assert len(list(queue.pending())) == 1


def test_plugin_todo_queue_respects_max_size(tmp_path: Path) -> None:
    queue_file = tmp_path / "todo_queue.json"
    queue = PluginTodoQueue(queue_file, max_queue_size=1)

    # Enqueue first item
    for _ in range(3):
        queue.record_failure("gap1", "ctx1", "goal1")

    assert len(list(queue.pending())) == 1

    # Second item should be dropped because queue is full
    for _ in range(3):
        queue.record_failure("gap2", "ctx2", "goal2")

    pending = list(queue.pending())
    assert len(pending) == 1
    assert pending[0].gap == "gap1"
    # Counter for gap2 should not reset and remain at threshold
    assert queue._counters["gap2"] == 3
