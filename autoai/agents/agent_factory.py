"""从配置批量创建代理的工厂.

启用声明式多代理设置 from a YAML/JSON config file,
creating AgentProfile, registering with orchestrator, comm_bus,
health monitor, and agent pool in one step.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agent_comm import AgentCommunicationBus
from .workflow_orchestrator import AgentProfile, WorkflowOrchestrator
from .health_monitor import AgentHealthMonitor
from .agent_pool import AgentPool

logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """规范 for a single 代理 to be 已创建."""

    agent_id: str
    name: str = ""
    role: str = ""
    roles: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    reliability_score: float = 1.0
    permanent: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.agent_id
        if self.role and not self.roles:
            self.roles = {self.role}

    def to_profile(self) -> AgentProfile:
        return AgentProfile(
            agent_id=self.agent_id,
            roles=self.roles,
            capabilities=self.capabilities,
            max_concurrent_tasks=self.max_concurrent_tasks,
            reliability_score=self.reliability_score,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentSpec:
        roles = data.get("roles", [])
        if isinstance(roles, str):
            roles = [r.strip() for r in roles.split(",")]
        caps = data.get("capabilities", [])
        if isinstance(caps, str):
            caps = [c.strip() for c in caps.split(",")]
        return cls(
            agent_id=data["agent_id"],
            name=data.get("name", data["agent_id"]),
            role=data.get("role", ""),
            roles=set(roles),
            capabilities=set(caps),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 3),
            reliability_score=data.get("reliability_score", 1.0),
            permanent=data.get("permanent", True),
        )


@dataclass
class AgentFleetConfig:
    """满 fleet 配置."""

    fleet_name: str = "default"
    agents: list[AgentSpec] = field(default_factory=list)
    pool_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentFleetConfig:
        agents = [AgentSpec.from_dict(a) for a in data.get("agents", [])]
        return cls(
            fleet_name=data.get("fleet_name", "default"),
            agents=agents,
            pool_config=data.get("pool_config", {}),
        )

    @classmethod
    def load(cls, path: Path) -> AgentFleetConfig:
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            try:
                import yaml
                data = yaml.safe_load(text)
            except ImportError:
                raise ImportError("YAML配置文件需要PyYAML")
        else:
            data = json.loads(text)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        data = {
            "fleet_name": self.fleet_name,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "role": a.role,
                    "roles": sorted(a.roles),
                    "capabilities": sorted(a.capabilities),
                    "max_concurrent_tasks": a.max_concurrent_tasks,
                    "reliability_score": a.reliability_score,
                    "permanent": a.permanent,
                }
                for a in self.agents
            ],
            "pool_config": self.pool_config,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class AgentFactory:
    """创建 and 注册 agents from fleet 配置.

    One-call setup: parse config → create profiles → register with
    编排器, comm_bus, health_monitor, and agent_pool.
    """

    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        comm_bus: AgentCommunicationBus,
        health_monitor: AgentHealthMonitor | None = None,
        agent_pool: AgentPool | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.comm_bus = comm_bus
        self.health = health_monitor
        self.pool = agent_pool
        self._created: list[str] = []

    def create_fleet(self, config: AgentFleetConfig) -> list[str]:
        """创建 all agents from a fleet config. Returns 列表 of 代理 IDs."""
        created = []
        for spec in config.agents:
            try:
                self._create_one(spec)
                created.append(spec.agent_id)
            except Exception as e:
                logger.error("[工厂] Failed 到create 代理 %s: %s", spec.agent_id, e)
        self._created.extend(created)
        logger.info("[factory] Fleet '%s' created: %d 代理", config.fleet_name, len(created))
        return created

    def _create_one(self, spec: AgentSpec) -> None:
        profile = spec.to_profile()
        self.orchestrator.register_agent(profile)
        self.comm_bus.register_agent(spec.agent_id, role=spec.role or next(iter(spec.roles), ""))
        if self.health is not None:
            self.health.register(spec.agent_id, role=spec.role or "")
        if self.pool is not None:
            self.pool.add_agent(
                spec.agent_id,
                roles=spec.roles,
                capabilities=spec.capabilities,
                permanent=spec.permanent,
            )
        logger.info(
            "[factory] Agent '%s' created: roles=%s caps=%s",
            spec.agent_id, spec.roles, spec.capabilities,
        )

    def destroy_all(self) -> int:
        """移除 all 已创建 agents. Returns 计数 已移除."""
        count = 0
        for agent_id in self._created:
            try:
                self.orchestrator.unregister_agent(agent_id)
                self.comm_bus.unregister_agent(agent_id)
                if self.health:
                    self.health.unregister(agent_id)
                if self.pool:
                    self.pool.remove_agent(agent_id)
                count += 1
            except Exception:
                pass
        self._created.clear()
        return count

    @property
    def created_agents(self) -> list[str]:
        return list(self._created)


def create_default_fleet_config() -> AgentFleetConfig:
    """创建 a sensible default fleet 配置."""
    return AgentFleetConfig(
        fleet_name="default",
        agents=[
            AgentSpec(
                agent_id="primary",
                name="Primary Agent",
                role="primary",
                roles={"primary", "coder", "thinker"},
                capabilities={"plan", "execute", "self_improve", "debug"},
            ),
            AgentSpec(
                agent_id="reviewer",
                name="Code Reviewer",
                role="reviewer",
                roles={"reviewer"},
                capabilities={"review", "approve", "test"},
                max_concurrent_tasks=5,
            ),
            AgentSpec(
                agent_id="tester",
                name="Test Runner",
                role="tester",
                roles={"tester"},
                capabilities={"test", "debug", "verify"},
            ),
        ],
    )


__all__ = [
    "AgentSpec",
    "AgentFleetConfig",
    "AgentFactory",
    "create_default_fleet_config",
]
