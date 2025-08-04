from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable


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
                payload TEXT
            )
            """
        )
        self.connection.commit()

    def emit(self, event_type: str, payload: dict | str | None = None) -> None:
        """Record a new event."""
        if payload is None:
            payload = {}
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO events(timestamp, event_type, payload) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), event_type, payload),
        )
        self.connection.commit()

    def get_events(self, limit: int | None = None) -> Iterable[dict]:
        """Yield events from the bus."""
        cur = self.connection.cursor()
        query = "SELECT timestamp, event_type, payload FROM events ORDER BY id"
        rows = cur.execute(
            query + (" LIMIT ?" if limit is not None else ""),
            [limit] if limit is not None else [],
        )
        for ts, et, payload in rows:
            yield {
                "timestamp": ts,
                "event_type": et,
                "payload": json.loads(payload),
            }

from .message_queue import EventMessage, MessageQueue


__all__ = ["EventBus", "MessageQueue", "EventMessage"]
