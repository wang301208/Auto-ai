"""Break log: immutable record of all boundary break decisions.

Replaces the approval workflow for the autonomous boundary management model.
Every boundary break is recorded with full decision context for post-hoc audit.
Human views break records via `agpt breaks` — no real-time approval needed.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BreakRecord:
    """A single boundary break decision record."""

    record_id: str = ""
    timestamp: str = ""
    agent_id: str = ""
    constraint_kind: str = ""
    old_value: Any = None
    new_value: Any = None
    goal_value: float = 0.0
    break_risk: float = 0.0
    risk_multiplier: float = 1.0
    decision: str = ""
    compensation: dict[str, Any] = field(default_factory=dict)
    alternative_paths: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.record_id:
            self.record_id = f"break_{self.timestamp.replace(':', '').replace('.', '_')}_{id(self) & 0xFFFF}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "constraint_kind": self.constraint_kind,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "goal_value": self.goal_value,
            "break_risk": self.break_risk,
            "risk_multiplier": self.risk_multiplier,
            "decision": self.decision,
            "compensation": self.compensation,
            "alternative_paths": self.alternative_paths,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BreakRecord:
        return cls(
            record_id=data.get("record_id", ""),
            timestamp=data.get("timestamp", ""),
            agent_id=data.get("agent_id", ""),
            constraint_kind=data.get("constraint_kind", ""),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            goal_value=data.get("goal_value", 0.0),
            break_risk=data.get("break_risk", 0.0),
            risk_multiplier=data.get("risk_multiplier", 1.0),
            decision=data.get("decision", ""),
            compensation=data.get("compensation", {}),
            alternative_paths=data.get("alternative_paths", []),
        )


class BreakLog:
    """Append-only break decision log backed by JSONL file.

    Thread-safe. Used by BoundaryManager to record all break decisions.
    Human inspects via `agpt breaks [--session ID] [--limit N]`.
    """

    def __init__(self, log_path: str | Path = "governance/break_log.jsonl") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        constraint_kind: str,
        old_value: Any,
        new_value: Any,
        goal_value: float = 0.0,
        break_risk: float = 0.0,
        risk_multiplier: float = 1.0,
        decision: str = "",
        compensation: dict[str, Any] | None = None,
        alternative_paths: list[str] | None = None,
        agent_id: str = "",
    ) -> BreakRecord:
        rec = BreakRecord(
            constraint_kind=constraint_kind,
            old_value=old_value,
            new_value=new_value,
            goal_value=goal_value,
            break_risk=break_risk,
            risk_multiplier=risk_multiplier,
            decision=decision,
            compensation=compensation or {},
            alternative_paths=alternative_paths or [],
            agent_id=agent_id,
        )
        self._append(rec)
        return rec

    def query(
        self,
        constraint_kind: str | None = None,
        agent_id: str | None = None,
        decision: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[BreakRecord]:
        results: list[BreakRecord] = []
        if not self.log_path.exists():
            return results
        with self._lock:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                rec = BreakRecord.from_dict(data)
            except Exception:
                continue
            if constraint_kind is not None and rec.constraint_kind != constraint_kind:
                continue
            if agent_id is not None and rec.agent_id != agent_id:
                continue
            if decision is not None and rec.decision != decision:
                continue
            if since is not None and rec.timestamp < since:
                continue
            results.append(rec)
            if len(results) >= limit:
                break
        return list(reversed(results))

    def stats(self) -> dict[str, Any]:
        records = self.query(limit=10000)
        by_kind: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        for r in records:
            by_kind[r.constraint_kind] = by_kind.get(r.constraint_kind, 0) + 1
            by_decision[r.decision] = by_decision.get(r.decision, 0) + 1
        return {
            "total": len(records),
            "by_constraint_kind": by_kind,
            "by_decision": by_decision,
        }

    def _append(self, rec: BreakRecord) -> None:
        line = json.dumps(rec.to_dict(), ensure_ascii=False)
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


__all__ = [
    "BreakLog",
    "BreakRecord",
]
