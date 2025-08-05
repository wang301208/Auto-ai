from __future__ import annotations

import threading

import autogpt.orchestrator as orch_mod
from autogpt.event_bus import EventMessage
from autogpt.orchestrator import Orchestrator


def test_orchestrator_process_lifecycle(monkeypatch):
    orc = Orchestrator()

    events: list[EventMessage] = []

    def fake_publish(event: EventMessage) -> None:
        events.append(event)

    orc.message_queue.publish = fake_publish  # type: ignore[assignment]

    def make_run(name: str):
        def _run(self: Orchestrator) -> None:
            self.message_queue.publish(
                EventMessage(event_type="TEST", payload={"agent": name}, source_agent=name)
            )
        return _run

    monkeypatch.setattr(Orchestrator, "_run_archaeologist", make_run("archaeologist"))
    monkeypatch.setattr(Orchestrator, "_run_tdd_developer", make_run("tdd_developer"))
    monkeypatch.setattr(Orchestrator, "_run_qa_agent", make_run("qa_agent"))
    monkeypatch.setattr(Orchestrator, "_run_sentry_agent", make_run("sentry_agent"))

    orc.start_agents()
    assert set(orc.threads.keys()) == {
        "archaeologist",
        "tdd_developer",
        "qa_agent",
        "sentry_agent",
    }
    for thread, _ in orc.threads.values():
        thread.join(timeout=0.1)

    orc.stop()

    assert [e.payload["agent"] for e in events] == [
        "archaeologist",
        "tdd_developer",
        "qa_agent",
        "sentry_agent",
    ]


def test_orchestrator_restarts_dead_threads(monkeypatch):
    orc = Orchestrator()

    started: list[str] = []

    def fake_start_thread(self, name: str, target):
        started.append(name)
        thread = threading.Thread(target=target, name=name)
        thread.start()
        orc.threads[name] = (thread, target)

    monkeypatch.setattr(Orchestrator, "_start_thread", fake_start_thread)

    def fast_run(self: Orchestrator) -> None:
        return

    monkeypatch.setattr(Orchestrator, "_run_archaeologist", fast_run)
    monkeypatch.setattr(Orchestrator, "_run_tdd_developer", fast_run)
    monkeypatch.setattr(Orchestrator, "_run_qa_agent", fast_run)
    monkeypatch.setattr(Orchestrator, "_run_sentry_agent", fast_run)

    orc.start_agents()
    assert started == [
        "archaeologist",
        "tdd_developer",
        "qa_agent",
        "sentry_agent",
    ]

    calls: list[str] = []

    def fake_restart(self, name: str, target):
        calls.append(name)
        thread = threading.Thread(target=target, name=name)
        thread.start()
        orc.threads[name] = (thread, target)

    monkeypatch.setattr(Orchestrator, "_start_thread", fake_restart)

    def fake_sleep(_):
        orc.stop_event.set()

    monkeypatch.setattr(orch_mod.time, "sleep", fake_sleep)

    orc.monitor()
    assert calls == [
        "archaeologist",
        "tdd_developer",
        "qa_agent",
        "sentry_agent",
    ]
