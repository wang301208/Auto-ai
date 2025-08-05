from __future__ import annotations

"""Simple orchestrator that starts core AutoGPT agents."""

import os
import time
import threading
from dataclasses import dataclass
from multiprocessing import Event, Process, Queue
from pathlib import Path
from queue import Empty
from typing import Callable, Dict, Iterable, Mapping

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


def _run_archaeologist(db_path: str, heartbeat: Queue, stop_event: Event, workdir: str) -> None:
    """Entry point for the Archaeologist agent process."""

    os.chdir(workdir)
    message_queue = MessageQueue(EventBus(db_path))
    Archaeologist(message_queue)
    while not stop_event.is_set():
        heartbeat.put(time.time())
        time.sleep(1)


def _run_tdd_developer(db_path: str, heartbeat: Queue, stop_event: Event, workdir: str) -> None:
    os.chdir(workdir)
    message_queue = MessageQueue(EventBus(db_path))
    agent = DummyAgent(workdir)
    TDDDeveloper(agent=agent, message_queue=message_queue)
    while not stop_event.is_set():
        heartbeat.put(time.time())
        time.sleep(1)


def _run_qa_agent(db_path: str, heartbeat: Queue, stop_event: Event, workdir: str) -> None:
    os.chdir(workdir)
    message_queue = MessageQueue(EventBus(db_path))
    agent = DummyAgent(workdir)
    QAAgent(agent=agent, message_queue=message_queue)
    while not stop_event.is_set():
        heartbeat.put(time.time())
        time.sleep(1)


def _run_sentry_agent(db_path: str, heartbeat: Queue, stop_event: Event, workdir: str) -> None:
    os.chdir(workdir)
    message_queue = MessageQueue(EventBus(db_path))
    agent = SentryAgent(message_queue=message_queue, stop_event=stop_event)

    def _beat() -> None:
        while not stop_event.is_set():
            heartbeat.put(time.time())
            time.sleep(1)

    threading.Thread(target=_beat, daemon=True).start()
    agent.run()


AGENT_TARGETS: Dict[str, Callable[[str, Queue, Event, str], None]] = {
    "archaeologist": _run_archaeologist,
    "tdd_developer": _run_tdd_developer,
    "qa_agent": _run_qa_agent,
    "sentry_agent": _run_sentry_agent,
}

AVAILABLE_AGENTS = list(AGENT_TARGETS.keys())


@dataclass
class ProcessInfo:
    process: Process
    target: Callable[[str, Queue, Event, str], None]
    queue: Queue
    last_heartbeat: float
    workdir: str


class Orchestrator:
    """Launch and supervise AutoGPT's event-driven helper agents."""

    def __init__(
        self,
        db_path: str | Path = "events.db",
        agents: Iterable[str] | None = None,
        workdirs: Mapping[str, str | Path] | None = None,
        heartbeat_timeout: float = 5.0,
    ) -> None:
        self.db_path = str(db_path)
        self.stop_event = Event()
        self.heartbeat_timeout = heartbeat_timeout
        self.agents = list(agents) if agents is not None else list(AGENT_TARGETS.keys())
        self.workdirs = {name: str(path) for name, path in (workdirs or {}).items()}
        self.processes: Dict[str, ProcessInfo] = {}

    # ------------------------------------------------------------------
    def _start_process(self, name: str) -> None:
        target = AGENT_TARGETS[name]
        workdir = self.workdirs.get(name, ".")
        queue: Queue = Queue()
        process = Process(
            target=target,
            name=name,
            args=(self.db_path, queue, self.stop_event, workdir),
            daemon=True,
        )
        process.start()
        self.processes[name] = ProcessInfo(
            process=process,
            target=target,
            queue=queue,
            last_heartbeat=time.time(),
            workdir=workdir,
        )

    # ------------------------------------------------------------------
    def start_agents(self) -> None:
        for name in self.agents:
            self._start_process(name)

    # ------------------------------------------------------------------
    def monitor(self) -> None:
        try:
            while not self.stop_event.is_set():
                for name, info in list(self.processes.items()):
                    while True:
                        try:
                            info.last_heartbeat = info.queue.get_nowait()
                        except Empty:
                            break
                    alive = info.process.is_alive()
                    stale = time.time() - info.last_heartbeat > self.heartbeat_timeout
                    if not alive or stale:
                        if alive:
                            info.process.terminate()
                            info.process.join(timeout=1)
                        self._start_process(name)
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    # ------------------------------------------------------------------
    def start(self) -> None:
        self.start_agents()
        self.monitor()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self.stop_event.set()
        for info in self.processes.values():
            info.process.join(timeout=1)
            if info.process.is_alive():
                info.process.terminate()


__all__ = ["Orchestrator", "AVAILABLE_AGENTS"]
