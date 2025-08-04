from __future__ import annotations

"""Event-driven diagnostic agent for plugin issues."""

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, Iterator

from autogpt.event_bus import EventMessage, MessageQueue

from .archaeologist_dependency import analyze_dependency

ISSUE_DETECTED = "ISSUE_DETECTED"
"""Event type indicating that a plugin issue was detected."""

DIAGNOSIS_COMPLETE = "DIAGNOSIS_COMPLETE"
"""Event type emitted after diagnostic analysis is completed."""


class Archaeologist:
    """Agent that inspects issues reported by plugins and emits diagnostics."""

    def __init__(self, message_queue: MessageQueue) -> None:
        self.message_queue = message_queue
        self.message_queue.subscribe(ISSUE_DETECTED, self._on_issue_detected)

    # ------------------------------------------------------------------
    def _on_issue_detected(self, event: EventMessage) -> None:
        """Handle an ISSUE_DETECTED event."""

        payload = event.payload or {}
        if not isinstance(payload, dict):
            return

        plugin_id = payload.get("plugin")
        error_log = payload.get("error_log")
        metadata = {
            k: v for k, v in payload.items() if k not in {"plugin", "error_log"}
        }

        if error_log and ("file" not in metadata or "line" not in metadata):
            file, line = next(self._parse_log(error_log), (None, None))
            if "file" not in metadata and file:
                metadata["file"] = file
            if "line" not in metadata and line is not None:
                metadata["line"] = line

        analysis = {
            "checkout": self._checkout_commit(metadata.get("commit")),
            "blame": self._git_blame(metadata.get("file"), metadata.get("line")),
            "dependencies": self._review_dependencies(metadata.get("file")),
        }

        diagnosis = {
            "plugin": plugin_id,
            "error_log": error_log,
            "metadata": metadata,
            "analysis": analysis,
            "recommendations": self._recommendations(analysis),
        }

        self.message_queue.publish(
            EventMessage(
                event_type=DIAGNOSIS_COMPLETE,
                payload=diagnosis,
                source_agent="archaeologist",
            )
        )

    # ------------------------------------------------------------------
    def _parse_log(self, log: str) -> Iterator[tuple[str, int]]:
        """Yield ``(file, line)`` pairs parsed from *log*.

        Supports common Python tracebacks and generic ``path:line`` formats
        often used by plugins. Gracefully yields nothing if no matches are
        found so callers can fall back to other metadata.
        """

        patterns = [
            re.compile(r'File "(?P<file>[^"\n]+)", line (?P<line>\d+)'),
            re.compile(r'(?P<file>[\w./\\-]+):(?P<line>\d+)'),
        ]
        for entry in log.splitlines():
            for pattern in patterns:
                match = pattern.search(entry)
                if match:
                    try:
                        yield match.group("file"), int(match.group("line"))
                    except (ValueError, AttributeError):
                        continue

    # ------------------------------------------------------------------
    def _checkout_commit(self, commit: str | None) -> str | None:
        """Checkout the specified commit and return git output."""

        if not commit:
            return None

        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        result = subprocess.run(
            ["git", "checkout", commit], capture_output=True, text=True
        )
        subprocess.run(["git", "checkout", current], capture_output=True, text=True)
        return result.stdout + result.stderr

    def _git_blame(self, file: str | None, line: int | None) -> str | None:
        """Run git blame on the specified file and line."""

        if not file:
            return None
        cmd = ["git", "blame"]
        if line is not None:
            cmd += ["-L", f"{line},{line}"]
        cmd.append(file)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()

    def _review_dependencies(self, file: str | None) -> list[dict[str, Any]]:
        """Analyze imported modules from ``file`` for compatibility issues."""

        if not file or not Path(file).exists():
            return []
        try:
            source_path = Path(file)
            tree = ast.parse(source_path.read_text())
        except Exception:
            return []

        deps: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                deps.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                deps.append(node.module.split(".")[0])

        analyses: list[dict[str, Any]] = []
        for dep in sorted(set(deps)):
            analyses.append(analyze_dependency(dep, source_path))
        return analyses

    def _recommendations(self, analysis: dict[str, Any]) -> str:
        """Create a simple recommendation string from analysis data."""

        recs: list[str] = []
        if analysis.get("blame"):
            recs.append("Review the blamed lines for potential fixes.")
        deps = analysis.get("dependencies") or []
        if deps:
            problematic = [d["dependency"] for d in deps if d.get("findings")]
            if problematic:
                recs.append(
                    "Investigate compatibility issues in: " + ", ".join(problematic)
                )
            else:
                recs.append(
                    "Check versions of dependencies: "
                    + ", ".join(d["dependency"] for d in deps)
                )
        return " ".join(recs) if recs else "No recommendations."
