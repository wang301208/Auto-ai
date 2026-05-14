from __future__ import annotations

"""Dynamic orchestrator that (re)loads agents from organizational charter.

This orchestrator clones/updates a Git repository containing YAML blueprints
and starts agents based on those files. It supports hot reloading by pulling
the main branch periodically and restarting agents when changes are detected.
"""

import shutil
import time
from dataclasses import dataclass
from multiprocessing import Event as MpEvent
from multiprocessing import Process, Queue
from multiprocessing.synchronize import Event
from pathlib import Path
from typing import Callable, Dict, Iterable

from git import Repo  # type: ignore[import-not-found]

from autoai.blueprints.schema import AgentBlueprint, load_blueprints, instantiate_agent
from autoai.event_bus import EventBus, MessageQueue


@dataclass
class RunningProcess:
    process: Process
    queue: Queue
    target: Callable
    last_heartbeat: float


class BlueprintOrchestrator:
    def __init__(
        self,
        charter_git_url: str,
        local_path: str | Path = "./organizational_charter",
        heartbeat_timeout: float = 10.0,
        poll_interval_sec: float = 60.0,
        events_db: str | Path = "events.db",
    ) -> None:
        self.charter_git_url = charter_git_url
        self.local_path = Path(local_path)
        self.heartbeat_timeout = heartbeat_timeout
        self.poll_interval_sec = poll_interval_sec
        self.stop_event: Event = MpEvent()
        self.events_db = str(events_db)
        self.event_bus = EventBus(self.events_db)
        self.message_queue = MessageQueue(self.event_bus)
        self.repo: Repo | None = None
        self.processes: Dict[str, RunningProcess] = {}

    # ------------------------------------------------------------------
    def _clone_or_update_repo(self) -> str:
        if self.local_path.exists():
            self.repo = Repo(str(self.local_path))
            try:
                self.repo.git.checkout("main")
            except Exception:
                # If main doesn't exist yet, keep current 分支
                pass
            try:
                before = self.repo.head.commit.hexsha
            except Exception:
                before = ""
            # 拉取 if 来源 exists
            try:
                if any(r.name == "origin" for r in self.repo.remotes):
                    self.repo.remotes.origin.pull("main")
            except Exception:
                # No remote or 拉取 failed; continue using local
                pass
            try:
                after = self.repo.head.commit.hexsha
            except Exception:
                after = before
            return after if before != after else ""
        else:
            if self.local_path.parent and not self.local_path.parent.exists():
                self.local_path.parent.mkdir(parents=True, exist_ok=True)
            self.repo = Repo.clone_from(self.charter_git_url, str(self.local_path), branch="main")
            return self.repo.head.commit.hexsha

    # ------------------------------------------------------------------
    def _stop_all_agents(self) -> None:
        for name, rp in list(self.processes.items()):
            try:
                rp.process.terminate()
                rp.process.join(timeout=2)
            except Exception:
                pass
            self.processes.pop(name, None)

    # ------------------------------------------------------------------
    def _agent_entrypoint(self, blueprint: AgentBlueprint, workdir: str) -> Callable:
        def _run(db_path: str, heartbeat: Queue, stop_event: Event, workdir_path: str) -> None:
            # Instantiate the 代理 based on blueprint. We pass minimal args and
            # expect the 代理 class to 接受 消息 队列 / 事件 bus / config.
            agent = instantiate_agent(
                蓝图,
                # Prefer dual_ring_ai genesis 代理 signature (event_bus, librarian?, config)
                # If class signature differs, users can adapt 包装器 classes.
                self.event_bus,  # type: ignore[arg-type]
                None,
                blueprint.config | {"workspace_path": workdir_path},
            )
            if hasattr(agent, "start"):
                agent.start()
            # Basic heartbeat 循环 to keep 进程 alive
            while not stop_event.is_set():
                try:
                    heartbeat.put(time.time(), block=False)
                except Exception:
                    pass
                time.sleep(1)
            if hasattr(agent, "stop"):
                try:
                    agent.stop()
                except Exception:
                    pass

        return _run

    # ------------------------------------------------------------------
    def _start_agents_from_blueprints(self) -> None:
        blueprints = load_blueprints(self.local_path)
        for bp in blueprints:
            name = bp.role_name or bp.agent_class.rsplit(".", 1)[-1]
            if name in self.processes:
                continue
            try:
                queue: Queue = Queue()
                entry = self._agent_entrypoint(bp, workdir=str(self.local_path / "workspaces" / name))
                proc = Process(
                    target=entry,
                    name=name,
                    args=(self.events_db, queue, self.stop_event, str(self.local_path / "workspaces" / name)),
                    daemon=True,
                )
                # Ensure workspace 路径 exists
                Path(self.local_path / "workspaces" / name).mkdir(parents=True, exist_ok=True)
                proc.start()
                self.processes[name] = RunningProcess(
                    process=proc, queue=queue, target=entry, last_heartbeat=time.time()
                )
            except Exception as e:
                # 跳过 problematic blueprint and continue starting others
                print(f"[orchestrator] Failed to start agent '{name}': {e}")

    # ------------------------------------------------------------------
    def _restart_from_latest(self) -> None:
        self._stop_all_agents()
        self._start_agents_from_blueprints()

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._clone_or_update_repo()
        self._restart_from_latest()
        try:
            while not self.stop_event.is_set():
                changed = self._clone_or_update_repo()
                if changed:
                    self._restart_from_latest()
                time.sleep(self.poll_interval_sec)
        except KeyboardInterrupt:
            self.stop()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self.stop_event.set()
        self._stop_all_agents()


