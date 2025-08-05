from __future__ import annotations

import time
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Event

import pytest

import autogpt.orchestrator as orch_mod
from autogpt.orchestrator import Orchestrator


def test_dashboard_process_monitored(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_dashboard(
        db_path: str, heartbeat: Queue, stop_event: Event, workdir: str
    ) -> None:
        while not stop_event.is_set():
            heartbeat.put(time.time())
            time.sleep(0.1)

    monkeypatch.setattr(orch_mod, "_run_dashboard", fake_run_dashboard)

    orc = Orchestrator(agents=[])
    orc.start_agents()

    assert "dashboard" in orc.processes

    info = orc.processes["dashboard"]
    info.process.terminate()
    info.process.join()

    restarted: list[bool] = []

    def fake_start_dashboard(self: Orchestrator) -> None:
        restarted.append(True)

    monkeypatch.setattr(Orchestrator, "_start_dashboard", fake_start_dashboard)

    def fake_sleep(_: float) -> None:
        orc.stop_event.set()

    monkeypatch.setattr(orch_mod.time, "sleep", fake_sleep)

    orc.monitor()
    assert restarted
    orc.stop()
