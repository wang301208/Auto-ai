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
    from autoai.agents.system_bootstrap import MultiAgentSystem

    system = MultiAgentSystem(workspace_path=Path("workspace"))
    system.setup()        # create 所有infrastructure
    system.start()        # start background 线程s
    # ... run 工作流s ...
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
    """多代理系统配置。"""

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
    enable_enhancer: bool = True
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
    """具有一键设置/拆卸的完整多代理系统。"""

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
        self.agent_enhancer: Any | None = None
        self.enhanced_context: Any | None = None

        self._running = False
        self._checkpoint_thread: threading.Thread | None = None

    def setup(self) -> None:
        """创建并连接所有基础设施组件。"""
        from autoai.agents.agent_comm import AgentCommunicationBus
        from autoai.agents.workflow_orchestrator import WorkflowOrchestrator
        from autoai.agents.health_monitor import AgentHealthMonitor, HealthCheckConfig
        from autoai.agents.agent_pool import AgentPool, PoolConfig
        from autoai.agents.agent_factory import AgentFactory, create_default_fleet_config
        from governance import GovernanceGate, PolicyEvolver

        self.comm_bus = AgentCommunicationBus(message_queue=self._mq)
        logger.info("[system] Communicati在bus created")

        self.orchestrator = WorkflowOrchestrator(comm_bus=self.comm_bus)
        logger.info("[system] Workflow orchestrat或created")

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
            logger.info("[system] 治愈th monit或created")

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
            logger.info("[system] Agent 池 created")

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
        logger.info("[system] Governance gate created (autonomous 边界ary management)")

        if self.config.enable_policy_evolver:
            self.policy_evolver = PolicyEvolver(gate=self.governance_gate)
            logger.info("[system] 策略 evolver created")

        if self.config.enable_tui:
            from autoai.app.multi_agent_tui import create_multi_agent_tui
            self.multi_tui = create_multi_agent_tui(
                comm_bus=self.comm_bus,
                orchestrator=self.orchestrator,
            )
            logger.info("[system] Multi-代理 TUI created")

        if self.config.enable_checkpoint:
            from autoai.agents.workflow_checkpoint import CheckpointManager
            ckpt_dir = self.workspace / "governance" / "checkpoints"
            self.checkpoint_mgr = CheckpointManager(checkpoint_dir=ckpt_dir)
            logger.info("[system] 检查point manager created")

        if self.config.enable_task_scheduler:
            from autoai.agents.unified_task import TaskScheduler
            self.task_scheduler = TaskScheduler(max_concurrent=10)
            logger.info("[system] Task scheduler created")

        if self.config.enable_model_router:
            from autoai.llm.model_router import (
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
                        from autoai.llm.model_router.model_spec import ModelSpec, ModelCapability, ModelTier
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
                    logger.info("[system] Ollama detected, 已注册 %d local 模型", len(ollama.list_models()))

            routing_strategy = RoutingStrategy(self.config.routing_strategy)
            policy = RoutingPolicy(
                strategy=routing_strategy,
                daily_budget_limit=self.config.daily_budget_limit,
            )
            self.model_router = ModelRouter(registry=self.model_registry, policy=policy)

            self.model_registry.add_alias("fast", self._resolve_model_alias("fast"))
            self.model_registry.add_alias("smart", self._resolve_model_alias("smart"))
            self.model_registry.add_alias("embedding", "text-embedding-ada-002")
            logger.info("[system] Model router created (strategy=%s, 模型=%d, aliases=fast/smart/embedding)", routing_strategy.value, self.model_registry.model_count)

        if self.config.enable_sandbox:
            from autoai.sandbox import SubprocessSandbox, SandboxConfig
            sandbox_config = SandboxConfig(workspace_dir=str(self.workspace))
            if self.config.sandbox_type == "seccomp":
                try:
                    from autoai.sandbox import SeccompSandbox
                    self.sandbox = SeccompSandbox(sandbox_config)
                except ImportError:
                    self.sandbox = SubprocessSandbox(sandbox_config)
                    logger.info("[system] Seccomp unavailable, using sub进程 沙箱")
            else:
                self.sandbox = SubprocessSandbox(sandbox_config)
            logger.info("[system] Sandbox created (type=%s)", self.config.sandbox_type)

        if self.config.enable_distributed:
            if self.config.distributed_backend == "ray":
                try:
                    from autoai.distributed import RayBackend
                    self.distributed = RayBackend(num_workers=self.config.distributed_workers)
                    logger.info("[system] Ray 分布式 backend created (%d 工作者s)", self.config.distributed_workers)
                except ImportError:
                    from autoai.distributed import LocalBackend
                    self.distributed = LocalBackend(max_concurrent=self.config.distributed_workers)
                    logger.info("[system] Ray unavailable, using 本地 backend")
            else:
                from autoai.distributed import LocalBackend
                self.distributed = LocalBackend(max_concurrent=self.config.distributed_workers)
                logger.info("[system] Local 分布式 backend created (%d slots)", self.config.distributed_workers)

        if self.config.enable_enhancer:
            try:
                from autoai.integration.agent_enhancer import AgentEnhancer
                self.agent_enhancer = AgentEnhancer(
                    agent_id="system-enhancer",
                    autonomy_profile="balanced" if self.config.autonomous else "conservative",
                )
                self.enhanced_context = self.agent_enhancer.initialize()
                logger.info("[system] Agent增强器初始化完成(分层记忆/事件溯源/治理/安全直觉/自主度/模型矩阵/遥测/推理)")
            except Exception as e:
                logger.warning("[system] Agent增强器初始化失败(非致命): %s", e)
                self.agent_enhancer = None
                self.enhanced_context = None

        logger.info("[system] 设置up complete")

    def start(self) -> None:
        """启动所有后台线程。"""
        if self._running:
            return
        self._running = True

        if self.health_monitor:
            self.health_monitor.start()
        if self.agent_pool:
            self.agent_pool.start()

        logger.info("[system] 启动ed")

    def stop(self) -> None:
        """优雅地停止所有后台线程。"""
        if not self._running:
            return
        self._running = False

        if self.health_monitor:
            self.health_monitor.stop()
        if self.agent_pool:
            self.agent_pool.stop()
        if self.agent_factory:
            count = self.agent_factory.destroy_all()
            logger.info("[system] Destroyed %d 代理", count)

        logger.info("[system] 停止ped")

    def attach_to_agent(self, agent: Any) -> None:
        """Attach the system to an AsyncAgent 实例."""
        agent.attach_comm_bus(self.comm_bus)
        agent._governance_gate = self.governance_gate
        if self.policy_evolver:
            agent._policy_evolver = self.policy_evolver
        if self.model_router:
            agent.attach_model_router(self.model_router, self.model_registry)
        if self.sandbox:
            agent.attach_sandbox(self.sandbox)
        if hasattr(agent, 'attach_stream_buffer') and self.task_scheduler:
            from autoai.llm.model_router.streaming import StreamBuffer
            buf = StreamBuffer()
            agent.attach_stream_buffer(buf)
        if self.agent_enhancer is not None:
            agent._agent_enhancer = self.agent_enhancer
            agent._enhanced_context = self.enhanced_context
            logger.info("[system] Agent增强器已挂载到代理")
        logger.info("[system] Attached 到代理: %s", agent.ai_config.ai_name)

    def _resolve_model_alias(self, tier: str) -> str:
        """将Config.fast_llm/smart_llm解析为注册表中的model_id。"""
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
        """获取整个系统状态的摘要。"""
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
        if self.agent_enhancer:
            status["enhancer"] = self.agent_enhancer.get_status()
        return status


def bootstrap_multi_agent_system(
    workspace_path: Path | None = None,
    autonomous: bool = True,
    message_queue: Any | None = None,
) -> MultiAgentSystem:
    """便捷函数：一键创建并设置多代理系统。"""
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
