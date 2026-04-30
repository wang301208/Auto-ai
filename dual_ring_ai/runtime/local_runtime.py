"""Composable local runtime for the autonomous evolution backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..core.algorithm_experiment import AlgorithmExperimentRunner
from ..core.algorithm_registry import AlgorithmRegistry
from ..core.event_bus import EventBus
from ..core.governance import GovernanceStore, PermissionGate
from ..core.sandbox_runner import SandboxRunner
from ..core.skill_lifecycle import SkillLifecycleManager


@dataclass
class LocalRuntimeConfig:
    root_path: Path
    enable_agents: bool = False


class LocalRuntime:
    """Local-first composition root for core backend services."""

    def __init__(self, config: LocalRuntimeConfig) -> None:
        self.config = config
        self.root_path = Path(config.root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.running = False

        self.event_bus = EventBus()
        self.governance = GovernanceStore(self.root_path / "governance")
        self.permission_gate = PermissionGate()
        self.skill_lifecycle = SkillLifecycleManager(
            self.root_path / "skill_library",
            self.event_bus,
            audit_log_path=self.root_path / "logs" / "skill_lifecycle_audit.jsonl",
        )
        self.algorithm_registry = AlgorithmRegistry(self.root_path / "algorithm_library")
        self.algorithm_experiments = AlgorithmExperimentRunner(
            self.root_path / "algorithm_experiments"
        )
        self.sandbox_runner = SandboxRunner(self.root_path / "workspace")
        self.agents = {}

    def start(self) -> None:
        self.event_bus.connect()
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.event_bus.disconnect()

    def status_snapshot(self) -> dict:
        return {
            "running": self.running,
            "services": {
                "event_bus": "ready",
                "governance": "ready",
                "skill_lifecycle": "ready",
                "algorithm_registry": "ready",
                "algorithm_experiments": "ready",
                "sandbox_runner": "ready",
            },
            "agents": list(self.agents.keys()),
            "paths": {
                "root_path": str(self.root_path),
                "skill_library": str(self.root_path / "skill_library"),
                "algorithm_library": str(self.root_path / "algorithm_library"),
                "workspace": str(self.root_path / "workspace"),
            },
        }
