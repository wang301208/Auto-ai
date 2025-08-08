from __future__ import annotations

"""Agent that watches plugin logs and health to detect issues."""

import re
import threading
from pathlib import Path
from typing import Any, Dict, Mapping
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from packaging.version import InvalidVersion, Version
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from autogpt.event_bus import ISSUE_DETECTED, EventMessage, MessageQueue


class SentryAgent:
    """Monitor plugin logs, health endpoints and dependencies for issues."""

    ERROR_PATTERN = re.compile(r"ERROR|Exception|Traceback")

    def __init__(
        self,
        message_queue: MessageQueue,
        *,
        plugin_log_dirs: Mapping[str, Path] | None = None,
        plugin_endpoints: Mapping[str, str] | None = None,
        dependencies: Mapping[str, Mapping[str, Any]] | None = None,
        poll_interval: float = 5.0,
        stop_event: threading.Event | None = None,
    ) -> None:
        self.message_queue = message_queue
        self.plugin_log_dirs = plugin_log_dirs or self._discover_log_dirs()
        self.plugin_endpoints = plugin_endpoints or {}
        self.dependencies = dependencies or {}
        self.poll_interval = poll_interval
        self.stop_event = stop_event or threading.Event()
        self.observer = Observer()

    # ------------------------------------------------------------------
    def _discover_log_dirs(self) -> Dict[str, Path]:
        dirs: Dict[str, Path] = {}
        for path in Path("plugins").glob("*/logs"):
            if path.is_dir():
                dirs[path.parent.name] = path
        return dirs

    # ------------------------------------------------------------------
    def _create_handler(self, plugin: str) -> FileSystemEventHandler:
        agent = self

        class Handler(FileSystemEventHandler):
            def __init__(self) -> None:
                self.positions: Dict[str, int] = {}

            def on_modified(self, event: Any) -> None:  # type: ignore[override]
                if event.is_directory:
                    return
                pos = self.positions.get(event.src_path, 0)
                try:
                    with open(
                        event.src_path, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        f.seek(pos)
                        data = f.read()
                        self.positions[event.src_path] = f.tell()
                except Exception:
                    return
                if agent.ERROR_PATTERN.search(data):
                    agent._publish_issue(plugin, data, "bug")

        return Handler()

    # ------------------------------------------------------------------
    def _start_log_watchers(self) -> None:
        for plugin, log_dir in self.plugin_log_dirs.items():
            handler = self._create_handler(plugin)
            self.observer.schedule(handler, str(log_dir), recursive=False)
        if self.plugin_log_dirs:
            self.observer.start()

    # ------------------------------------------------------------------
    def _poll_health(self) -> None:
        for plugin, base in self.plugin_endpoints.items():
            url = base.rstrip("/") + "/health"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code != 200:
                    self._publish_issue(plugin, f"status {resp.status_code}", "bug")
            except Exception as e:  # pragma: no cover - network errors
                self._publish_issue(plugin, str(e), "bug")

    # ------------------------------------------------------------------
    def _check_dependencies(self) -> None:
        for plugin, deps in self.dependencies.items():
            for name, info in deps.items():
                repo_url: str | None = None
                current: str | None = None

                if isinstance(info, dict):
                    repo_url = info.get("repo_url")
                    current = info.get("version") or info.get("current")
                else:
                    current = str(info)

                if repo_url:
                    latest = self._get_latest_repo_release(repo_url)
                    if latest and current and self._is_newer_version(latest, current):
                        self._publish_issue(
                            plugin, f"{name} {latest}", "dependency_update"
                        )
                elif current:
                    try:
                        resp = requests.get(
                            f"https://pypi.org/pypi/{name}/json", timeout=5
                        )
                        if resp.status_code == 200:
                            latest = resp.json().get("info", {}).get("version")
                            if latest and self._is_newer_version(latest, current):
                                self._publish_issue(
                                    plugin, f"{name} {latest}", "dependency_update"
                                )
                    except Exception:  # pragma: no cover - network errors
                        continue

    def _get_latest_repo_release(self, repo_url: str) -> str | None:
        """Return latest release tag for a GitHub repository."""
        parsed = urlparse(repo_url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) < 2:
            return None
        owner, repo = path_parts[:2]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        try:
            resp = requests.get(api_url, timeout=5)
            if resp.status_code == 200:
                tag = resp.json().get("tag_name")
                if tag:
                    return tag
        except Exception:
            pass

        html_url = f"https://github.com/{owner}/{repo}/releases"
        try:
            resp = requests.get(html_url, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "/releases/tag/" in href:
                        return href.rstrip("/").split("/")[-1]
        except Exception:
            pass
        return None

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Return True if *latest* is newer than *current*."""
        latest = latest.lstrip("v")
        current = current.lstrip("v")
        try:
            return Version(latest) > Version(current)
        except InvalidVersion:
            return latest != current

    # ------------------------------------------------------------------
    def _publish_issue(self, plugin: str, error_log: str, issue_type: str) -> None:
        self.message_queue.publish(
            EventMessage(
                event_type=ISSUE_DETECTED,
                payload={
                    "plugin": plugin,
                    "error_log": error_log,
                    "issue_type": issue_type,
                },
                source_agent="sentry",
            )
        )

    # ------------------------------------------------------------------
    def run(self) -> None:
        self._start_log_watchers()
        try:
            while not self.stop_event.is_set():
                self._poll_health()
                self._check_dependencies()
                self.stop_event.wait(self.poll_interval)
        finally:
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
