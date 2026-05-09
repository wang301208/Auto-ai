#!/usr/bin/env python3
"""Smoke tests for the Dual Ring AI system."""

from __future__ import annotations

from datetime import UTC, datetime

from dual_ring_ai.core.event_bus import EventBus, EventTypes
from dual_ring_ai.main_controller import MainController


def test_event_bus_records_published_events_locally():
    event_bus = EventBus()
    event_bus.connect()

    event_bus.publish(
        EventTypes.SYSTEM_STARTED,
        {"test": True, "timestamp": datetime.now(UTC).isoformat()},
        "test_script",
    )

    events = event_bus.list_events(EventTypes.SYSTEM_STARTED)
    assert events[-1].payload["test"] is True
    assert events[-1].source_agent == "test_script"


def test_librarian_initializes_with_fallback_storage():
    from dual_ring_ai.core.librarian import Librarian

    librarian = Librarian()

    assert isinstance(librarian.skills, dict)
    assert isinstance(librarian.plugins, dict)
    assert hasattr(librarian, "vector_db")


def test_main_controller_initializes_agents():
    controller = MainController()

    assert len(controller.agents) > 0
    assert "task_planner" in controller.agents
    assert "execution_engine" in controller.agents


def test_task_execution_returns_none_until_runtime_started():
    controller = MainController()

    assert controller.execute_task("create a hello world skill") is None


def test_dashboard_collects_system_started_event():
    from dual_ring_ai.dashboard.monitor import Dashboard, DEFAULT_DASHBOARD_CONFIG

    event_bus = EventBus()
    event_bus.connect()
    dashboard = Dashboard(event_bus, DEFAULT_DASHBOARD_CONFIG)

    event_bus.publish(
        EventTypes.SYSTEM_STARTED,
        {"test": True, "timestamp": datetime.now(UTC).isoformat()},
        "test_script",
    )

    stats = dashboard.get_system_stats()
    assert stats["total_events"] == 1
    assert stats["events_by_type"][EventTypes.SYSTEM_STARTED] == 1
