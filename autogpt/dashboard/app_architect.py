from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request

from autogpt.event_bus import EventBus, MessageQueue
from autogpt.event_bus.message_types import HUMAN_ARCHITECT_APPROVAL_REQUIRED, EventMessage


def create_app(events_db: str | Path = "events.db") -> Flask:
    app = Flask(__name__)
    bus = EventBus(events_db)
    mq = MessageQueue(bus)

    pending: list[dict] = []

    def on_event(event: EventMessage) -> None:
        # Store minimal info for UI listing
        try:
            payload = event.payload if isinstance(event.payload, dict) else {}
        except Exception:
            payload = {}
        pending.append(
            {
                "timestamp": event.timestamp,
                "source": event.source_agent,
                "proposal_branch_name": payload.get("proposal_branch_name"),
                "proposal_branch_url": payload.get("proposal_branch_url"),
                "rationale": payload.get("rationale"),
                "changes_summary": payload.get("changes_summary"),
            }
        )

    mq.subscribe(HUMAN_ARCHITECT_APPROVAL_REQUIRED, on_event)

    @app.get("/pending")
    def list_pending() -> tuple[str, int]:
        return jsonify(pending), 200

    @app.post("/approve")
    def approve() -> tuple[str, int]:
        data = request.get_json(silent=True) or {}
        branch = data.get("branch")
        # In a full implementation, this would merge the PR. Here we just acknowledge.
        return jsonify({"status": "approved", "branch": branch}), 200

    @app.post("/reject")
    def reject() -> tuple[str, int]:
        data = request.get_json(silent=True) or {}
        branch = data.get("branch")
        reason = data.get("reason")
        return jsonify({"status": "rejected", "branch": branch, "reason": reason}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5055)


