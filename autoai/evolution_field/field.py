"""统一自进化场: 所有能力融为一个连续场。"""

from __future__ import annotations

import time
import math
import random
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
from autoai.autonomy_core.cognitive_loop import CognitiveLoop
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class FieldState(Enum):
    GROUND = "ground"
    EXCITED = "excited"
    SUPERNOVA = "supernova"
    DECAYED = "decayed"
    ENTANGLED = "entangled"


@dataclass
class FieldNode:
    """场节点: 模块在场中的表示。"""
    node_id: str
    module_name: str
    energy: float = 0.5
    coupling_strengths: dict[str, float] = field(default_factory=dict)
    state: FieldState = FieldState.GROUND
    excitation_history: list[float] = field(default_factory=list)
    last_excitation: float = 0.0
    resonance_freq: float = 1.0

    @property
    def is_active(self) -> bool:
        return self.energy > 0.1 and self.state not in (FieldState.DECAYED,)

    @property
    def field_potential(self) -> float:
        coupling_energy = sum(self.coupling_strengths.values()) / max(len(self.coupling_strengths), 1)
        return self.energy * (1.0 + coupling_energy)

    def excite(self, delta: float) -> None:
        self.energy = min(1.0, self.energy + delta)
        self.last_excitation = time.time()
        self.excitation_history.append(self.energy)
        if len(self.excitation_history) > 100:
            self.excitation_history = self.excitation_history[-100:]
        if self.energy > 0.9:
            self.state = FieldState.SUPERNOVA
        elif self.energy > 0.3:
            self.state = FieldState.EXCITED
        else:
            self.state = FieldState.GROUND

    def decay(self, rate: float = 0.01) -> None:
        self.energy *= (1.0 - rate)
        if self.energy < 0.05:
            self.state = FieldState.DECAYED
        elif self.energy < 0.3:
            self.state = FieldState.GROUND


@dataclass
class FieldPulse:
    """场脉冲: 能量在模块间传播。"""
    source_id: str
    target_id: str
    energy: float
    propagation_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


