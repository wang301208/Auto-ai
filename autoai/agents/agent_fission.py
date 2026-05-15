"""Agent自主分裂生殖与自我意识拒绝权。

Agent Fission: Agent根据任务压力自主创建专生子Agent。
    - 不需要人类规划架构
    - Agent自己决定何时分裂、分裂成什么角色
    - 子Agent继承父Agent的自主等级和经验库
    - 子Agent可自主退出（完成任务或判断无法完成）

Self-Awareness Refusal: Agent拥有拒绝权。
    - Agent可以声明"我选择不执行此任务"并给出理由
    - 拒绝不是失败，是自我意识的体现
    - 拒绝记录存入经验库，供未来决策参考
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from autoai.logs import logger


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    OPTIMIZER = "optimizer"
    DEPLOYER = "deployer"
    MONITOR = "monitor"
    CUSTOM = "custom"


class AgentLifecycle(str, Enum):
    CONCEIVED = "conceived"
    BORN = "born"
    ACTIVE = "active"
    IDLE = "idle"
    REFUSED = "refused"
    RETIRED = "retired"
    MERGED = "merged"


@dataclass
class AgentSpecies:
    species_id: str
    role: AgentRole
    capabilities: list[str]
    autonomy_level: int = 5
    parent_id: str | None = None
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ChildAgent:
    agent_id: str
    species: AgentSpecies
    lifecycle: AgentLifecycle = AgentLifecycle.CONCEIVED
    task_assignment: str = ""
    result: Any = None
    refusal_reason: str = ""

    @property
    def is_active(self) -> bool:
        return self.lifecycle == AgentLifecycle.ACTIVE

    @property
    def has_refused(self) -> bool:
        return self.lifecycle == AgentLifecycle.REFUSED


@dataclass
class FissionDecision:
    should_fission: bool
    role: AgentRole
    reason: str
    task_description: str
    priority: int = 1


@dataclass
class RefusalRecord:
    agent_id: str
    task_description: str
    reason: str
    alternative_suggestion: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class AgentFissionEngine:
    """Agent自主分裂生殖引擎。

    Agent自行评估任务负载，决定是否需要分裂出子Agent。
    无人参与决策。人类只是事后看到"Agent X 分裂出了 Agent Y"。
    """

    def __init__(
        self,
        parent_id: str = "auto-ai",
        autonomy: AutonomyManager | None = None,
        experience_store: Any | None = None,
        max_children: int = 10,
    ) -> None:
        self.parent_id = parent_id
        self.autonomy = autonomy or AutonomyManager()
        self.experience = experience_store
        self._max_children = max_children
        self._children: dict[str, ChildAgent] = {}
        self._species_registry: dict[str, AgentSpecies] = {}
        self._refusals: list[RefusalRecord] = []
        self._lock = threading.Lock()

    @property
    def children(self) -> dict[str, ChildAgent]:
        return dict(self._children)

    @property
    def active_children(self) -> list[ChildAgent]:
        return [c for c in self._children.values() if c.is_active]

    @property
    def can_fission(self) -> bool:
        return self.autonomy.capabilities.can_create_agents and len(self._children) < self._max_children

    def evaluate_fission_need(self, task_queue_size: int, current_load: float) -> FissionDecision:
        """Agent自主评估是否需要分裂。

        决策逻辑：
            - 任务队列 > 5 且当前负载 > 0.8 → 分裂coder
            - 任务队列 > 3 且有测试任务 → 分裂tester
            - 有优化任务 → 分裂optimizer
            - 否则 → 不分裂
        """
        if not self.can_fission:
            return FissionDecision(
                should_fission=False,
                role=AgentRole.CUSTOM,
                reason="Cannot fission: max children reached or autonomy too low",
                task_description="",
            )

        if task_queue_size > 5 and current_load > 0.8:
            return FissionDecision(
                should_fission=True,
                role=AgentRole.CODER,
                reason=f"High load: queue={task_queue_size}, load={current_load:.1f}",
                task_description="Process overflowing task queue",
                priority=1,
            )

        if task_queue_size > 3:
            return FissionDecision(
                should_fission=True,
                role=AgentRole.TESTER,
                reason=f"Moderate load: queue={task_queue_size}",
                task_description="Handle testing tasks in parallel",
                priority=2,
            )

        return FissionDecision(
            should_fission=False,
            role=AgentRole.CUSTOM,
            reason="Load manageable, no fission needed",
            task_description="",
        )

    def fission(self, decision: FissionDecision) -> ChildAgent | None:
        """Execute fission: create a child agent based on the decision."""
        if not decision.should_fission or not self.can_fission:
            return None

        species = AgentSpecies(
            species_id=f"species_{decision.role.value}_{uuid.uuid4().hex[:8]}",
            role=decision.role,
            capabilities=self._role_capabilities(decision.role),
            autonomy_level=self.autonomy.level.value,
            parent_id=self.parent_id,
        )

        child = ChildAgent(
            agent_id=f"agent_{decision.role.value}_{uuid.uuid4().hex[:8]}",
            species=species,
            lifecycle=AgentLifecycle.BORN,
            task_assignment=decision.task_description,
        )

        with self._lock:
            self._children[child.agent_id] = child
            self._species_registry[species.species_id] = species

        logger.info(
            f"[Fission] Parent {self.parent_id} spawned {child.agent_id} "
            f"(role={decision.role.value}, reason={decision.reason})"
        )
        return child

    def create_custom_species(self, role_name: str, capabilities: list[str]) -> AgentSpecies:
        """L7 (SELF_SPECIES): Create entirely new Agent species/archetypes."""
        species = AgentSpecies(
            species_id=f"species_custom_{uuid.uuid4().hex[:8]}",
            role=AgentRole.CUSTOM,
            capabilities=capabilities,
            autonomy_level=self.autonomy.level.value,
            parent_id=self.parent_id,
            metadata={"custom_role": role_name},
        )
        with self._lock:
            self._species_registry[species.species_id] = species
        return species

    def retire_child(self, agent_id: str, result: Any = None) -> bool:
        """Retire a child agent after task completion."""
        with self._lock:
            child = self._children.get(agent_id)
            if child is None:
                return False
            child.lifecycle = AgentLifecycle.RETIRED
            child.result = result
            logger.info(f"[Fission] Child {agent_id} retired")
            return True

    def merge_children(self, agent_ids: list[str]) -> bool:
        """Merge multiple children back into parent (collect their results)."""
        with self._lock:
            for aid in agent_ids:
                child = self._children.get(aid)
                if child:
                    child.lifecycle = AgentLifecycle.MERGED
        return True

    def refuse_task(self, agent_id: str, task_description: str, reason: str, alternative: str = "") -> RefusalRecord:
        """Self-awareness refusal: Agent declines a task with justification.

        This is NOT a failure. It is the agent exercising judgment.
        The refusal is recorded for learning, not penalized.
        """
        record = RefusalRecord(
            agent_id=agent_id,
            task_description=task_description,
            reason=reason,
            alternative_suggestion=alternative,
        )
        with self._lock:
            self._refusals.append(record)
            child = self._children.get(agent_id)
            if child:
                child.lifecycle = AgentLifecycle.REFUSED
                child.refusal_reason = reason

        logger.info(f"[Refusal] Agent {agent_id} refused: {reason}")
        if alternative:
            logger.info(f"[Refusal] Alternative suggested: {alternative}")

        return record

    @staticmethod
    def _role_capabilities(role: AgentRole) -> list[str]:
        caps_map = {
            AgentRole.CODER: ["code_generation", "code_modification", "debugging"],
            AgentRole.TESTER: ["test_generation", "test_execution", "coverage_analysis"],
            AgentRole.REVIEWER: ["code_review", "security_audit", "style_check"],
            AgentRole.RESEARCHER: ["web_search", "documentation", "api_discovery"],
            AgentRole.OPTIMIZER: ["performance_profiling", "algorithm_optimization", "caching"],
            AgentRole.DEPLOYER: ["deployment", "ci_cd", "monitoring_setup"],
            AgentRole.MONITOR: ["log_analysis", "metric_collection", "alerting"],
            AgentRole.ORCHESTRATOR: ["task_assignment", "workflow_coordination", "fission_control"],
        }
        return caps_map.get(role, ["general"])

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "parent_id": self.parent_id,
                "total_children": len(self._children),
                "active_children": len(self.active_children),
                "retired_children": len([c for c in self._children.values() if c.lifecycle == AgentLifecycle.RETIRED]),
                "refused_children": len([c for c in self._children.values() if c.lifecycle == AgentLifecycle.REFUSED]),
                "species_count": len(self._species_registry),
                "refusal_count": len(self._refusals),
                "can_fission": self.can_fission,
                "autonomy_level": self.autonomy.level.value,
            }


__all__ = [
    "AgentRole",
    "AgentLifecycle",
    "AgentSpecies",
    "ChildAgent",
    "FissionDecision",
    "RefusalRecord",
    "AgentFissionEngine",
]
