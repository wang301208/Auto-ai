"""SQLite storage for self improvement data."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

from autogpt.event_bus import EventMessage, MessageQueue


class DatabaseManager:
    """Small wrapper around sqlite3 for storing improvement data."""

    def __init__(
        self, db_path: Path | str, message_queue: MessageQueue | None = None
    ) -> None:
        self.db_path = Path(db_path)
        self.message_queue = message_queue
        self.connection = sqlite3.connect(self.db_path)
        self.init_db()

    def init_db(self) -> None:
        cur = self.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                exception TEXT,
                traceback TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                name TEXT,
                duration REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                description TEXT,
                result TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles_detailed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                name TEXT,
                function TEXT,
                ncalls INTEGER,
                cumtime REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patch_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                success INTEGER
            )
            """
        )
        self.connection.commit()

    def log_error(self, exception: str, traceback_str: str) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO errors(timestamp, exception, traceback) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), exception, traceback_str),
        )
        self.connection.commit()
        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="error",
                    payload={"exception": exception, "traceback": traceback_str},
                    source_agent="database_manager",
                )
            )

    def log_profile(self, name: str, duration: float) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO profiles(timestamp, name, duration) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), name, duration),
        )
        self.connection.commit()
        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="profile",
                    payload={"name": name, "duration": duration},
                    source_agent="database_manager",
                )
            )

    def log_execution(self, description: str, result: str) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO executions(timestamp, description, result) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), description, result),
        )
        self.connection.commit()
        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="execution",
                    payload={"description": description, "result": result},
                    source_agent="database_manager",
                )
            )

    def log_profile_detail(
        self, name: str, function: str, ncalls: int, cumtime: float
    ) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO profiles_detailed(timestamp, name, function, ncalls, cumtime) VALUES (?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), name, function, ncalls, cumtime),
        )
        self.connection.commit()
        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="profile_detail",
                    payload={
                        "name": name,
                        "function": function,
                        "ncalls": ncalls,
                        "cumtime": cumtime,
                    },
                    source_agent="database_manager",
                )
            )

    def get_errors(self) -> Iterable[Tuple]:
        cur = self.connection.cursor()
        return cur.execute("SELECT timestamp, exception, traceback FROM errors")

    def get_profiles(self) -> Iterable[Tuple]:
        cur = self.connection.cursor()
        return cur.execute("SELECT timestamp, name, duration FROM profiles")

    def get_profile_details(self) -> Iterable[Tuple]:
        cur = self.connection.cursor()
        return cur.execute(
            "SELECT timestamp, name, function, ncalls, cumtime FROM profiles_detailed"
        )

    def get_hotspots(self, threshold: float) -> Iterable[Tuple]:
        cur = self.connection.cursor()
        return cur.execute(
            "SELECT function, SUM(cumtime) as total FROM profiles_detailed GROUP BY function HAVING total > ?",
            (threshold,),
        )

    def get_executions(self) -> Iterable[Tuple]:
        cur = self.connection.cursor()
        return cur.execute("SELECT timestamp, description, result FROM executions")

    def log_patch_attempt(self, success: bool) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "INSERT INTO patch_attempts(timestamp, success) VALUES (?, ?)",
            (datetime.utcnow().isoformat(), int(success)),
        )
        self.connection.commit()
        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="patch_attempt",
                    payload={"success": bool(success)},
                    source_agent="database_manager",
                )
            )

    def get_last_patch_attempts(self, count: int) -> Iterable[Tuple]:
        cur = self.connection.cursor()
        return cur.execute(
            "SELECT success FROM patch_attempts ORDER BY id DESC LIMIT ?",
            (count,),
        )
