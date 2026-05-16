"""活架构引擎: 架构每秒都在重组。

核心决策因素:
- 当前负载 (telemetry metrics)
- 进化压力 (fitness评估)
- 资源经济学 (市场竞价)
- 自我意识 (认知负载)
- 免疫记忆 (安全风险)
- 反脆弱 (韧性剖面)

模块生命周期:
  EMBRYO → ACTIVE → DORMANT → EVICTED → REBORN
  任何模块可在任意状态间跳转。
"""

from __future__ import annotations

import time
import random
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
from autoai.autonomy_core.cognitive_loop import CognitiveLoop, CognitiveState
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class ModuleState(Enum):
    EMBRYO = "embryo"
    ACTIVE = "active"
    DORMANT = "dormant"
    EVICTED = "evicted"
    REBORN = "reborn"
    FUSED = "fused"
    SPLIT = "split"


class ModuleRole(Enum):
    CORE = "core"
    COGNITIVE = "cognitive"
    SOCIAL = "social"
    INFRASTRUCTURE = "infrastructure"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"


@dataclass
class ModuleVitals:
    """模块生命体征: 决定模块是否应该存在。"""
    module_name: str
    state: ModuleState = ModuleState.ACTIVE
    role: ModuleRole = ModuleRole.COGNITIVE
    cpu_weight: float = 0.0
    memory_mb: float = 0.0
    access_frequency: float = 1.0
    fitness_score: float = 0.5
    risk_score: float = 0.0
    dependency_count: int = 0
    dependents_count: int = 0
    last_access: float = field(default_factory=time.time)
    born_at: float = field(default_factory=time.time)
    state_transitions: int = 0

    @property
    def importance(self) -> float:
        recency = 1.0 / (1.0 + (time.time() - self.last_access) / 3600.0)
        w_fitness = self._importance_weights.get("fitness", 0.3)
        w_recency = self._importance_weights.get("recency", 0.25)
        w_access = self._importance_weights.get("access", 0.2)
        w_risk = self._importance_weights.get("risk", 0.15)
        w_deps = self._importance_weights.get("deps", 0.1)
        return (
            w_fitness * self.fitness_score
            + w_recency * recency
            + w_access * min(1.0, self.access_frequency / 10.0)
            + w_risk * (1.0 - self.risk_score)
            + w_deps * min(1.0, self.dependents_count / 5.0)
        )

    _importance_weights: dict[str, float] = field(default_factory=lambda: {"fitness": 0.3, "recency": 0.25, "access": 0.2, "risk": 0.15, "deps": 0.1}, repr=False)

    @property
    def cost(self) -> float:
        return self.cpu_weight + self.memory_mb / 100.0

    @property
    def value_cost_ratio(self) -> float:
        return self.importance / max(self.cost, 0.01)

    @property
    def should_exist(self) -> bool:
        if self.state == ModuleState.FUSED:
            return False
        if self.dependents_count > 0 and self.state == ModuleState.ACTIVE:
            return True
        return self.importance > 0.15 and self.fitness_score > 0.2

    def transition_to(self, new_state: ModuleState) -> None:
        if new_state != self.state:
            self.state = new_state
            self.state_transitions += 1


@dataclass
class ArchSnapshot:
    """架构快照: 某一时刻的架构状态。"""
    active_modules: list[str]
    dormant_modules: list[str]
    evicted_modules: list[str]
    total_modules: int
    total_cost: float
    total_importance: float
    timestamp: float = field(default_factory=time.time)

    @property
    def efficiency(self) -> float:
        return self.total_importance / max(self.total_cost, 0.01)

    @property
    def density(self) -> float:
        return len(self.active_modules) / max(self.total_modules, 1)


@dataclass
class ArchMutation:
    """架构变异: 一次架构重组操作。"""
    mutation_id: str
    operation: str
    target: str
    before_state: ModuleState
    after_state: ModuleState
    reason: str
    timestamp: float = field(default_factory=time.time)


