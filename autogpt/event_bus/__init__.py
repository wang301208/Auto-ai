from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .message_types import (
    APPROVAL_GRANTED,
    CODE_FIX_PROPOSED,
    DIAGNOSIS_COMPLETE,
    HUMAN_APPROVAL_REQUIRED,
    ISSUE_RESOLVED,
    ApprovalGranted,
    CodeFixProposed,
    DiagnosisComplete,
    EventMessage,
    HumanApprovalRequired,
    IssueResolved,
)


class EventBus:
    """Simple event bus storing events in a SQLite table."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                payload TEXT,
                source_agent TEXT
            )
            """
        )
        self.connection.commit()

    def emit(self, event: EventMessage) -> None:
        """Record a new event."""
        payload = event.payload
        if payload is None:
            payload = json.dumps({})
        elif not isinstance(payload, str):
            payload = json.dumps(payload)
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO events(timestamp, event_type, payload, source_agent) VALUES (?, ?, ?, ?)",
            (event.timestamp, event.event_type, payload, event.source_agent),
        )
        self.connection.commit()

    def get_events(self, limit: int | None = None) -> Iterable[EventMessage]:
        """Yield events from the bus."""
        cur = self.connection.cursor()
        query = "SELECT timestamp, event_type, payload, source_agent FROM events ORDER BY id"
        rows = cur.execute(
            query + (" LIMIT ?" if limit is not None else ""),
            [limit] if limit is not None else [],
        )
        for ts, et, payload, source_agent in rows:
            try:
                payload_obj = json.loads(payload)
            except Exception:
                payload_obj = payload

            if et == DIAGNOSIS_COMPLETE and isinstance(payload_obj, dict):
                yield DiagnosisComplete(
                    summary=str(payload_obj.get("summary", "")),
                    actionable_recommendations=str(
                        payload_obj.get("actionable_recommendations", "")
                    ),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == CODE_FIX_PROPOSED and isinstance(payload_obj, dict):
                yield CodeFixProposed(
                    branch_name=str(payload_obj.get("branch_name", "")),
                    commit_hash=str(payload_obj.get("commit_hash", "")),
                    summary=str(payload_obj.get("summary", "")),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == HUMAN_APPROVAL_REQUIRED and isinstance(payload_obj, dict):
                yield HumanApprovalRequired(
                    branch_name=str(payload_obj.get("branch_name", "")),
                    test_output=str(payload_obj.get("test_output", "")),
                    summary=str(payload_obj.get("summary", "")),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == APPROVAL_GRANTED and isinstance(payload_obj, dict):
                yield ApprovalGranted(
                    branch_name=str(payload_obj.get("branch_name", "")),
                    commit_hash=str(payload_obj.get("commit_hash", "")),
                    summary=str(payload_obj.get("summary", "")),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == ISSUE_RESOLVED and isinstance(payload_obj, dict):
                yield IssueResolved(
                    branch_name=str(payload_obj.get("branch_name", "")),
                    commit_hash=str(payload_obj.get("commit_hash", "")),
                    summary=str(payload_obj.get("summary", "")),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            else:
                yield EventMessage(
                    event_type=et,
                    payload=payload_obj,
                    source_agent=source_agent,
                    timestamp=ts,
                )


from .message_queue import MessageQueue

__all__ = [
    "EventBus",
    "MessageQueue",
    "EventMessage",
    "DiagnosisComplete",
    "CodeFixProposed",
    "HumanApprovalRequired",
    "ApprovalGranted",
    "IssueResolved",
    "DIAGNOSIS_COMPLETE",
    "CODE_FIX_PROPOSED",
    "HUMAN_APPROVAL_REQUIRED",
    "APPROVAL_GRANTED",
    "ISSUE_RESOLVED",
]
