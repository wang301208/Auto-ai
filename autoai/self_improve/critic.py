"""Critic agent producing diagnostic reports from the improvement DB."""

from __future__ import annotations

import json
from typing import List

from .database import DatabaseManager


class CriticAgent:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def _collect(self) -> dict:
        return {
            "errors": [
                dict(timestamp=t, exception=e, traceback=tb)
                for t, e, tb in self.db.get_errors()
            ],
            "profiles": [
                dict(timestamp=t, name=n, duration=d)
                for t, n, d in self.db.get_profiles()
            ],
            "executions": [
                dict(timestamp=t, description=desc, result=res)
                for t, desc, res in self.db.get_executions()
            ],
        }

    def generate_report(self, output_format: str = "markdown") -> str:
        data = self._collect()
        if output_format == "json":
            return json.dumps(data, indent=2)

        lines: List[str] = ["# Diagnostic Report", ""]
        if data["errors"]:
            lines.append("## Errors")
            for item in data["errors"]:
                lines.append(f"- **{item['timestamp']}** {item['exception']}")
        if data["profiles"]:
            lines.append("\n## Profiles")
            for item in data["profiles"]:
                lines.append(f"- **{item['name']}** {item['duration']:.6f}s")
        if data["executions"]:
            lines.append("\n## Executions")
            for item in data["executions"]:
                lines.append(f"- {item['description']}: {item['result']}")
        return "\n".join(lines)
