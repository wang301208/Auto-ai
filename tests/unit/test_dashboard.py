from __future__ import annotations

import json

from autogpt.dashboard import create_dashboard_app
from autogpt.event_bus import (
    DIAGNOSIS_COMPLETE,
    ISSUE_RESOLVED,
    EventMessage,
    MessageQueue,
)


def test_dashboard_tracks_events() -> None:
    mq = MessageQueue()
    app = create_dashboard_app(mq)
    client = app.test_client()

    event = EventMessage(
        event_type="ISSUE_DETECTED",
        payload={"issue_id": "42", "issue_type": "bug"},
        source_agent="tester",
    )
    mq.publish(event)

    resp = client.get("/issues")
    data = resp.get_json()
    assert data["42"]["event_type"] == "ISSUE_DETECTED"
    assert data["42"]["source_agent"] == "tester"
    assert data["42"]["timestamp"] == event.timestamp


def test_auth_token_required() -> None:
    mq = MessageQueue()
    app = create_dashboard_app(mq, auth_token="secret")
    client = app.test_client()

    assert client.get("/").status_code == 401
    assert client.get("/?token=secret").status_code == 200


def test_dashboard_streams_events_and_updates_state() -> None:
    mq = MessageQueue()
    app = create_dashboard_app(mq)

    with app.test_request_context("/stream"):
        resp = app.view_functions["stream"]()
        gen = resp.response

        events = [
            EventMessage(
                event_type="ISSUE_DETECTED",
                payload={"issue_id": "1", "issue_type": "bug"},
                source_agent="tester",
            ),
            EventMessage(
                event_type=DIAGNOSIS_COMPLETE,
                payload={"issue_id": "1"},
                source_agent="diag",
            ),
            EventMessage(
                event_type=ISSUE_RESOLVED,
                payload={"issue_id": "1"},
                source_agent="tester",
            ),
        ]

        for event in events:
            mq.publish(event)
            data = next(gen)
            payload = json.loads(data.split("data: ")[1])
            assert payload["event_type"] == event.event_type

    client = app.test_client()
    resp = client.get("/issues")
    issue = resp.get_json()["1"]
    assert issue["event_type"] == ISSUE_RESOLVED
    assert len(issue["events"]) == len(events)


def test_dashboard_handles_missing_issue_id() -> None:
    mq = MessageQueue()
    app = create_dashboard_app(mq)
    client = app.test_client()

    event = EventMessage(
        event_type="ISSUE_DETECTED",
        payload={"issue_type": "bug"},
        source_agent="tester",
    )
    mq.publish(event)

    resp = client.get("/issues")
    data = resp.get_json()
    assert "unknown" in data


def test_stream_removes_disconnected_clients() -> None:
    mq = MessageQueue()
    app = create_dashboard_app(mq)
    stream_func = app.view_functions["stream"]
    subscribers = next(
        cell.cell_contents
        for cell in stream_func.__closure__
        if isinstance(cell.cell_contents, list)
    )

    assert len(subscribers) == 0
    with app.test_request_context("/stream"):
        resp = stream_func()
        gen = resp.response
        assert len(subscribers) == 1
        mq.publish(
            EventMessage(
                event_type="ISSUE_DETECTED",
                payload={"issue_type": "bug"},
                source_agent="tester",
            )
        )
        next(gen)
        gen.close()
        assert len(subscribers) == 0