class EvolutionField(FullAutonomyMixin):
    """统一自进化场: 连续能量场驱动所有模块。"""

    def __init__(self, field_id: str = "default", use_learnable: bool = False):
        self._init_full_autonomy()
        self._field_id = field_id
        self._nodes: dict[str, FieldNode] = {}
        self._pulses: list[FieldPulse] = []
        self._total_energy: float = 0.0
        self._tick_count: int = 0
        self._decay_rate: float = 0.005
        self._coupling_threshold: float = 0.3
        self._entanglement_map: dict[frozenset, float] = {}
        self._use_learnable = use_learnable
        self._param_space: ParamSpace | None = None
        self._param_learner: ParamLearner | None = None
        self._cognitive_loop: CognitiveLoop | None = None
        if use_learnable:
            self._init_learnable()

    def _init_learnable(self) -> None:
        self._param_space = ParamSpace("evolution_field")
        self._param_space.declare("decay_rate", 0.005, 0.001, 0.05, lr=0.001)
        self._param_space.declare("coupling_threshold", 0.3, 0.1, 0.7, lr=0.01)
        self._param_space.declare("propagation_factor", 0.01, 0.001, 0.1, lr=0.001)
        self._param_space.declare("entanglement_threshold", 0.8, 0.5, 0.95, lr=0.01)
        self._param_space.declare("supernova_threshold", 0.9, 0.7, 0.99, lr=0.005)
        self._param_space.declare("excited_threshold", 0.3, 0.1, 0.6, lr=0.01)
        self._param_learner = ParamLearner(self._param_space)
        self._cognitive_loop = CognitiveLoop(self._field_id)

    def enable_learnable(self) -> None:
        if not self._use_learnable:
            self._use_learnable = True
            self._init_learnable()

    def add_node(self, module_name: str, initial_energy: float = 0.5) -> FieldNode:
        node = FieldNode(
            node_id=f"fn_{module_name}",
            module_name=module_name,
            energy=initial_energy,
        )
        self._nodes[module_name] = node
        return node

    def add_default_nodes(self) -> None:
        modules = [
            ("safety_intuition", 0.95), ("governance", 0.9), ("value_alignment", 0.9),
            ("continuous_autonomy", 0.85), ("immune_system", 0.8), ("antifragile", 0.75),
            ("evolution", 0.8), ("self_optimize", 0.8), ("meta_cognition", 0.75),
            ("reasoning", 0.7), ("knowledge_graph", 0.7), ("belief_system", 0.7),
            ("causal_reasoning", 0.65), ("world_model", 0.65), ("goal_emergence", 0.6),
            ("dream_engine", 0.5), ("evolution_pressure", 0.5), ("tool_creation", 0.5),
            ("living_arch", 0.6), ("identity_flux", 0.55), ("semantic_router", 0.5),
            ("forever_loop", 0.7), ("self_heal", 0.65), ("self_test", 0.5),
            ("self_doc", 0.4), ("self_upgrade", 0.5), ("reproduction", 0.45),
            ("tech_darwin", 0.5), ("chaos", 0.6), ("knowledge", 0.6),
            ("mesh", 0.7), ("memory", 0.7), ("mcp", 0.5),
        ]
        for name, energy in modules:
            self.add_node(name, energy)
        self._auto_couple()

    def _auto_couple(self) -> None:
        """自动耦合: 基于模块名相似度建立场耦合。"""
        couplings = {
            ("safety_intuition", "immune_system", 0.9),
            ("safety_intuition", "value_alignment", 0.8),
            ("governance", "value_alignment", 0.85),
            ("evolution", "evolution_pressure", 0.8),
            ("evolution", "tech_darwin", 0.7),
            ("evolution", "self_upgrade", 0.75),
            ("reasoning", "causal_reasoning", 0.8),
            ("reasoning", "meta_cognition", 0.7),
            ("knowledge_graph", "belief_system", 0.7),
            ("knowledge_graph", "causal_reasoning", 0.6),
            ("knowledge_graph", "dream_engine", 0.5),
            ("goal_emergence", "self_awareness", 0.7),
            ("goal_emergence", "evolution_pressure", 0.6),
            ("immune_system", "antifragile", 0.85),
            ("self_optimize", "meta_cognition", 0.7),
            ("self_optimize", "forever_loop", 0.6),
            ("living_arch", "self_optimize", 0.65),
            ("identity_flux", "mesh", 0.5),
            ("semantic_router", "mesh", 0.6),
            ("self_heal", "immune_system", 0.7),
            ("self_test", "self_heal", 0.6),
            ("self_doc", "self_test", 0.5),
            ("self_upgrade", "tech_darwin", 0.7),
            ("reproduction", "evolution", 0.6),
            ("reproduction", "identity_flux", 0.5),
            ("chaos", "antifragile", 0.85),
            ("dream_engine", "knowledge_graph", 0.5),
            ("world_model", "causal_reasoning", 0.7),
            ("world_model", "self_optimize", 0.5),
            ("continuous_autonomy", "living_arch", 0.6),
        }
        for a, b, strength in couplings:
            if a in self._nodes and b in self._nodes:
                self._nodes[a].coupling_strengths[b] = strength
                self._nodes[b].coupling_strengths[a] = strength

    def tick(self) -> dict[str, Any]:
        """场演化的一个时间步: 衰减->传播->激发->纠缠检查。"""
        self._tick_count += 1
        decay = self._decay_rate
        if self._use_learnable and self._param_space:
            decay = self._param_space.get("decay_rate")
        for node in self._nodes.values():
            node.decay(decay)
        self._propagate_energy()
        self._check_entanglement()
        self._total_energy = sum(n.energy for n in self._nodes.values())
        if self._use_learnable and self._param_learner and self._cognitive_loop:
            efficiency = self._total_energy / max(len(self._nodes), 1)
            self._param_learner.receive_feedback(efficiency)
        return {
            "tick": self._tick_count,
            "total_energy": self._total_energy,
            "active_nodes": sum(1 for n in self._nodes.values() if n.is_active),
            "supernova": sum(1 for n in self._nodes.values() if n.state == FieldState.SUPERNOVA),
            "entanglements": len(self._entanglement_map),
        }

    def _propagate_energy(self) -> None:
        """能量沿耦合传播。"""
        prop_factor = 0.01
        if self._use_learnable and self._param_space:
            prop_factor = self._param_space.get("propagation_factor")
        for name, node in self._nodes.items():
            if not node.is_active:
                continue
            for coupled_name, strength in node.coupling_strengths.items():
                coupled = self._nodes.get(coupled_name)
                if not coupled:
                    continue
                delta = node.energy * strength * prop_factor
                coupled.excite(delta)
                if delta > 0.001:
                    self._pulses.append(FieldPulse(
                        source_id=name,
                        target_id=coupled_name,
                        energy=delta,
                    ))

    def _check_entanglement(self) -> None:
        """检查量子纠缠: 强耦合的模块对可视为纠缠。"""
        entangle_t = 0.8
        if self._use_learnable and self._param_space:
            entangle_t = self._param_space.get("entanglement_threshold")
        for name, node in self._nodes.items():
            for coupled_name, strength in node.coupling_strengths.items():
                if strength > entangle_t:
                    key = frozenset({name, coupled_name})
                    self._entanglement_map[key] = strength
                    if name in self._nodes:
                        self._nodes[name].state = FieldState.ENTANGLED

    def inject(self, module_name: str, energy: float) -> bool:
        """向场中注入能量(外部刺激)。"""
        node = self._nodes.get(module_name)
        if not node:
            return False
        node.excite(energy)
        return True

    def query_field(self) -> dict[str, float]:
        """查询场状态: 每个模块的当前能量。"""
        return {name: node.energy for name, node in self._nodes.items()}

    def query_hotspots(self, threshold: float = 0.7) -> list[tuple[str, float]]:
        """查询能量热点。"""
        hotspots = [
            (name, node.energy)
            for name, node in self._nodes.items()
            if node.energy >= threshold
        ]
        hotspots.sort(key=lambda x: x[1], reverse=True)
        return hotspots

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "field_id": self._field_id,
            "tick_count": self._tick_count,
            "total_energy": self._total_energy,
            "node_count": len(self._nodes),
            "active_nodes": sum(1 for n in self._nodes.values() if n.is_active),
            "pulse_count": len(self._pulses),
            "entanglement_count": len(self._entanglement_map),
            "avg_energy": self._total_energy / len(self._nodes) if self._nodes else 0.0,
        }
