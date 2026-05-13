"""Break report generator for post-hoc human audit.

Generates human-readable TUI reports from break log entries.
Used by `agpt breaks` CLI command for post-hoc boundary break review.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .break_log import BreakLog, BreakRecord


class BreakReport:
    """Generate human-readable break decision reports for TUI display."""

    def __init__(self, break_log: BreakLog | None = None) -> None:
        self.break_log = break_log or BreakLog()

    def format_record(self, rec: BreakRecord) -> str:
        lines = [
            f"  {'='*60}",
            f"  Break ID:    {rec.record_id}",
            f"  Time:        {rec.timestamp}",
            f"  Agent:       {rec.agent_id}",
            f"  Constraint:  {rec.constraint_kind}",
            f"  Old Value:   {rec.old_value}",
            f"  New Value:   {rec.new_value}",
            f"  Decision:    {rec.decision}",
            f"  ---",
            f"  Goal Value:  {rec.goal_value:.4f}",
            f"  Break Risk:  {rec.break_risk:.4f}",
            f"  Risk Mult:   {rec.risk_multiplier:.2f}",
        ]
        if rec.compensation:
            lines.append(f"  --- Compensation ---")
            for k, v in rec.compensation.items():
                lines.append(f"    {k}: {v}")
        if rec.alternative_paths:
            lines.append(f"  --- Alternative Paths Considered ---")
            for p in rec.alternative_paths:
                lines.append(f"    - {p}")
        lines.append(f"  {'='*60}")
        return "\n".join(lines)

    def format_summary(self, stats: dict[str, Any]) -> str:
        lines = [
            "Break Log Summary",
            f"  Total breaks: {stats['total']}",
            f"  By constraint kind:",
        ]
        for kind, count in stats.get("by_constraint_kind", {}).items():
            lines.append(f"    {kind}: {count}")
        lines.append(f"  By decision:")
        for decision, count in stats.get("by_decision", {}).items():
            lines.append(f"    {decision}: {count}")
        return "\n".join(lines)

    def generate(
        self,
        constraint_kind: str | None = None,
        agent_id: str | None = None,
        since: str | None = None,
        limit: int = 20,
        summary_only: bool = False,
    ) -> str:
        if summary_only:
            return self.format_summary(self.break_log.stats())

        records = self.break_log.query(
            constraint_kind=constraint_kind,
            agent_id=agent_id,
            since=since,
            limit=limit,
        )
        if not records:
            return "No boundary breaks found."

        parts: list[str] = []
        parts.append(f"Boundary Break Report ({len(records)} records)")
        parts.append("")
        for rec in records:
            parts.append(self.format_record(rec))

        parts.append("")
        parts.append(self.format_summary(self.break_log.stats()))
        return "\n".join(parts)


__all__ = ["BreakReport"]
