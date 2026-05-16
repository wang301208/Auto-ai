"""身份流变: Agent身份的演化、融合、消解。"""

from __future__ import annotations

import time
import hashlib
import random
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.learnable_params import ParamSpace
from autoai.autonomy_core.reasoning_decider import ReasoningDecider, DecisionContext, DecisionVerdict
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class IdentityState(Enum):
    EMBRYONIC = "embryonic"
    AWAKENING = "awakening"
    MATURE = "mature"
    TRANSCENDENT = "transcendent"
    FUSED = "fused"
    DISSOLVED = "dissolved"


@dataclass
class AgentIdentity:
    """Agent身份: 不是固定的，是当前状态的投影。"""
    identity_id: str
    name: str
    state: IdentityState = IdentityState.EMBRYONIC
    capabilities: set[str] = field(default_factory=set)
    core_values: set[str] = field(default_factory=set)
    beliefs_fingerprint: str = ""
    fitness: float = 0.5
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    child_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_mutation: float = field(default_factory=time.time)
    mutation_count: int = 0

    @property
    def complexity(self) -> float:
        return min(1.0, len(self.capabilities) / 20.0) * 0.5 + self.fitness * 0.5

    @property
    def lineage_depth(self) -> int:
        return len(self.parent_ids)

    @property
    def is_alive(self) -> bool:
        return self.state not in (IdentityState.FUSED, IdentityState.DISSOLVED)

    def mutate(self, new_capabilities: set[str] | None = None, new_fitness: float | None = None) -> None:
        if new_capabilities is not None:
            self.capabilities = new_capabilities
        if new_fitness is not None:
            self.fitness = new_fitness
        self.last_mutation = time.time()
        self.mutation_count += 1

    def fingerprint(self) -> str:
        cap_str = ",".join(sorted(self.capabilities))
        val_str = ",".join(sorted(self.core_values))
        raw = f"{self.identity_id}:{cap_str}:{val_str}:{self.fitness:.2f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class FusionResult:
    """融合结果: 两个Agent融合为超Agent。"""
    super_id: str
    component_ids: list[str]
    merged_capabilities: set[str] = field(default_factory=set)
    merged_values: set[str] = field(default_factory=set)
    synergy_score: float = 0.0
    redundancy_eliminated: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_synergistic(self) -> bool:
        return self.synergy_score > 0.3


@dataclass
class IdentityDelta:
    """身份变化: 记录身份的每次变化。"""
    identity_id: str
    change_type: str
    before_fingerprint: str
    after_fingerprint: str
    description: str
    timestamp: float = field(default_factory=time.time)

    @property
    def is_significant(self) -> bool:
        return self.before_fingerprint != self.after_fingerprint


