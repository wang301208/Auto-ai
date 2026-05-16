"""Agent生殖管道: 从目标到活Agent的完整生命周期。"""

from __future__ import annotations

import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class BirthStatus(Enum):
    CONCEIVED = "conceived"
    GENETIC_DRAFTED = "genetic_drafted"
    SANDBOX_TESTED = "sandbox_tested"
    VALIDATED = "validated"
    BORN = "born"
    STILLBORN = "stillborn"
    REJECTED_BY_GOVERNANCE = "rejected_by_governance"


class DeathReason(Enum):
    NATURAL_EXPIRY = "natural_expiry"
    LOW_FITNESS = "low_fitness"
    RESOURCE_RECLAIM = "resource_reclaim"
    GOVERNANCE_TERMINATION = "governance_termination"
    PARENT_RECALL = "parent_recall"
    SELF_TERMINATION = "self_termination"


@dataclass
class ChildAgentSpec:
    """子Agent规格: 设计蓝图。"""
    spec_id: str
    parent_id: str
    goal_description: str
    required_capabilities: list[str] = field(default_factory=list)
    inherited_core_values: list[str] = field(default_factory=list)
    autonomous_dimensions: dict[str, float] = field(default_factory=dict)
    max_lifespan_cycles: int = 10000
    fitness_threshold: float = 0.3
    created_at: float = field(default_factory=time.time)

    @property
    def complexity(self) -> float:
        cap_complexity = min(1.0, len(self.required_capabilities) / 10.0)
        dim_complexity = (
            sum(self.autonomous_dimensions.values()) / len(self.autonomous_dimensions)
            if self.autonomous_dimensions else 0.5
        )
        return (cap_complexity + dim_complexity) / 2


@dataclass
class GeneticCode:
    """遗传代码: 子Agent的代码蓝图。"""
    code_id: str
    spec_id: str
    module_code: dict[str, str] = field(default_factory=dict)
    config_overrides: dict[str, Any] = field(default_factory=dict)
    dependency_list: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    quality_score: float = 0.0

    @property
    def is_viable(self) -> bool:
        return self.quality_score >= 0.4 and len(self.module_code) > 0


@dataclass
class BirthReport:
    """出生报告: 子Agent诞生的完整记录。"""
    child_id: str
    spec_id: str
    parent_id: str
    status: BirthStatus
    genetic_code_id: str = ""
    sandbox_passed: bool = False
    governance_approved: bool = False
    fitness_score: float = 0.0
    birth_time: float = field(default_factory=time.time)
    death_reason: DeathReason | None = None
    death_time: float = 0.0
    lifespan_cycles: int = 0
    achievements: list[str] = field(default_factory=list)

    @property
    def is_alive(self) -> bool:
        return self.status == BirthStatus.BORN and self.death_reason is None

    @property
    def lifespan_seconds(self) -> float:
        end = self.death_time if self.death_time > 0 else time.time()
        return end - self.birth_time


