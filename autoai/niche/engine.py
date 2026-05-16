"""生态位计算引擎: Agent在能力空间中的生态位定位、竞争分析与生态演替。"""

from __future__ import annotations

import math
import random
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
from autoai.autonomy_core.real_executor import RealExecutor
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class CapabilityAxis(Enum):
    REASONING = "reasoning"
    PERCEPTION = "perception"
    ACTION = "action"
    COMMUNICATION = "communication"
    MEMORY = "memory"
    LEARNING = "learning"
    CREATIVITY = "creativity"
    RESILIENCE = "resilience"
    AUTONOMY = "autonomy"
    COLLABORATION = "collaboration"


@dataclass
class CapabilityVector:
    """能力向量: Agent在各轴上的能力值。"""
    values: dict[CapabilityAxis, float] = field(default_factory=dict)

    def __post_init__(self):
        for axis in CapabilityAxis:
            self.values.setdefault(axis, 0.0)

    def magnitude(self) -> float:
        return math.sqrt(sum(v * v for v in self.values.values()))

    def dot(self, other: CapabilityVector) -> float:
        return sum(self.values[a] * other.values[a] for a in CapabilityAxis)

    def cosine_similarity(self, other: CapabilityVector) -> float:
        m1, m2 = self.magnitude(), other.magnitude()
        if m1 < 1e-9 or m2 < 1e-9:
            return 0.0
        return self.dot(other) / (m1 * m2)

    def distance(self, other: CapabilityVector) -> float:
        return math.sqrt(sum((self.values[a] - other.values[a]) ** 2 for a in CapabilityAxis))

    def project(self, axis: CapabilityAxis) -> float:
        return self.values.get(axis, 0.0)


@dataclass
class NicheProfile:
    """生态位轮廓: Agent在生态中的完整定位。"""
    agent_id: str
    capability: CapabilityVector = field(default_factory=CapabilityVector)
    resource_footprint: float = 0.5
    access_patterns: dict[str, float] = field(default_factory=dict)
    fitness_score: float = 0.0
    niche_width: float = 0.0
    competitors: list[str] = field(default_factory=list)
    symbionts: list[str] = field(default_factory=list)
    ecological_role: str = "generalist"

    @property
    def dominance(self) -> float:
        return self.capability.magnitude() * self.resource_footprint

    @property
    def specialization(self) -> float:
        vals = list(self.capability.values.values())
        if not vals or sum(vals) < 1e-9:
            return 0.0
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        return min(1.0, math.sqrt(variance) * 2.0)


class EcologicalRole(Enum):
    KEYSTONE = "keystone"
    GENERALIST = "generalist"
    SPECIALIST = "specialist"
    PIONEER = "pioneer"
    DECOMPOSER = "decomposer"
    SYMBIONT = "symbiont"


