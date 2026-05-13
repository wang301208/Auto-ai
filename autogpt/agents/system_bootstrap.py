"""Multi-agent system bootstrapper.

One-call setup for the complete multi-agent system:
- AgentCommunicationBus
- WorkflowOrchestrator
- AgentHealthMonitor
- AgentPool (elastic scaling)
- AgentFactory (fleet creation)
- GovernanceGate (audit-net)
- PolicyEvolver (auto-evolution)
- MultiAgentTUI (observation)
- Workflow checkpoint auto-save
- TaskScheduler (unified task dispatch)
- ModelRouter (unified model routing)

Usage:
    from autogpt.agents.system_bootstrap import MultiAgentSystem

    system = MultiAgentSystem(workspace_path=Path("workspace"))
    system.setup()        # create all infrastructure
    system.start()        # start background threads
    # ... run workflows ...
    system.stop()         # graceful shutdown
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """Configuration for the multi-agent system."""

    autonomous: bool = True
    multi_agent: bool = True
    enable_health_monitor: bool = True
    enable_agent_pool: bool = True
    enable_policy_evolver: bool = True
    enable_checkpoint: bool = True
    enable_tui: bool = False
    enable_task_scheduler: bool = True
    enable_model_router: bool = True
    detect_local_models: bool = True
    heartbeat_interval: float = 10.0
    health_check_interval: float = 5.0
    checkpoint_interval: float = 30.0
    pool_check_interval: float = 15.0
    evolver_interval_cycles: int = 100
    hard_boundaries: set[str] = field(default_factory=lambda: {
        "budget_exceeded", "file_delete", "sandbox_escape",
    })
    routing_strategy: str = "cost_optimal"
    daily_budget_limit: float = 10.0
    enable_sandbox: bool = True
    sandbox_type: str = "subprocess"
    enable_distributed: bool = False
    distributed_backend: str = "local"
    distributed_workers: int = 2


class MultiAgentSystem:
    """Complete multi-agent system with one-call setup/teardown."""

    def __init__(
        self,
        workspace_path: Path | None = None,
        config: SystemConfig | None = None,
        message_queue: Any | None = None,
        agent_factory_callback: Callable[[str, str], str] | None = None,
        agent_restart_callback: Callable[[str, str], bool] | None = None,
    ) -> None:
        self.workspace = workspace_path or Path(".")
        self.config = config or SystemConfig()
        self._mq = message_queue
        self._agent_factory_cb = agent_factory_callback
        self._agent_restart_cb = agent_restart_callback

        self.comm_bus: Any | None = None
        self.orchestrator: Any | None = None
        self.health_monitor: Any | None = None
        self.agent_pool: Any | None = None
        self.agent_factory: Any | None = None
        self.governance_gate: Any | None = None
        self.policy_evolver: Any | None = None
        self.multi_tui: Any | None = None
        self.checkpoint_mgr: Any | None = None
        self.task_scheduler: Any | None = None
        self.model_router: Any | None = None
        self.model_registry: Any | None = None
        self.sandbox: Any | None = None
        self.distributed: Any | None = None

        self._running = False
        self._checkpoint_thread: threading.Thread | None = None

    def setup(self) -> None:
        """Create and wire all infrastructure components."""
        from autogpt.agents.agent_comm import AgentCommunicationBus
        from autogpt.agents.workflow_orchestrator import WorkflowOrchestrator
        from autogpt.agents.health_monitor import AgentHealthMonitor, HealthCheckConfig
        from autogpt.agents.agent_pool import AgentPool, PoolConfig
        from autogpt.agents.agent_factory import AgentFactory, create_default_fleet_config
        from governance import GovernanceGate, PolicyEvolver

        self.comm_bus = AgentCommunicationBus(message_queue=self._mq)
        logger.info("[system] Communication bus created")

        self.orchestrator = WorkflowOrchestrator(comm_bus=self.comm_bus)
        logger.info("[system] Workflow orchestrator created")

        if self.config.enable_health_monitor:
            health_config = HealthCheckConfig(
                heartbeat_interval_seconds=self.config.heartbeat_interval,
                check_interval_seconds=self.config.health_check_interval,
                auto_evict=True,
                auto_restart=self._agent_restart_cb is not None,
            )
            self.health_monitor = AgentHealthMonitor(
                comm_bus=self.comm_bus,
                orchestrator=self.orchestrator,
                config=health_config,
                restart_callback=self._agent_restart_cb,
            )
            logger.info("[system] Health monitor created")

        if self.config.enable_agent_pool:
            pool_config = PoolConfig(
                check_interval_seconds=self.config.pool_check_interval,
            )
            self.agent_pool = AgentPool(
                orchestrator=self.orchestrator,
                comm_bus=self.comm_bus,
                health_monitor=self.health_monitor,
                agent_factory=self._agent_factory_cb,
                config=pool_config,
            )
            logger.info("[system] Agent pool created")

        self.agent_factory = AgentFactory(
            orchestrator=self.orchestrator,
            comm_bus=self.comm_bus,
            health_monitor=self.health_monitor,
            agent_pool=self.agent_pool,
        )
        default_fleet = create_default_fleet_config()
        self.agent_factory.create_fleet(default_fleet)
        logger.info("[system] Default fleet deployed: %s", self.agent_factory.created_agents)

        self.governance_gate = GovernanceGate(
            hard_boundaries=self.config.hard_boundaries,
        )
        logger.info("[system] Governance gate created (autonomous boundary management)")

        if self.config.enable_policy_evolver:
            self.policy_evolver = PolicyEvolver(gate=self.governance_gate)
            logger.info("[system] Policy evolver created")

        if self.config.enable_tui:
            from autogpt.app.multi_agent_tui import create_multi_agent_tui
            self.multi_tui = create_multi_agent_tui(
                comm_bus=self.comm_bus,
                orchestrator=self.orchestrator,
            )
            logger.info("[system] Multi-agent TUI created")

        if self.config.enable_checkpoint:
            from autogpt.agents.workflow_checkpoint import CheckpointManager
            ckpt_dir = self.workspace / "governance" / "checkpoints"
            self.checkpoint_mgr = CheckpointManager(checkpoint_dir=ckpt_dir)
            logger.info("[system] Checkpoint manager created")

        if self.config.enable_task_scheduler:
            from autogpt.agents.unified_task import TaskScheduler
            self.task_scheduler = TaskScheduler(max_concurrent=10)
            logger.info("[system] Task scheduler created")

        if self.config.enable_model_router:
            from autogpt.llm.model_router import (
                ModelRegistry,
                ModelRouter,
                OllamaProvider,
                OpenAICompatProvider,
                RoutingPolicy,
                RoutingStrategy,
            )
            self.model_registry = ModelRegistry()
            self.model_registry.load_builtin_specs()
            models_yaml = Path(__file__).parent.parent / "llm" / "model_router" / "models.yaml"
            if models_yaml.exists():
                self.model_registry.load_from_file(models_yaml)

            if self.config.detect_local_models:
                ollama = OllamaProvider(auto_detect=True)
                if ollama.is_detected:
                    self.model_registry.register_provider(ollama)
                    for m in ollama.list_models():
                        from autogpt.llm.model_router.model_spec import ModelSpec, ModelCapability, ModelTier
                        spec = ModelSpec(
                            model_id=m,
                            provider_name="ollama",
                            display_name=f"{m} (Local)",
                            tier=ModelTier.FAST,
                            capabilities=ModelCapability.CHAT | ModelCapability.STREAMING,
                            is_local=True,
                        )
                        if not self.model_registry.get_model(m):
                            self.model_registry.register_model(spec)
                    logger.info("[system] Ollama detected, registered %d local models", len(ollama.list_models()))

            routing_strategy = RoutingStrategy(self.config.routing_strategy)
            policy = RoutingPolicy(
                strategy=routing_strategy,
                daily_budget_limit=self.config.daily_budget_limit,
            )
            self.model_router = ModelRouter(registry=self.model_registry, policy=policy)

            self.model_registry.add_alias("fast", self._resolve_model_alias("fast"))
            self.model_registry.add_alias("smart", self._resolve_model_alias("smart"))
            self.model_registry.add_alias("embedding", "text-embedding-ada-002")
            logger.info("[system] Model router created (strategy=%s, models=%d, aliases=fast/smart/embedding)", routing_strategy.value, self.model_registry.model_count)

        if self.config.enable_sandbox:
            from autogpt.sandbox import SubprocessSandbox, SandboxConfig
            sandbox_config = SandboxConfig(workspace_dir=str(self.workspace))
            if self.config.sandbox_type == "seccomp":
                try:
                    from autogpt.sandbox import SeccompSandbox
                    self.sandbox = SeccompSandbox(sandbox_config)
                except ImportError:
                    self.sandbox = SubprocessSandbox(sandbox_config)
                    logger.info("[system] Seccomp unavailable, using subprocess sandbox")
            else:
                self.sandbox = SubprocessSandbox(sandbox_config)
            logger.info("[system] Sandbox created (type=%s)", self.config.sandbox_type)

        if self.config.enable_distributed:
            if self.config.distributed_backend == "ray":
                try:
                    from autogpt.distributed import RayBackend
                    self.distributed = RayBackend(num_workers=self.config.distributed_workers)
                    logger.info("[system] Ray distributed backend created (%d workers)", self.config.distributed_workers)
                except ImportError:
                    from autogpt.distributed import LocalBackend
                    self.distributed = LocalBackend(max_concurrent=self.config.distributed_workers)
                    logger.info("[system] Ray unavailable, using local backend")
            else:
                from autogpt.distributed import LocalBackend
                self.distributed = LocalBackend(max_concurrent=self.config.distributed_workers)
                logger.info("[system] Local distributed backend created (%d slots)", self.config.distributed_workers)

        logger.info("[system] Setup complete")

    def start(self) -> None:
        """Start all background threads."""
        if self._running:
            return
        self._running = True

        if self.health_monitor:
            self.health_monitor.start()
        if self.agent_pool:
            self.agent_pool.start()

        logger.info("[system] Started")

    def stop(self) -> None:
        """Gracefully stop all background threads."""
        if not self._running:
            return
        self._running = False

        if self.health_monitor:
            self.health_monitor.stop()
        if self.agent_pool:
            self.agent_pool.stop()
        if self.agent_factory:
            count = self.agent_factory.destroy_all()
            logger.info("[system] Destroyed %d agents", count)

        logger.info("[system] Stopped")

    def attach_to_agent(self, agent: Any) -> None:
        """Attach the system to an AsyncAgent instance."""
        agent.attach_comm_bus(self.comm_bus)
        agent._governance_gate = self.governance_gate
        if self.policy_evolver:
            agent._policy_evolver = self.policy_evolver
        if self.model_router:
            agent.attach_model_router(self.model_router, self.model_registry)
        if self.sandbox:
            agent.attach_sandbox(self.sandbox)
        if hasattr(agent, 'attach_stream_buffer') and self.task_scheduler:
            from autogpt.llm.model_router.streaming import StreamBuffer
            buf = StreamBuffer()
            agent.attach_stream_buffer(buf)
        logger.info("[system] Attached to agent: %s", agent.ai_config.ai_name)

    def _resolve_model_alias(self, tier: str) -> str:
        """Resolve Config.fast_llm/smart_llm to a model_id in registry."""
        if not self.model_registry:
            return "gpt-4o-mini"
        config_model = getattr(self.config, f"{tier}_llm", None)
        if config_model:
            existing = self.model_registry.get_model(config_model)
            if existing:
                return config_model
        tier_map = {"fast": "gpt-4o-mini", "smart": "gpt-4o", "embedding": "text-embedding-ada-002"}
        fallback = tier_map.get(tier, "gpt-4o-mini")
        if self.model_registry.get_model(fallback):
            return fallback
        models = self.model_registry.list_models(tier=tier)
        return models[0].model_id if models else fallback

    def get_system_status(self) -> dict[str, Any]:
        """Get a summary of the entire system state."""
        status: dict[str, Any] = {"running": self._running}
        if self.comm_bus:
            status["comm"] = self.comm_bus.get_stats()
        if self.orchestrator:
            status["orchestrator"] = {
                "active_workflows": self.orchestrator.active_workflow_count,
                "agent_utilization": self.orchestrator.get_agent_utilization(),
            }
        if self.health_monitor:
            status["health"] = self.health_monitor.get_all_status()
        if self.agent_pool:
            status["pool"] = self.agent_pool.get_pool_status()
        if self.governance_gate:
            status["governance"] = {
                "autonomous": True,
                "hard_boundaries": list(self.governance_gate.hard_boundaries),
                "boundary_manager": self.governance_gate.boundary.stats() if self.governance_gate.boundary else {},
            }
        if self.agent_factory:
            status["fleet"] = self.agent_factory.created_agents
        if self.task_scheduler:
            status["task_scheduler"] = {
                "pending": self.task_scheduler.pending_count,
                "completed": len(self.task_scheduler.completed_tasks),
                "stats": {
                    "total_dispatched": self.task_scheduler.stats.total_dispatched,
                    "total_succeeded": self.task_scheduler.stats.total_succeeded,
                    "total_failed": self.task_scheduler.stats.total_failed,
                    "by_category": self.task_scheduler.stats.by_category,
                },
            }
        if self.model_router:
            status["model_router"] = {
                "registry_summary": self.model_registry.summary(),
                "daily_remaining": self.model_router.policy.daily_remaining,
            }
        if self.sandbox:
            status["sandbox"] = {
                "type": self.config.sandbox_type,
                "enabled": self.config.enable_sandbox,
            }
        if self.distributed:
            status["distributed"] = self.distributed.summary()
        return status


def bootstrap_multi_agent_system(
    workspace_path: Path | None = None,
    autonomous: bool = True,
    message_queue: Any | None = None,
) -> MultiAgentSystem:
    """Convenience function: create and setup a multi-agent system in one call."""
    config = SystemConfig(autonomous=autonomous, multi_agent=True)
    system = MultiAgentSystem(
        workspace_path=workspace_path,
        config=config,
        message_queue=message_queue,
    )
    system.setup()
    system.start()
    return system


__all__ = [
    "SystemConfig",
    "MultiAgentSystem",
    "bootstrap_multi_agent_system",
]