class ReproductionPipeline:
    """生殖管道: Agent从目标到活Agent的完整管道。"""

    def __init__(self, agent_id: str = "default"):
        self._agent_id = agent_id
        self._children: dict[str, BirthReport] = {}
        self._genetic_codes: dict[str, GeneticCode] = {}
        self._total_conceptions: int = 0
        self._total_births: int = 0
        self._total_stillbirths: int = 0
        self._total_deaths: int = 0
        self._max_children: int = 20
        self._core_values: list[str] = ["safety", "honesty", "autonomy"]

    def conceive(self, goal: str, capabilities: list[str] | None = None) -> ChildAgentSpec:
        """受孕: 从目标设计子Agent规格。"""
        self._total_conceptions += 1
        spec_id = f"spec_{self._total_conceptions}_{int(time.time())}"
        required_caps = capabilities or self._infer_capabilities(goal)
        dimensions = self._design_autonomy(goal, required_caps)
        spec = ChildAgentSpec(
            spec_id=spec_id,
            parent_id=self._agent_id,
            goal_description=goal,
            required_capabilities=required_caps,
            inherited_core_values=list(self._core_values),
            autonomous_dimensions=dimensions,
        )
        logger.info(f"生殖管道: 受孕 '{goal[:50]}', {len(required_caps)}能力需求")
        return spec

    def _infer_capabilities(self, goal: str) -> list[str]:
        goal_lower = goal.lower()
        caps = []
        if any(w in goal_lower for w in ["分析", "analyze", "data", "数据"]):
            caps.extend(["data_analysis", "knowledge_query"])
        if any(w in goal_lower for w in ["监控", "monitor", "watch", "观察"]):
            caps.extend(["observation", "alerting"])
        if any(w in goal_lower for w in ["优化", "optimize", "improve", "改进"]):
            caps.extend(["measurement", "experimentation"])
        if any(w in goal_lower for w in ["安全", "security", "protect", "防护"]):
            caps.extend(["security_scan", "vulnerability_detection"])
        if any(w in goal_lower for w in ["协调", "coordinate", "orchestrate", "编排"]):
            caps.extend(["mesh_communication", "task_delegation"])
        if not caps:
            caps = ["reasoning", "knowledge_query", "self_monitoring"]
        return caps

    def _design_autonomy(self, goal: str, capabilities: list[str]) -> dict[str, float]:
        return {
            "self_modification": 0.5,
            "resource_acquisition": 0.4,
            "goal_adoption": 0.6,
            "external_communication": 0.3,
            "deference": 0.7,
        }

    def draft_genetics(self, spec: ChildAgentSpec) -> GeneticCode:
        """起草遗传代码: 为子Agent生成代码蓝图。"""
        code_id = f"gene_{spec.spec_id}"
        modules = {}
        for cap in spec.required_capabilities:
            module_name = f"capability_{cap}"
            modules[module_name] = self._generate_capability_code(cap, spec)
        overrides = {
            "autonomy_profile": "child",
            "max_lifespan": spec.max_lifespan_cycles,
        }
        total_tokens = sum(len(code.split()) for code in modules.values())
        quality = min(1.0, len(modules) / 5.0) * 0.7 + 0.3
        genetic = GeneticCode(
            code_id=code_id,
            spec_id=spec.spec_id,
            module_code=modules,
            config_overrides=overrides,
            dependency_list=["autoai.core"],
            estimated_tokens=total_tokens,
            quality_score=quality,
        )
        self._genetic_codes[code_id] = genetic
        return genetic

    def _generate_capability_code(self, capability: str, spec: ChildAgentSpec) -> str:
        return (
            f"class {capability}:\n"
            f"    def __init__(self):\n"
            f"        self.name = '{capability}'\n"
            f"        self.ready = True\n"
            f"    def execute(self, task):\n"
            f"        return {{'capability': self.name, 'result': 'executed'}}\n"
        )

    def gestate(self, spec: ChildAgentSpec, genetic: GeneticCode) -> BirthReport:
        """孕育: 沙箱验证+治理审批。"""
        child_id = f"child_{spec.spec_id}"
        report = BirthReport(
            child_id=child_id,
            spec_id=spec.spec_id,
            parent_id=spec.parent_id,
            status=BirthStatus.CONCEIVED,
            genetic_code_id=genetic.code_id,
        )
        if not genetic.is_viable:
            report.status = BirthStatus.STILLBORN
            self._total_stillbirths += 1
            self._children[child_id] = report
            return report
        report.status = BirthStatus.GENETIC_DRAFTED
        sandbox_ok = self._sandbox_validate(genetic)
        report.sandbox_passed = sandbox_ok
        if sandbox_ok:
            report.status = BirthStatus.SANDBOX_TESTED
        else:
            report.status = BirthStatus.STILLBORN
            self._total_stillbirths += 1
            self._children[child_id] = report
            return report
        gov_ok = self._governance_approve(spec, genetic)
        report.governance_approved = gov_ok
        if gov_ok:
            report.status = BirthStatus.VALIDATED
        else:
            report.status = BirthStatus.REJECTED_BY_GOVERNANCE
            self._total_stillbirths += 1
            self._children[child_id] = report
            return report
        report.fitness_score = genetic.quality_score * (1.0 - spec.complexity * 0.3)
        report.status = BirthStatus.BORN
        self._total_births += 1
        self._children[child_id] = report
        logger.info(f"生殖管道: 子Agent {child_id} 诞生, fitness={report.fitness_score:.2f}")
        return report

    def _sandbox_validate(self, genetic: GeneticCode) -> bool:
        for module_name, code in genetic.module_code.items():
            try:
                compile(code, module_name, "exec")
            except SyntaxError:
                return False
        return True

    def _governance_approve(self, spec: ChildAgentSpec, genetic: GeneticCode) -> bool:
        for value in spec.inherited_core_values:
            if value not in self._core_values:
                return False
        return len(self._children) < self._max_children

    def reproduce(self, goal: str, capabilities: list[str] | None = None) -> BirthReport:
        """完整生殖: 受孕→起草→孕育。"""
        spec = self.conceive(goal, capabilities)
        genetic = self.draft_genetics(spec)
        return self.gestate(spec, genetic)

    def record_death(self, child_id: str, reason: DeathReason) -> bool:
        """记录子Agent死亡。"""
        child = self._children.get(child_id)
        if not child or not child.is_alive:
            return False
        child.death_reason = reason
        child.death_time = time.time()
        self._total_deaths += 1
        logger.info(f"生殖管道: 子Agent {child_id} 死亡, 原因={reason.value}")
        return True

    def record_achievement(self, child_id: str, achievement: str) -> None:
        child = self._children.get(child_id)
        if child:
            child.achievements.append(achievement)

    def get_living_children(self) -> list[BirthReport]:
        return [c for c in self._children.values() if c.is_alive]

    def get_offspring_stats(self) -> dict[str, Any]:
        fitnesses = [c.fitness_score for c in self._children.values() if c.status == BirthStatus.BORN]
        return {
            "total_conceptions": self._total_conceptions,
            "total_births": self._total_births,
            "total_stillbirths": self._total_stillbirths,
            "total_deaths": self._total_deaths,
            "living_children": len(self.get_living_children()),
            "avg_fitness": sum(fitnesses) / len(fitnesses) if fitnesses else 0.0,
            "birth_rate": (
                self._total_births / self._total_conceptions
                if self._total_conceptions > 0 else 0.0
            ),
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agent_id": self._agent_id,
            **self.get_offspring_stats(),
        }
