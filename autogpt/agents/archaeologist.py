"""Event-driven diagnostic agent for plugin issues."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, Iterator, cast

from autogpt.event_bus import (
    ISSUE_DETECTED,
    TICKET_RECEIVED,
    DiagnosisComplete,
    EventMessage,
    MessageQueue,
)
from autogpt.app.i18n import _
from autogpt.event_bus.message_types import DiagnosisDetails
from autogpt.skills.librarian import LibrarianAgent
from autogpt.logs import logger

from .archaeologist_dependency import analyze_dependency


class Archaeologist:
    """Agent that inspects issues reported by plugins and emits diagnostics."""

    def __init__(
        self,
        message_queue: MessageQueue,
        librarian: LibrarianAgent | None = None,
    ) -> None:
        """Create a new instance of :class:`Archaeologist`.

        Args:
            message_queue: The message queue used for communication with other
                agents.
            librarian: Optional ``LibrarianAgent``. If not provided, a default
                ``LibrarianAgent`` will be created.
        """
        self.message_queue = message_queue
        self.message_queue.subscribe(ISSUE_DETECTED, self._on_ticket_received)
        self.message_queue.subscribe(TICKET_RECEIVED, self._on_ticket_received)
        self.librarian = librarian or LibrarianAgent()

    # ------------------------------------------------------------------
    def _on_ticket_received(self, event: EventMessage) -> None:
        """Handle an ISSUE_DETECTED or TICKET_RECEIVED event."""

        payload = event.payload or {}
        if not isinstance(payload, dict):
            return

        plugin_id = payload.get("plugin")
        error_log = payload.get("error_log")
        description = payload.get("description")
        issue_type = payload.get("issue_type", "bug")
        metadata = {
            k: v
            for k, v in payload.items()
            if k not in {"plugin", "error_log", "issue_type", "description"}
        }

        details: dict[str, Any]
        if issue_type == "bug":
            if error_log and ("file" not in metadata or "line" not in metadata):
                file, line = next(self._parse_log(error_log), (None, None))
                if "file" not in metadata and file:
                    metadata["file"] = file
                if "line" not in metadata and line is not None:
                    metadata["line"] = line

            analysis: dict[str, Any] = {
                "checkout": self._checkout_commit(metadata.get("commit")),
                "blame": self._git_blame(metadata.get("file"), metadata.get("line")),
                "dependencies": self._review_dependencies(
                    metadata.get("file"), metadata.get("dependencies")
                ),
            }

            summary_parts = [
                f"Diagnostics for plugin {plugin_id}" if plugin_id else "Diagnostics"
            ]
            if metadata.get("file"):
                location = metadata["file"]
                if metadata.get("line") is not None:
                    location += f":{metadata['line']}"
                summary_parts.append(f"at {location}")
            summary = " ".join(summary_parts)

            blame_info = self._parse_blame_output(analysis.get("blame"))
            context: list[dict[str, Any]] = []
            if metadata.get("file") and metadata.get("line") is not None:
                context = self._source_context(metadata["file"], metadata["line"])

            details = {
                "metadata": metadata,
                "error_log": error_log,
                "blame": blame_info,
                "context": context,
                "dependencies": analysis.get("dependencies"),
            }
            if description:
                details["description"] = description

        elif issue_type == "dependency_update":
            dep_info = metadata.get("dependencies")
            if not dep_info and error_log:
                parts = error_log.split()
                if parts:
                    new_version = parts[1] if len(parts) > 1 else None
                    dep_info = {parts[0]: {"new_version": new_version}}

            analysis = {
                "dependencies": self._review_dependencies(
                    metadata.get("file"), dep_info
                )
            }
            summary = (
                f"Dependency update for plugin {plugin_id}"
                if plugin_id
                else "Dependency update"
            )
            details = {
                "metadata": metadata,
                "error_log": error_log,
                "dependencies": analysis.get("dependencies"),
            }
            if description:
                details["description"] = description
        else:
            return

        if description:
            query = description
        else:
            query_parts: list[str] = []
            if issue_type:
                query_parts.append(issue_type.replace("_", " "))
            if plugin_id:
                query_parts.append(f"plugin {plugin_id}")
            if error_log:
                query_parts.append(str(error_log))
            for k, v in metadata.items():
                if isinstance(v, (str, int)):
                    query_parts.append(f"{k} {v}")
            query = " ".join(query_parts)

        try:
            skills = self.librarian.find_skill(query)
        except Exception as err:  # noqa: BLE001
            logger.error(f"Error searching for skill: {err}")
            skills = []
        if skills:
            skill = skills[0]
            call_name = f"skill_{skill['skill_name']}_v{skill['version']}"
            params = skill.get("parameters", {})
            param_list = ", ".join(params.keys()) if params else "no parameters"
            skill_rec = _(
                "Issue can be solved by invoking {call_name} with parameters: {param_list}."
            ).format(call_name=call_name, param_list=param_list)
            details["recommended_skill"] = {
                "name": skill["skill_name"],
                "version": skill["version"],
                "parameters": params,
            }
        else:
            skill_rec = _("New skill development recommended.")
            details["recommended_skill"] = None

        base_rec = self._recommendations(analysis)
        recs = []
        if base_rec and base_rec != "No recommendations.":
            recs.append(base_rec)
        recs.append(skill_rec)
        recommendations = " ".join(recs)
        details["skill_search"] = skills

        self.message_queue.publish(
            DiagnosisComplete(
                summary=summary,
                actionable_recommendations=recommendations,
                details=cast(DiagnosisDetails, details),
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
            re.compile(r"(?P<file>[\w./\\-]+):(?P<line>\d+)"),
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

    def _parse_blame_output(self, blame: str | None) -> dict[str, Any] | None:
        """Parse commit hash and author from ``git blame`` output."""

        if not blame:
            return None
        first_line = blame.splitlines()[0]
        match = re.match(
            r"^(?P<commit>\S+)\s+\((?P<author>.+?)\s+\d{4}-\d{2}-\d{2}",
            first_line,
        )
        if match:
            return {
                "commit": match.group("commit"),
                "author": match.group("author").strip(),
                "text": blame,
            }
        return {"text": blame}

    def _source_context(
        self, file: str, line: int, span: int = 2
    ) -> list[dict[str, Any]]:
        """Return source lines surrounding ``line`` from ``file``."""

        try:
            lines = Path(file).read_text().splitlines()
        except Exception:
            return []
        start = max(line - span - 1, 0)
        end = min(line + span, len(lines))
        return [{"line": i + 1, "content": lines[i]} for i in range(start, end)]

    def _review_dependencies(
        self, file: str | None, dep_info: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Analyze imported modules from ``file`` for compatibility issues."""

        source_path = Path(file) if file else Path("nonexistent.py")
        tree = None
        if source_path.exists():
            try:
                tree = ast.parse(source_path.read_text())
            except Exception:
                tree = None

        deps: list[str] = []
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    deps.extend(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    deps.append(node.module.split(".")[0])

        dep_info = dep_info or {}
        names = sorted(set(deps) | set(dep_info.keys()))
        analyses: list[dict[str, Any]] = []
        for dep in names:
            info = dep_info.get(dep)
            new_version = None
            if isinstance(info, dict):
                new_version = info.get("new_version")
            elif isinstance(info, str):
                new_version = info
            analyses.append(
                analyze_dependency(dep, source_path, new_version=new_version)
            )
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