class NicheEngine(FullAutonomyMixin):
    """生态位计算引擎: 计算Agent在能力生态中的定位、竞争、共生与演替。"""

    def __init__(self, use_learnable: bool = False):
        self._init_full_autonomy()
        self._profiles: dict[str, NicheProfile] = {}
        self._interaction_matrix: dict[tuple[str, str], float] = {}
        self._succession_history: list[dict[str, Any]] = []
        self._tick_count: int = 0
        self._use_learnable = use_learnable
        self._param_space: ParamSpace | None = None
        self._param_learner: ParamLearner | None = None
        self._real_executor: RealExecutor | None = None
        if use_learnable:
            self._init_learnable()

    def _init_learnable(self) -> None:
        self._param_space = ParamSpace("niche")
        self._param_space.declare("overlap_similarity_weight", 0.7, 0.3, 0.9, lr=0.01)
        self._param_space.declare("overlap_resource_weight", 0.3, 0.1, 0.7, lr=0.01)
        self._param_space.declare("competition_fitness_factor", 0.5, 0.1, 0.9, lr=0.01)
        self._param_space.declare("symbiosis_overlap_penalty", 0.5, 0.1, 0.9, lr=0.01)
        self._param_space.declare("keystone_dominance_threshold", 0.7, 0.4, 0.9, lr=0.01)
        self._param_space.declare("fitness_weight_dominance", 0.6, 0.3, 0.8, lr=0.01)
        self._param_space.declare("fitness_weight_specialization", 0.2, 0.05, 0.5, lr=0.01)
        self._param_space.declare("fitness_weight_niche_width", 0.2, 0.05, 0.5, lr=0.01)
        self._param_learner = ParamLearner(self._param_space)
        self._real_executor = RealExecutor()

    def enable_learnable(self) -> None:
        if not self._use_learnable:
            self._use_learnable = True
            self._init_learnable()

    def register(self, agent_id: str, capability: CapabilityVector | None = None, resource_footprint: float = 0.5) -> NicheProfile:
        cap = capability or CapabilityVector()
        profile = NicheProfile(agent_id=agent_id, capability=cap, resource_footprint=resource_footprint)
        self._profiles[agent_id] = profile
        return profile

    def update_capability(self, agent_id: str, axis: CapabilityAxis, value: float) -> bool:
        profile = self._profiles.get(agent_id)
        if not profile:
            return False
        profile.capability.values[axis] = max(0.0, min(1.0, value))
        return True

    def compute_niche_overlap(self, id_a: str, id_b: str) -> float:
        """计算两个Agent的生态位重叠度(0~1)。"""
        pa, pb = self._profiles.get(id_a), self._profiles.get(id_b)
        if not pa or not pb:
            return 0.0
        similarity = pa.capability.cosine_similarity(pb.capability)
        resource_overlap = min(pa.resource_footprint, pb.resource_footprint) / max(pa.resource_footprint, pb.resource_footprint, 1e-9)
        sim_w = 0.7
        res_w = 0.3
        if self._use_learnable and self._param_space:
            sim_w = self._param_space.get("overlap_similarity_weight")
            res_w = self._param_space.get("overlap_resource_weight")
        return similarity * sim_w + resource_overlap * res_w

    def compute_competition(self, id_a: str, id_b: str) -> float:
        """竞争强度: 高重叠 + 相近能力 = 高竞争。"""
        overlap = self.compute_niche_overlap(id_a, id_b)
        pa, pb = self._profiles.get(id_a), self._profiles.get(id_b)
        if not pa or not pb:
            return 0.0
        fitness_diff = abs(pa.fitness_score - pb.fitness_score)
        fit_factor = 0.5
        if self._use_learnable and self._param_space:
            fit_factor = self._param_space.get("competition_fitness_factor")
        return overlap * (1.0 - fitness_diff * fit_factor)

    def compute_symbiosis(self, id_a: str, id_b: str) -> float:
        """共生潜力: 互补能力 = 高共生。"""
        pa, pb = self._profiles.get(id_a), self._profiles.get(id_b)
        if not pa or not pb:
            return 0.0
        complementarity = 0.0
        for axis in CapabilityAxis:
            va, vb = pa.capability.values[axis], pb.capability.values[axis]
            complementarity += va * (1.0 - vb) + vb * (1.0 - va)
        complementarity /= (2.0 * len(CapabilityAxis))
        overlap = self.compute_niche_overlap(id_a, id_b)
        overlap_penalty = 0.5
        if self._use_learnable and self._param_space:
            overlap_penalty = self._param_space.get("symbiosis_overlap_penalty")
        return complementarity * (1.0 - overlap * overlap_penalty)

    def assign_ecological_roles(self) -> dict[str, str]:
        """为所有Agent分配生态角色。"""
        roles: dict[str, str] = {}
        for aid, profile in self._profiles.items():
            overlaps = [self.compute_niche_overlap(aid, other) for other in self._profiles if other != aid]
            avg_overlap = sum(overlaps) / max(len(overlaps), 1)
            symbioses = [self.compute_symbiosis(aid, other) for other in self._profiles if other != aid]
            max_symbiosis = max(symbioses) if symbioses else 0.0
            competitions = [self.compute_competition(aid, other) for other in self._profiles if other != aid]
            max_competition = max(competitions) if competitions else 0.0
            keystone_t = 0.7
            if self._use_learnable and self._param_space:
                keystone_t = self._param_space.get("keystone_dominance_threshold")
            if profile.dominance > keystone_t and avg_overlap > 0.5:
                role = EcologicalRole.KEYSTONE.value
            elif profile.specialization > 0.6:
                role = EcologicalRole.SPECIALIST.value
            elif max_symbiosis > 0.5 and max_competition < 0.3:
                role = EcologicalRole.SYMBIONT.value
            elif profile.capability.magnitude() < 0.3:
                role = EcologicalRole.DECOMPOSER.value
            elif avg_overlap < 0.3 and profile.capability.magnitude() > 0.4:
                role = EcologicalRole.PIONEER.value
            else:
                role = EcologicalRole.GENERALIST.value
            profile.ecological_role = role
            roles[aid] = role
        return roles

    def compute_niche_width(self, agent_id: str) -> float:
        """生态位宽度: Levins公式 BW = 1/sum(p_i^2)。"""
        profile = self._profiles.get(agent_id)
        if not profile:
            return 0.0
        vals = [v for v in profile.capability.values.values() if v > 0]
        if not vals:
            return 0.0
        total = sum(vals)
        if total < 1e-9:
            return 0.0
        proportions = [v / total for v in vals]
        bw = 1.0 / sum(p * p for p in proportions)
        max_bw = len(vals)
        profile.niche_width = bw / max_bw if max_bw > 0 else 0.0
        return profile.niche_width

    def find_optimal_niche(self, agent_id: str) -> dict[str, Any]:
        """寻找最优生态位: 当前Agent应发展的能力轴。"""
        profile = self._profiles.get(agent_id)
        if not profile:
            return {}
        development_priorities: list[tuple[CapabilityAxis, float]] = []
        for axis in CapabilityAxis:
            current = profile.capability.values[axis]
            gap = 1.0 - current
            competing_better = sum(
                1 for other in self._profiles.values()
                if other.agent_id != agent_id and other.capability.values[axis] > current
            )
            competition_penalty = competing_better * 0.1
            symbiotic_bonus = sum(
                self.compute_symbiosis(agent_id, other.agent_id) * other.capability.values[axis]
                for other in self._profiles.values() if other.agent_id != agent_id
            ) * 0.2
            priority = gap * (1.0 - competition_penalty) + symbiotic_bonus
            development_priorities.append((axis, priority))
        development_priorities.sort(key=lambda x: x[1], reverse=True)
        w_dom, w_spec, w_nw = 0.6, 0.2, 0.2
        if self._use_learnable and self._param_space:
            w_dom = self._param_space.get("fitness_weight_dominance")
            w_spec = self._param_space.get("fitness_weight_specialization")
            w_nw = self._param_space.get("fitness_weight_niche_width")
        profile.fitness_score = profile.dominance * w_dom + profile.specialization * w_spec + profile.niche_width * w_nw
        return {
            "agent_id": agent_id,
            "current_fitness": profile.fitness_score,
            "development_priorities": [(a.value, round(p, 3)) for a, p in development_priorities[:5]],
            "ecological_role": profile.ecological_role,
            "dominance": round(profile.dominance, 3),
            "specialization": round(profile.specialization, 3),
        }

    def detect_succession(self) -> list[dict[str, Any]]:
        """检测生态演替: 一个Agent替代另一个的趋势。"""
        successions = []
        for aid, profile in self._profiles.items():
            for other_id, other in self._profiles.items():
                if aid == other_id:
                    continue
                overlap = self.compute_niche_overlap(aid, other_id)
                if overlap < 0.5:
                    continue
                if profile.fitness_score <= other.fitness_score:
                    continue
                displacement = (profile.fitness_score - other.fitness_score) * overlap
                if displacement > 0.1:
                    successions.append({
                        "challenger": aid,
                        "incumbent": other_id,
                        "overlap": round(overlap, 3),
                        "displacement": round(displacement, 3),
                    })
        if successions:
            self._succession_history.append({"tick": self._tick_count, "successions": successions})
        return successions

    def tick(self) -> dict[str, Any]:
        """生态位演化的一个时间步。"""
        self._tick_count += 1
        for aid in self._profiles:
            self.compute_niche_width(aid)
        roles = self.assign_ecological_roles()
        successions = self.detect_succession()
        for aid, profile in self._profiles.items():
            w_dom, w_spec, w_nw = 0.6, 0.2, 0.2
            if self._use_learnable and self._param_space:
                w_dom = self._param_space.get("fitness_weight_dominance")
                w_spec = self._param_space.get("fitness_weight_specialization")
                w_nw = self._param_space.get("fitness_weight_niche_width")
            profile.fitness_score = profile.dominance * w_dom + profile.specialization * w_spec + profile.niche_width * w_nw
            competitors = []
            symbionts = []
            for other_id in self._profiles:
                if other_id == aid:
                    continue
                if self.compute_competition(aid, other_id) > 0.3:
                    competitors.append(other_id)
                if self.compute_symbiosis(aid, other_id) > 0.4:
                    symbionts.append(other_id)
            profile.competitors = competitors
            profile.symbionts = symbionts
        return {
            "tick": self._tick_count,
            "agents": len(self._profiles),
            "roles": roles,
            "successions": successions,
            "avg_fitness": sum(p.fitness_score for p in self._profiles.values()) / max(len(self._profiles), 1),
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "tick_count": self._tick_count,
            "agent_count": len(self._profiles),
            "succession_events": len(self._succession_history),
            "roles": {p.ecological_role: sum(1 for q in self._profiles.values() if q.ecological_role == p.ecological_role) for p in self._profiles.values()},
            "avg_fitness": sum(p.fitness_score for p in self._profiles.values()) / max(len(self._profiles), 1),
            "avg_dominance": sum(p.dominance for p in self._profiles.values()) / max(len(self._profiles), 1),
        }
