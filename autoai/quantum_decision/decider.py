from __future__ import annotations

import math
import random
import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class PathState(Enum):
    SUPERPOSED = "superposed"
    COLLAPSED = "collapsed"
    ELIMINATED = "eliminated"


@dataclass
class DecisionPath:
    action: str
    amplitude: float = 1.0
    phase: float = 0.0
    state: PathState = PathState.SUPERPOSED
    expected_value: float = 0.0
    risk: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def probability(self) -> float:
        return self.amplitude ** 2

    @property
    def is_viable(self) -> float:
        return self.state == PathState.SUPERPOSED and self.amplitude > 0.01


@dataclass
class Superposition:
    """决策叠加态: 多个可能路径同时存在。"""
    paths: list[DecisionPath] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    collapsed_to: DecisionPath | None = None

    @property
    def total_probability(self) -> float:
        return sum(p.probability for p in self.paths if p.is_viable)

    @property
    def is_normalized(self) -> bool:
        return abs(self.total_probability - 1.0) < 0.01

    def normalize(self) -> None:
        total = self.total_probability
        if total > 0:
            scale = 1.0 / math.sqrt(total)
            for p in self.paths:
                p.amplitude *= scale

    def add_path(self, path: DecisionPath) -> None:
        self.paths.append(path)
        self.normalize()

    def interfere(self) -> None:
        """路径干涉: 相位相近的路径增强，相反的抵消。"""
        for i, p1 in enumerate(self.paths):
            for j, p2 in enumerate(self.paths):
                if i >= j:
                    continue
                phase_diff = p1.phase - p2.phase
                interference = math.cos(phase_diff) * 0.1
                if interference > 0:
                    p1.amplitude *= (1.0 + interference)
                    p2.amplitude *= (1.0 + interference)
                else:
                    p1.amplitude *= (1.0 + interference)
                    p2.amplitude *= (1.0 + interference)
        for p in self.paths:
            p.amplitude = max(0.01, p.amplitude)
        self.normalize()

    def collapse(self) -> DecisionPath | None:
        """坍缩: 从叠加态中选择一个路径。"""
        viable = [p for p in self.paths if p.is_viable]
        if not viable:
            return None
        self.normalize()
        r = random.random()
        cumulative = 0.0
        selected = viable[0]
        for path in viable:
            cumulative += path.probability
            if r <= cumulative:
                selected = path
                break
        for p in self.paths:
            if p is selected:
                p.state = PathState.COLLAPSED
            else:
                p.state = PathState.ELIMINATED
        self.collapsed_to = selected
        return selected


class QuantumDecider:
    """量子决策器: 叠加→干涉→坍缩。"""

    def __init__(self):
        self._decisions: list[Superposition] = []
        self._entanglements: list[tuple[str, str, float]] = []

    def create_superposition(self, options: list[dict[str, Any]]) -> Superposition:
        """创建决策叠加态。"""
        paths = []
        for i, opt in enumerate(options):
            action = opt.get("action", f"option_{i}")
            ev = opt.get("expected_value", 0.5)
            risk = opt.get("risk", 0.5)
            phase = opt.get("phase", i * math.pi / max(1, len(options)))
            amp = math.sqrt(opt.get("probability", 1.0 / len(options)))
            paths.append(DecisionPath(
                action=action, amplitude=amp, phase=phase,
                expected_value=ev, risk=risk,
            ))
        sp = Superposition(paths=paths)
        sp.normalize()
        self._decisions.append(sp)
        return sp

    def apply_entanglement(self, dim_a: str, dim_b: str, strength: float = 0.5) -> None:
        """创建维度间纠缠。"""
        self._entanglements.append((dim_a, dim_b, strength))

    def decide(self, options: list[dict[str, Any]], use_interference: bool = True) -> DecisionPath | None:
        """完整量子决策: 叠加→干涉→坍缩。"""
        sp = self.create_superposition(options)
        if use_interference:
            sp.interfere()
        result = sp.collapse()
        if result:
            logger.info(f"量子决策坍缩: {result.action} (P={result.probability:.3f})")
        return result

    def evaluate_ev_risk(self, options: list[dict[str, Any]]) -> list[dict[str, float]]:
        """EV-Risk分析: 对每个选项计算期望值和风险。"""
        results = []
        for opt in options:
            ev = opt.get("expected_value", 0.5)
            risk = opt.get("risk", 0.5)
            sharpe = (ev - 0.1) / risk if risk > 0 else 0
            results.append({
                "action": opt.get("action", "unknown"),
                "expected_value": ev,
                "risk": risk,
                "sharpe_ratio": sharpe,
                "utility": ev - 0.5 * risk ** 2,
            })
        results.sort(key=lambda x: x["utility"], reverse=True)
        return results

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "decisions_made": len(self._decisions),
            "entanglements": len(self._entanglements),
            "last_collapsed": self._decisions[-1].collapsed_to.action if self._decisions and self._decisions[-1].collapsed_to else None,
        }
