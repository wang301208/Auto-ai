"""Dashboard web app displaying live events from the MessageQueue."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import Any, Dict, Iterable, cast

from flask import Flask, Response, abort, render_template, request

from autogpt.event_bus import (
    CODE_FIX_PROPOSED,
    DIAGNOSIS_COMPLETE,
    HUMAN_APPROVAL_REQUIRED,
    ISSUE_DETECTED,
    ISSUE_RESOLVED,
    TICKET_RECEIVED,
    EventMessage,
    MessageQueue,
)

EVENT_TYPES = [
    ISSUE_DETECTED,
    TICKET_RECEIVED,
    DIAGNOSIS_COMPLETE,
    CODE_FIX_PROPOSED,
    HUMAN_APPROVAL_REQUIRED,
    ISSUE_RESOLVED,
]

EVENT_STAGE_MAPPING = {
    ISSUE_DETECTED: "detected",
    TICKET_RECEIVED: "detected",
    DIAGNOSIS_COMPLETE: "diagnosed",
    CODE_FIX_PROPOSED: "fix_proposed",
    HUMAN_APPROVAL_REQUIRED: "awaiting_approval",
    ISSUE_RESOLVED: "resolved",
}


def init_db(db_path: str | os.PathLike | None = None) -> sqlite3.Connection:
    """Initialise and return a SQLite connection."""

    db_path = Path(
        db_path
        or os.getenv("DASHBOARD_DB_PATH")
        or Path(__file__).with_name("dashboard.db")
    )
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            issue_id TEXT,
            event_type TEXT,
            payload TEXT,
            source_agent TEXT,
            timestamp TEXT
        )
        """
    )
    conn.commit()
    return conn


def create_dashboard_app(
    message_queue: MessageQueue | None = None,
    *,
    auth_token: str | None = None,
    db_path: str | os.PathLike | None = None,
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
    db = init_db(db_path)

    def _compute_stage(events: list[Dict[str, Any]]) -> str:
        event_types = {e["event_type"] for e in events}
        for et in reversed(EVENT_TYPES):
            if et in event_types:
                return EVENT_STAGE_MAPPING[et]
        return "unknown"

    def _load_events() -> None:
        cur = db.execute(
            "SELECT issue_id, event_type, payload, source_agent, timestamp FROM events ORDER BY timestamp"
        )
        for row in cur.fetchall():
            data = {
                "event_type": row[1],
                "payload": json.loads(row[2]) if row[2] else {},
                "source_agent": row[3],
                "timestamp": row[4],
                "issue_id": row[0],
            }
            issue = issues.setdefault(data["issue_id"], {"events": []})
            issue["events"].append(data)
            issue.update(data)
            issue["stage"] = _compute_stage(issue["events"])

    _load_events()

    def _authorized() -> bool:
        token = auth_token or os.getenv("DASHBOARD_TOKEN")
        if not token:
            return True
        supplied = request.args.get("token") or request.headers.get("X-Dashboard-Token")
        return supplied == token

    def _issue_id(event: EventMessage) -> str:
        payload = event.payload if isinstance(event.payload, dict) else {}
        return str(payload.get("issue_id") or payload.get("branch_name") or "unknown")

    def _broadcast(event: EventMessage) -> None:
        data: Dict[str, Any] = {
            "event_type": event.event_type,
            "payload": event.payload,
            "source_agent": event.source_agent,
            "timestamp": event.timestamp,
            "issue_id": _issue_id(event),
        }
        with lock:
            issue = issues.setdefault(cast(str, data["issue_id"]), {"events": []})
            issue["events"].append(data)
            issue.update(data)
            issue["stage"] = _compute_stage(issue["events"])
            db.execute(
                "INSERT INTO events(issue_id, event_type, payload, source_agent, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    data["issue_id"],
                    data["event_type"],
                    json.dumps(data["payload"]),
                    data["source_agent"],
                    data["timestamp"],
                ),
            )
            db.commit()
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
    db_path: str | os.PathLike | None = None,
) -> None:
    """Run the dashboard web server."""

    app = create_dashboard_app(message_queue, auth_token=auth_token, db_path=db_path)
    app.run(host=host, port=port)


if __name__ == "__main__":  # pragma: no cover - manual launch
    run_dashboard()
