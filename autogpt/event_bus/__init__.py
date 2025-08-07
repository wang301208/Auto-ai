from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .event_bus import connect as redis_connect
from .event_bus import publish as redis_publish
from .event_bus import subscribe as redis_subscribe
from .message_types import (
    APPROVAL_GRANTED,
    CODE_FIX_PROPOSED,
    DEPLOYMENT_FAILED,
    DIAGNOSIS_COMPLETE,
    HUMAN_APPROVAL_REQUIRED,
    ISSUE_DETECTED,
    ISSUE_RESOLVED,
    SKILL_CREATED,
    SKILL_REQUESTED,
    TESTS_FAILED,
    ApprovalGranted,
    CodeFixProposed,
    DeploymentFailed,
    DiagnosisComplete,
    EventMessage,
    HumanApprovalRequired,
    IssueResolved,
    SkillCreated,
    SkillRequested,
    TestsFailed,
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
                    details=payload_obj.get("details"),
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
                    diff=str(payload_obj.get("diff", "")),
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
            elif et == TESTS_FAILED and isinstance(payload_obj, dict):
                yield TestsFailed(
                    branch_name=str(payload_obj.get("branch_name", "")),
                    test_output=str(payload_obj.get("test_output", "")),
                    summary=str(payload_obj.get("summary", "")),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == DEPLOYMENT_FAILED and isinstance(payload_obj, dict):
                yield DeploymentFailed(
                    branch_name=str(payload_obj.get("branch_name", "")),
                    commit_hash=str(payload_obj.get("commit_hash", "")),
                    summary=str(payload_obj.get("summary", "")),
                    return_code=int(payload_obj.get("return_code", 0)),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == SKILL_CREATED and isinstance(payload_obj, dict):
                yield SkillCreated(
                    skill_name=str(payload_obj.get("skill_name", "")),
                    version=str(payload_obj.get("version", "")),
                    description=payload_obj.get("description"),
                    tags=payload_obj.get("tags"),
                    parameters=payload_obj.get("parameters"),
                    source_agent=source_agent,
                    timestamp=ts,
                )
            elif et == SKILL_REQUESTED and isinstance(payload_obj, dict):
                yield SkillRequested(
                    skill_name=str(payload_obj.get("skill_name", "")),
                    request_id=payload_obj.get("request_id"),
                    parameters=payload_obj.get("parameters"),
                    requester=payload_obj.get("requester"),
                    context=payload_obj.get("context"),
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
    "TestsFailed",
    "ApprovalGranted",
    "IssueResolved",
    "DeploymentFailed",
    "SkillCreated",
    "SkillRequested",
    "ISSUE_DETECTED",
    "DIAGNOSIS_COMPLETE",
    "CODE_FIX_PROPOSED",
    "HUMAN_APPROVAL_REQUIRED",
    "TESTS_FAILED",
    "APPROVAL_GRANTED",
    "ISSUE_RESOLVED",
    "DEPLOYMENT_FAILED",
    "SKILL_CREATED",
    "SKILL_REQUESTED",
    "redis_connect",
    "redis_publish",
    "redis_subscribe",
]