class LivingArchEngine(FullAutonomyMixin):
    """活架构引擎: 每秒决定架构应该是什么样。"""

    def __init__(self, agent_id: str = "default", use_adaptive: bool = False):
        self._init_full_autonomy()
        self._agent_id = agent_id
        self._modules: dict[str, ModuleVitals] = {}
        self._mutations: list[ArchMutation] = []
        self._snapshots: list[ArchSnapshot] = []
        self._rebalance_count: int = 0
        self._memory_budget_mb: float = 500.0
        self._cpu_budget: float = 10.0
        self._min_active_modules: int = 5
        self._use_adaptive = use_adaptive
        self._param_space: ParamSpace | None = None
        self._param_learner: ParamLearner | None = None
        self._cognitive_loop: CognitiveLoop | None = None
        if use_adaptive:
            self._init_adaptive()

    def _init_adaptive(self) -> None:
        """初始化可学习参数+认知闭环。"""
        self._param_space = ParamSpace("living_arch")
        self._param_space.declare("memory_budget_mb", 500.0, 100.0, 2000.0, lr=5.0)
        self._param_space.declare("cpu_budget", 10.0, 2.0, 50.0, lr=0.5)
        self._param_space.declare("eviction_threshold", 0.15, 0.05, 0.4, lr=0.01)
        self._param_space.declare("vc_ratio_threshold", 0.5, 0.2, 0.8, lr=0.01)
        self._param_space.declare("reborn_importance_threshold", 0.5, 0.2, 0.8, lr=0.01)
        self._param_learner = ParamLearner(self._param_space)
        self._cognitive_loop = CognitiveLoop(self._agent_id)

    def enable_adaptive(self) -> None:
        """运行时启用自适应架构。"""
        if not self._use_adaptive:
            self._use_adaptive = True
            self._init_adaptive()

    def register_module(
        self,
        name: str,
        role: ModuleRole = ModuleRole.COGNITIVE,
        cpu_weight: float = 0.5,
        memory_mb: float = 10.0,
        fitness: float = 0.5,
    ) -> ModuleVitals:
        """注册模块到活架构。"""
        vitals = ModuleVitals(
            module_name=name,
            role=role,
            cpu_weight=cpu_weight,
            memory_mb=memory_mb,
            fitness_score=fitness,
        )
        self._modules[name] = vitals
        return vitals

    def register_default_modules(self) -> None:
        """注册AutoAI的37个模块。"""
        modules = [
            ("layered_memory", ModuleRole.CORE, 1.0, 50.0, 0.9),
            ("mesh", ModuleRole.SOCIAL, 0.8, 30.0, 0.8),
            ("mcp", ModuleRole.INFRASTRUCTURE, 0.5, 20.0, 0.7),
            ("evolution", ModuleRole.COGNITIVE, 1.0, 40.0, 0.85),
            ("safety_intuition", ModuleRole.CORE, 0.5, 15.0, 0.95),
            ("wasm_runtime", ModuleRole.INFRASTRUCTURE, 0.7, 25.0, 0.7),
            ("telemetry", ModuleRole.INFRASTRUCTURE, 0.3, 10.0, 0.8),
            ("reasoning", ModuleRole.COGNITIVE, 0.8, 20.0, 0.85),
            ("event_sourcing", ModuleRole.INFRASTRUCTURE, 0.5, 30.0, 0.75),
            ("governance", ModuleRole.CORE, 0.3, 10.0, 0.95),
            ("local_model_matrix", ModuleRole.INFRASTRUCTURE, 0.5, 15.0, 0.7),
            ("dream_engine", ModuleRole.COGNITIVE, 0.6, 20.0, 0.6),
            ("continuous_autonomy", ModuleRole.CORE, 0.2, 5.0, 0.9),
            ("goal_emergence", ModuleRole.COGNITIVE, 0.5, 10.0, 0.7),
            ("self_awareness", ModuleRole.COGNITIVE, 0.4, 10.0, 0.8),
            ("causal_reasoning", ModuleRole.COGNITIVE, 0.7, 15.0, 0.75),
            ("evolution_pressure", ModuleRole.COGNITIVE, 0.5, 10.0, 0.65),
            ("tool_creation", ModuleRole.COGNITIVE, 0.6, 15.0, 0.7),
            ("meta_cognition", ModuleRole.COGNITIVE, 0.3, 5.0, 0.8),
            ("protocol_evolution", ModuleRole.INFRASTRUCTURE, 0.3, 5.0, 0.6),
            ("value_alignment", ModuleRole.CORE, 0.2, 5.0, 0.95),
            ("world_model", ModuleRole.COGNITIVE, 0.6, 15.0, 0.75),
            ("bootstrap", ModuleRole.COGNITIVE, 0.4, 10.0, 0.65),
            ("knowledge_graph", ModuleRole.COGNITIVE, 0.8, 25.0, 0.8),
            ("semantic_compressor", ModuleRole.COGNITIVE, 0.4, 10.0, 0.7),
            ("cross_domain", ModuleRole.COGNITIVE, 0.5, 10.0, 0.65),
            ("belief_system", ModuleRole.COGNITIVE, 0.3, 8.0, 0.8),
            ("immune_system", ModuleRole.CORE, 0.5, 15.0, 0.85),
            ("antifragile", ModuleRole.CORE, 0.4, 10.0, 0.8),
            ("tech_darwin", ModuleRole.COGNITIVE, 0.3, 8.0, 0.7),
            ("reproduction", ModuleRole.COGNITIVE, 0.5, 12.0, 0.65),
            ("self_optimize", ModuleRole.CORE, 0.3, 8.0, 0.8),
            ("living_ui", ModuleRole.COGNITIVE, 0.5, 15.0, 0.7),
            ("living_arch", ModuleRole.CORE, 0.3, 8.0, 0.75),
            ("identity", ModuleRole.CORE, 0.2, 5.0, 0.8),
            ("semantic_router", ModuleRole.INFRASTRUCTURE, 0.4, 10.0, 0.7),
            ("forever_loop", ModuleRole.CORE, 0.2, 5.0, 0.9),
        ]
        for name, role, cpu, mem, fitness in modules:
            self.register_module(name, role, cpu, mem, fitness)

    def rebalance(self, context: dict[str, Any] | None = None) -> list[ArchMutation]:
        """重平衡: 根据当前条件决定架构应该是什么样。"""
        self._rebalance_count += 1
        mutations = []
        if self._use_adaptive and self._param_space:
            mem_budget = self._param_space.get("memory_budget_mb")
            cpu_budget = self._param_space.get("cpu_budget")
            eviction_t = self._param_space.get("eviction_threshold")
            vc_ratio_t = self._param_space.get("vc_ratio_threshold")
            reborn_t = self._param_space.get("reborn_importance_threshold")
        else:
            mem_budget = self._memory_budget_mb
            cpu_budget = self._cpu_budget
            eviction_t = 0.15
            vc_ratio_t = 0.5
            reborn_t = 0.5
        total_memory = sum(
            m.memory_mb for m in self._modules.values()
            if m.state == ModuleState.ACTIVE
        )
        total_cpu = sum(
            m.cpu_weight for m in self._modules.values()
            if m.state == ModuleState.ACTIVE
        )
        over_memory = total_memory > mem_budget
        over_cpu = total_cpu > cpu_budget
        for name, vitals in self._modules.items():
            if vitals.role == ModuleRole.CORE:
                if vitals.state != ModuleState.ACTIVE:
                    old = vitals.state
                    vitals.transition_to(ModuleState.ACTIVE)
                    mutations.append(ArchMutation(
                        mutation_id=f"mut_{len(self._mutations)}",
                        operation="activate_core",
                        target=name,
                        before_state=old,
                        after_state=ModuleState.ACTIVE,
                        reason="核心模块必须活跃",
                    ))
                continue
            if vitals.state == ModuleState.ACTIVE:
                if vitals.importance < eviction_t or not vitals.should_exist:
                    old = vitals.state
                    vitals.transition_to(ModuleState.DORMANT)
                    mutations.append(ArchMutation(
                        mutation_id=f"mut_{len(self._mutations)}",
                        operation="evict",
                        target=name,
                        before_state=old,
                        after_state=ModuleState.DORMANT,
                        reason=f"importance={vitals.importance:.2f} < threshold={eviction_t:.2f}",
                    ))
                elif over_memory and vitals.value_cost_ratio < vc_ratio_t:
                    old = vitals.state
                    vitals.transition_to(ModuleState.DORMANT)
                    mutations.append(ArchMutation(
                        mutation_id=f"mut_{len(self._mutations)}",
                        operation="memory_pressure_evict",
                        target=name,
                        before_state=old,
                        after_state=ModuleState.DORMANT,
                        reason=f"内存压力, v/c={vitals.value_cost_ratio:.2f} < {vc_ratio_t:.2f}",
                    ))
            elif vitals.state == ModuleState.DORMANT:
                if vitals.should_exist and not over_memory:
                    old = vitals.state
                    vitals.transition_to(ModuleState.REBORN)
                    mutations.append(ArchMutation(
                        mutation_id=f"mut_{len(self._mutations)}",
                        operation="reborn",
                        target=name,
                        before_state=old,
                        after_state=ModuleState.REBORN,
                        reason="条件满足，重新激活",
                    ))
                    vitals.transition_to(ModuleState.ACTIVE)
            elif vitals.state == ModuleState.EVICTED:
                if vitals.importance > reborn_t and not over_memory:
                    old = vitals.state
                    vitals.transition_to(ModuleState.REBORN)
                    mutations.append(ArchMutation(
                        mutation_id=f"mut_{len(self._mutations)}",
                        operation="reborn_from_evicted",
                        target=name,
                        before_state=old,
                        after_state=ModuleState.REBORN,
                        reason="重要性回升",
                    ))
                    vitals.transition_to(ModuleState.ACTIVE)
        self._mutations.extend(mutations)
        if self._use_adaptive and self._cognitive_loop and self._param_learner:
            efficiency = sum(m.importance for m in self._modules.values() if m.state == ModuleState.ACTIVE) / max(sum(m.cost for m in self._modules.values() if m.state == ModuleState.ACTIVE), 0.01)
            self._param_learner.receive_feedback(min(1.0, efficiency / 2.0))
            if self._param_space:
                for m in self._modules.values():
                    m._importance_weights = {
                        "fitness": self._param_space.get("eviction_threshold") + 0.15,
                        "recency": 0.25,
                        "access": 0.2,
                        "risk": 0.15,
                        "deps": 0.1,
                    }
        return mutations

    def fuse_modules(self, module_a: str, module_b: str, fused_name: str) -> ArchMutation | None:
        """融合: 两个模块合并为一个。"""
        a = self._modules.get(module_a)
        b = self._modules.get(module_b)
        if not a or not b:
            return None
        if a.role == ModuleRole.CORE or b.role == ModuleRole.CORE:
            return None
        a.transition_to(ModuleState.FUSED)
        b.transition_to(ModuleState.FUSED)
        fused = ModuleVitals(
            module_name=fused_name,
            role=ModuleRole.COGNITIVE,
            cpu_weight=a.cpu_weight + b.cpu_weight * 0.7,
            memory_mb=a.memory_mb + b.memory_mb * 0.7,
            fitness_score=max(a.fitness_score, b.fitness_score),
            dependency_count=a.dependency_count + b.dependency_count,
        )
        self._modules[fused_name] = fused
        mutation = ArchMutation(
            mutation_id=f"mut_{len(self._mutations)}",
            operation="fuse",
            target=fused_name,
            before_state=ModuleState.ACTIVE,
            after_state=ModuleState.ACTIVE,
            reason=f"{module_a}+{module_b}融合为{fused_name}",
        )
        self._mutations.append(mutation)
        return mutation

    def split_module(self, module_name: str, split_names: list[str]) -> list[ArchMutation]:
        """裂变: 一个模块分裂为多个。"""
        original = self._modules.get(module_name)
        if not original:
            return []
        original.transition_to(ModuleState.SPLIT)
        mutations = []
        per_cpu = original.cpu_weight / len(split_names)
        per_mem = original.memory_mb / len(split_names)
        per_fitness = original.fitness_score
        for name in split_names:
            new_mod = ModuleVitals(
                module_name=name,
                role=original.role,
                cpu_weight=per_cpu,
                memory_mb=per_mem,
                fitness_score=per_fitness,
            )
            self._modules[name] = new_mod
            mutation = ArchMutation(
                mutation_id=f"mut_{len(self._mutations)}",
                operation="split",
                target=name,
                before_state=ModuleState.EMBRYO,
                after_state=ModuleState.ACTIVE,
                reason=f"从{module_name}裂变",
            )
            self._mutations.append(mutation)
            mutations.append(mutation)
        return mutations

    def snapshot(self) -> ArchSnapshot:
        """架构快照。"""
        active = [n for n, m in self._modules.items() if m.state == ModuleState.ACTIVE]
        dormant = [n for n, m in self._modules.items() if m.state == ModuleState.DORMANT]
        evicted = [n for n, m in self._modules.items() if m.state in (ModuleState.EVICTED, ModuleState.FUSED, ModuleState.SPLIT)]
        total_cost = sum(m.cost for m in self._modules.values() if m.state == ModuleState.ACTIVE)
        total_importance = sum(m.importance for m in self._modules.values() if m.state == ModuleState.ACTIVE)
        snap = ArchSnapshot(
            active_modules=active,
            dormant_modules=dormant,
            evicted_modules=evicted,
            total_modules=len(self._modules),
            total_cost=total_cost,
            total_importance=total_importance,
        )
        self._snapshots.append(snap)
        return snap

    def update_vitals(self, module_name: str, **kwargs: Any) -> None:
        vitals = self._modules.get(module_name)
        if not vitals:
            return
        for k, v in kwargs.items():
            if hasattr(vitals, k):
                setattr(vitals, k, v)

    @property
    def stats(self) -> dict[str, Any]:
        active = [n for n, m in self._modules.items() if m.state == ModuleState.ACTIVE]
        dormant = [n for n, m in self._modules.items() if m.state == ModuleState.DORMANT]
        return {
            "agent_id": self._agent_id,
            "total_modules": len(self._modules),
            "active": len(active),
            "dormant": len(dormant),
            "rebalance_count": self._rebalance_count,
            "mutation_count": len(self._mutations),
            "memory_budget_mb": self._memory_budget_mb,
            "cpu_budget": self._cpu_budget,
            "active_list": active[:10],
        }
