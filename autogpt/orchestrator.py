from __future__ import annotations

"""Simple orchestrator that starts core AutoGPT agents."""

import threading
import time
from pathlib import Path
from typing import Callable

from autogpt.agents import Archaeologist, QAAgent, SentryAgent, TDDDeveloper
from autogpt.event_bus import EventBus, MessageQueue


class DummyAgent:
    """Minimal stand-in for :class:`autogpt.agents.agent.Agent`.

    The specialized agents only access ``config.workspace_path`` on the passed
    ``agent`` instance.  To avoid heavy dependencies the orchestrator provides a
    very small object exposing this attribute.
    """

    def __init__(self, workspace_path: str | Path = ".") -> None:
        self.config = type("Config", (), {"workspace_path": str(workspace_path)})()


class Orchestrator:
    """Launch and supervise AutoGPT's event-driven helper agents."""

    def __init__(self, db_path: str | Path = "events.db") -> None:
        self.stop_event = threading.Event()
        self.event_bus = EventBus(db_path)
        self.message_queue = MessageQueue(self.event_bus)
        self.threads: dict[str, tuple[threading.Thread, Callable[[], None]]] = {}

    # ------------------------------------------------------------------
    def _start_thread(self, name: str, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        self.threads[name] = (thread, target)

    # ------------------------------------------------------------------
    def _run_archaeologist(self) -> None:
        Archaeologist(self.message_queue)
        while not self.stop_event.is_set():
            time.sleep(1)

    def _run_tdd_developer(self) -> None:
        agent = DummyAgent()
        TDDDeveloper(agent=agent, message_queue=self.message_queue)
        while not self.stop_event.is_set():
            time.sleep(1)

    def _run_qa_agent(self) -> None:
        agent = DummyAgent()
        QAAgent(agent=agent, message_queue=self.message_queue)
        while not self.stop_event.is_set():
            time.sleep(1)

    def _run_sentry_agent(self) -> None:
        agent = SentryAgent(message_queue=self.message_queue, stop_event=self.stop_event)
        agent.run()

    # ------------------------------------------------------------------
    def start_agents(self) -> None:
        """Start all helper agents."""

        self._start_thread("archaeologist", self._run_archaeologist)
        self._start_thread("tdd_developer", self._run_tdd_developer)
        self._start_thread("qa_agent", self._run_qa_agent)
        self._start_thread("sentry_agent", self._run_sentry_agent)

    # ------------------------------------------------------------------
    def monitor(self) -> None:
        """Monitor agent threads and restart them if necessary."""

        try:
            while not self.stop_event.is_set():
                for name, (thread, target) in list(self.threads.items()):
                    if not thread.is_alive():
                        self._start_thread(name, target)
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the orchestrator."""

        self.start_agents()
        self.monitor()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Stop all agents and wait for their threads to exit."""

        self.stop_event.set()
        for thread, _ in self.threads.values():
            thread.join(timeout=1)


__all__ = ["Orchestrator"]
