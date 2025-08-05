from __future__ import annotations

from autogpt.dashboard import create_dashboard_app
from autogpt.event_bus import EventMessage, MessageQueue


def test_dashboard_tracks_events() -> None:
    mq = MessageQueue()
    app = create_dashboard_app(mq)
    client = app.test_client()

    event = EventMessage(
        event_type="ISSUE_DETECTED",
        payload={"issue_id": "42"},
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
