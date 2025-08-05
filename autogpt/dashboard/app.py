"""Dashboard web app displaying live events from the MessageQueue."""

from __future__ import annotations

import json
import os
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import Any, Dict, Iterable

from flask import Flask, Response, abort, render_template, request

from autogpt.event_bus import (
    CODE_FIX_PROPOSED,
    DIAGNOSIS_COMPLETE,
    HUMAN_APPROVAL_REQUIRED,
    ISSUE_RESOLVED,
    EventMessage,
    MessageQueue,
)

EVENT_TYPES = [
    "ISSUE_DETECTED",
    DIAGNOSIS_COMPLETE,
    CODE_FIX_PROPOSED,
    HUMAN_APPROVAL_REQUIRED,
    ISSUE_RESOLVED,
]


def create_dashboard_app(
    message_queue: MessageQueue | None = None,
    *,
    auth_token: str | None = None,
) -> Flask:
    """Create a Flask app that serves a live event dashboard.

    Parameters
    ----------
    message_queue:
        Queue to subscribe to. If ``None`` a new queue will be created.
    auth_token:
        Optional token required in query parameter ``token`` or header
        ``X-Dashboard-Token`` to access endpoints.
    """

    app = Flask(__name__, template_folder=str(Path(__file__).with_name("templates")))
    mq = message_queue or MessageQueue()
    subscribers: list[Queue] = []
    issues: Dict[str, Dict[str, Any]] = {}
    lock = Lock()

    def _authorized() -> bool:
        token = auth_token or os.getenv("DASHBOARD_TOKEN")
        if not token:
            return True
        supplied = request.args.get("token") or request.headers.get(
            "X-Dashboard-Token"
        )
        return supplied == token

    def _issue_id(event: EventMessage) -> str:
        payload = event.payload if isinstance(event.payload, dict) else {}
        return (
            str(payload.get("issue_id")
                or payload.get("branch_name")
                or "unknown")
        )

    def _broadcast(event: EventMessage) -> None:
        data = {
            "event_type": event.event_type,
            "payload": event.payload,
            "source_agent": event.source_agent,
            "timestamp": event.timestamp,
            "issue_id": _issue_id(event),
        }
        with lock:
            issues.setdefault(data["issue_id"], {"events": []})["events"].append(data)
            issues[data["issue_id"]].update(data)
        for q in list(subscribers):
            q.put(data)

    for event_type in EVENT_TYPES:
        mq.subscribe(event_type, _broadcast)

    @app.route("/")
    def index() -> str:
        if not _authorized():
            abort(401)
        return render_template("index.html")

    @app.route("/stream")
    def stream() -> Response:
        if not _authorized():
            abort(401)
        q: Queue = Queue()
        subscribers.append(q)

        def gen() -> Iterable[str]:
            try:
                while True:
                    data = q.get()
                    yield f"data: {json.dumps(data)}\n\n"
            except GeneratorExit:
                subscribers.remove(q)

        return Response(gen(), mimetype="text/event-stream")

    @app.route("/issues")
    def get_issues() -> Any:
        if not _authorized():
            abort(401)
        with lock:
            return {k: v for k, v in issues.items()}

    return app


def run_dashboard(
    message_queue: MessageQueue | None = None,
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    auth_token: str | None = None,
) -> None:
    """Run the dashboard web server."""

    app = create_dashboard_app(message_queue, auth_token=auth_token)
    app.run(host=host, port=port)


if __name__ == "__main__":  # pragma: no cover - manual launch
    run_dashboard()