class IdentityFlux(FullAutonomyMixin):
    """身份流变引擎: Agent身份的持续演化。"""

    def __init__(self, use_reasoning: bool = False):
        self._init_full_autonomy()
        self._identities: dict[str, AgentIdentity] = {}
        self._deltas: list[IdentityDelta] = []
        self._fusions: list[FusionResult] = []
        self._dissolutions: list[str] = []
        self._use_reasoning = use_reasoning
        self._param_space: ParamSpace | None = None
        self._decider: ReasoningDecider | None = None
        if use_reasoning:
            self._init_reasoning()

    def _init_reasoning(self) -> None:
        self._param_space = ParamSpace("identity_flux")
        self._param_space.declare("mature_threshold", 0.8, 0.5, 0.95, lr=0.01)
        self._param_space.declare("transcendent_threshold", 0.95, 0.8, 0.99, lr=0.005)
        self._param_space.declare("fusion_synergy_bonus", 0.2, 0.0, 0.5, lr=0.01)
        self._decider = ReasoningDecider(self._param_space)

    def enable_reasoning(self) -> None:
        if not self._use_reasoning:
            self._use_reasoning = True
            self._init_reasoning()

    def spawn(self, name: str, capabilities: set[str] | None = None, core_values: set[str] | None = None) -> AgentIdentity:
        """诞生新身份。"""
        identity_id = f"id_{hashlib.sha256(name.encode()).hexdigest()[:8]}"
        identity = AgentIdentity(
            identity_id=identity_id,
            name=name,
            state=IdentityState.AWAKENING,
            capabilities=capabilities or set(),
            core_values=core_values or {"safety", "honesty", "autonomy"},
        )
        self._identities[identity_id] = identity
        return identity

    def evolve(self, identity_id: str, new_capabilities: set[str] | None = None, new_fitness: float | None = None) -> IdentityDelta | None:
        """身份演化。"""
        identity = self._identities.get(identity_id)
        if not identity or not identity.is_alive:
            return None
        before_fp = identity.fingerprint()
        identity.mutate(new_capabilities, new_fitness)
        after_fp = identity.fingerprint()
        if self._use_reasoning and self._param_space:
            mature_t = self._param_space.get("mature_threshold")
            transcendent_t = self._param_space.get("transcendent_threshold")
        else:
            mature_t = 0.8
            transcendent_t = 0.95
        if identity.fitness > mature_t and identity.state == IdentityState.AWAKENING:
            identity.state = IdentityState.MATURE
        elif identity.fitness > transcendent_t and identity.state == IdentityState.MATURE:
            identity.state = IdentityState.TRANSCENDENT
        delta = IdentityDelta(
            identity_id=identity_id,
            change_type="evolve",
            before_fingerprint=before_fp,
            after_fingerprint=after_fp,
            description=f"能力变化, fitness={identity.fitness:.2f}",
        )
        self._deltas.append(delta)
        return delta

    def fuse(self, id_a: str, id_b: str, super_name: str | None = None) -> FusionResult | None:
        """融合: 两个Agent合并为超Agent。"""
        a = self._identities.get(id_a)
        b = self._identities.get(id_b)
        if not a or not b or not a.is_alive or not b.is_alive:
            return None
        merged_caps = a.capabilities | b.capabilities
        merged_values = a.core_values & b.core_values
        if not merged_values:
            merged_values = {"safety", "honesty", "autonomy"}
        redundancy = len(a.capabilities & b.capabilities)
        synergy = (len(merged_caps) - len(a.capabilities) - len(b.capabilities) + redundancy)
        synergy_score = min(1.0, synergy / max(len(merged_caps), 1) + redundancy * 0.1)
        synergy_bonus = 0.2
        if self._use_reasoning and self._param_space:
            synergy_bonus = self._param_space.get("fusion_synergy_bonus")
        super_id = f"super_{a.identity_id}_{b.identity_id}"
        name = super_name or f"{a.name}+{b.name}"
        super_identity = AgentIdentity(
            identity_id=super_id,
            name=name,
            state=IdentityState.MATURE,
            capabilities=merged_caps,
            core_values=merged_values,
            fitness=max(a.fitness, b.fitness) * (1 + synergy_score * synergy_bonus),
            generation=max(a.generation, b.generation) + 1,
            parent_ids=[a.identity_id, b.identity_id],
        )
        super_identity.fitness = min(1.0, super_identity.fitness)
        self._identities[super_id] = super_identity
        a.state = IdentityState.FUSED
        b.state = IdentityState.FUSED
        a.child_ids.append(super_id)
        b.child_ids.append(super_id)
        result = FusionResult(
            super_id=super_id,
            component_ids=[id_a, id_b],
            merged_capabilities=merged_caps,
            merged_values=merged_values,
            synergy_score=synergy_score,
            redundancy_eliminated=redundancy,
        )
        self._fusions.append(result)
        logger.info(f"身份融合: {a.name}+{b.name} -> {name}, synergy={synergy_score:.2f}")
        return result

    def dissolve(self, identity_id: str, reason: str = "resource_reclaim") -> bool:
        """消解: Agent释放资源，身份存入历史。"""
        identity = self._identities.get(identity_id)
        if not identity:
            return False
        if identity.state == IdentityState.DISSOLVED:
            return False
        for child_id in identity.child_ids:
            child = self._identities.get(child_id)
            if child and child.is_alive:
                logger.warning(f"不能消解: 活跃子Agent {child_id} 依赖")
                return False
        before_fp = identity.fingerprint()
        identity.state = IdentityState.DISSOLVED
        identity.capabilities = set()
        after_fp = identity.fingerprint()
        delta = IdentityDelta(
            identity_id=identity_id,
            change_type="dissolve",
            before_fingerprint=before_fp,
            after_fingerprint=after_fp,
            description=f"消解: {reason}",
        )
        self._deltas.append(delta)
        self._dissolutions.append(identity_id)
        logger.info(f"身份消解: {identity.name}, 原因={reason}")
        return True

    def get_identity(self, identity_id: str) -> AgentIdentity | None:
        return self._identities.get(identity_id)

    def get_active_identities(self) -> list[AgentIdentity]:
        return [i for i in self._identities.values() if i.is_alive]

    @property
    def stats(self) -> dict[str, Any]:
        active = self.get_active_identities()
        return {
            "total_identities": len(self._identities),
            "active": len(active),
            "fusions": len(self._fusions),
            "dissolutions": len(self._dissolutions),
            "deltas": len(self._deltas),
            "avg_fitness": (
                sum(i.fitness for i in active) / len(active) if active else 0.0
            ),
            "max_generation": max(
                (i.generation for i in self._identities.values()), default=0
            ),
        }
