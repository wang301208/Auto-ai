import threading
import time
from pathlib import Path

import pytest

from autogpt.agents.sentry import SentryAgent
from autogpt.event_bus import ISSUE_DETECTED, EventMessage, MessageQueue


class DummyResponse:
    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict:
        return self._json


def test_sentry_agent_log_monitoring(tmp_path: Path) -> None:
    mq = MessageQueue()
    received: list[EventMessage] = []
    mq.subscribe(ISSUE_DETECTED, lambda m: received.append(m))

    logs_dir = tmp_path / "plugins" / "plug" / "logs"
    logs_dir.mkdir(parents=True)
    log_file = logs_dir / "run.log"
    log_file.write_text("")

    stop = threading.Event()
    agent = SentryAgent(
        mq,
        plugin_log_dirs={"plug": logs_dir},
        poll_interval=0.1,
        stop_event=stop,
    )
    thread = threading.Thread(target=agent.run, daemon=True)
    thread.start()

    log_file.write_text("ERROR something\n")
    time.sleep(0.5)
    stop.set()
    thread.join(timeout=1)

    assert any(e.payload.get("issue_type") == "bug" for e in received)


def test_sentry_agent_healthcheck_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mq = MessageQueue()
    received: list[EventMessage] = []
    mq.subscribe(ISSUE_DETECTED, lambda m: received.append(m))

    agent = SentryAgent(mq, plugin_endpoints={"plug": "http://example"})

    def fake_get(url: str, timeout: int = 5) -> DummyResponse:
        return DummyResponse(500)

    monkeypatch.setattr("requests.get", fake_get)
    agent._poll_health()

    assert any(e.payload.get("issue_type") == "bug" for e in received)


def test_sentry_agent_dependency_update(monkeypatch: pytest.MonkeyPatch) -> None:
    mq = MessageQueue()
    received: list[EventMessage] = []
    mq.subscribe(ISSUE_DETECTED, lambda m: received.append(m))

    agent = SentryAgent(mq, dependencies={"plug": {"pkg": "1.0"}})

    def fake_get(url: str, timeout: int = 5) -> DummyResponse:
        return DummyResponse(200, {"info": {"version": "2.0"}})

    monkeypatch.setattr("requests.get", fake_get)
    agent._check_dependencies()

    assert any(e.payload.get("issue_type") == "dependency_update" for e in received)
