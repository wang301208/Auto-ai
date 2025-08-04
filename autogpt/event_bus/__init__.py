from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .message_types import EventMessage


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
            yield EventMessage(
                event_type=et,
                payload=payload_obj,
                source_agent=source_agent,
                timestamp=ts,
            )


from .message_queue import MessageQueue

__all__ = ["EventBus", "MessageQueue", "EventMessage"]
