from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class BootstrapPhase(Enum):
    SEED = "seed"
    SPROUT = "sprout"
    GROWTH = "growth"
    MATURITY = "maturity"
    REPRODUCTION = "reproduction"


@dataclass
class Seed:
    """最小可运行内核。"""
    capabilities: list[str] = field(default_factory=lambda: ["reason", "remember", "act"])
    quality_score: float = 0.1
    generation: int = 0

    @property
    def is_viable(self) -> bool:
        return len(self.capabilities) >= 3 and self.quality_score > 0.0


@dataclass
class BootstrapReport:
    phase: BootstrapPhase
    capabilities_acquired: list[str] = field(default_factory=list)
    total_capabilities: int = 0
    quality_score: float = 0.0
    improvements_made: int = 0
    elapsed_seconds: float = 0.0
    generation: int = 0

    @property
    def is_mature(self) -> bool:
        return self.phase == BootstrapPhase.MATURITY and self.quality_score >= 0.8

    @property
    def growth_rate(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.improvements_made / self.elapsed_seconds


class SelfBootstrapper:
    """自举启动器: 从种子到成熟Agent。"""

    def __init__(self, target_capabilities: list[str] | None = None):
        self._target = target_capabilities or [
            "reason", "remember", "act", "self_improve", "plan",
            "learn", "communicate", "create", "reflect", "adapt",
        ]
        self._seed = Seed()
        self._current_phase = BootstrapPhase.SEED
        self._acquired: list[str] = list(self._seed.capabilities)
        self._quality = self._seed.quality_score
        self._generation = 0
        self._improvements = 0
        self._start_time = time.time()
        self._phase_history: list[BootstrapReport] = []
        self._improvement_hooks: list[Callable[[str], bool]] = []

    @property
    def phase(self) -> BootstrapPhase:
        return self._current_phase

    @property
    def acquired_capabilities(self) -> list[str]:
        return list(self._acquired)

    def add_improvement_hook(self, hook: Callable[[str], bool]) -> None:
        self._improvement_hooks.append(hook)

    def _try_acquire(self, capability: str) -> bool:
        for hook in self._improvement_hooks:
            try:
                if not hook(capability):
                    return False
            except Exception:
                pass
        return True

    def sprout(self) -> BootstrapReport:
        """发芽: 从种子发展出基本能力。"""
        self._current_phase = BootstrapPhase.SPROUT
        basic = ["self_improve", "plan", "learn"]
        for cap in basic:
            if cap not in self._acquired and self._try_acquire(cap):
                self._acquired.append(cap)
                self._improvements += 1
                self._quality += 0.15
        self._quality = min(1.0, self._quality)
        self._generation += 1
        report = self._make_report()
        self._phase_history.append(report)
        logger.info(f"自举发芽: 获得{len(basic)}项能力, 质量={self._quality:.2f}")
        return report

    def grow(self, rounds: int = 5) -> BootstrapReport:
        """生长: 递归自我改进。"""
        self._current_phase = BootstrapPhase.GROWTH
        for _ in range(rounds):
            missing = [c for c in self._target if c not in self._acquired]
            if not missing:
                break
            for cap in missing:
                if self._try_acquire(cap):
                    self._acquired.append(cap)
                    self._improvements += 1
                    self._quality += 0.1
        self._quality = min(1.0, self._quality)
        self._generation += 1
        report = self._make_report()
        self._phase_history.append(report)
        return report

    def mature(self) -> BootstrapReport:
        """成熟: 达到稳定状态。"""
        self._current_phase = BootstrapPhase.MATURITY
        all_present = all(c in self._acquired for c in self._target)
        if all_present:
            self._quality = min(1.0, self._quality + 0.1)
        else:
            missing = [c for c in self._target if c not in self._acquired]
            for cap in missing:
                if self._try_acquire(cap):
                    self._acquired.append(cap)
                    self._improvements += 1
                    self._quality += 0.05
        self._quality = min(1.0, self._quality)
        report = self._make_report()
        self._phase_history.append(report)
        logger.info(f"自举成熟: {len(self._acquired)}项能力, 质量={self._quality:.2f}, 成熟={report.is_mature}")
        return report

    def reproduce(self) -> Seed:
        """繁殖: 产生下一代种子。"""
        self._current_phase = BootstrapPhase.REPRODUCTION
        self._generation += 1
        child = Seed(
            capabilities=list(self._acquired),
            quality_score=self._quality * 0.9,
            generation=self._generation,
        )
        logger.info(f"自举繁殖: 第{self._generation}代, 质量={child.quality_score:.2f}")
        return child

    def run_full_bootstrap(self) -> BootstrapReport:
        """完整自举流程: 种子->发芽->生长->成熟。"""
        self.sprout()
        self.grow(rounds=3)
        return self.mature()

    def _make_report(self) -> BootstrapReport:
        return BootstrapReport(
            phase=self._current_phase,
            capabilities_acquired=list(self._acquired),
            total_capabilities=len(self._acquired),
            quality_score=self._quality,
            improvements_made=self._improvements,
            elapsed_seconds=time.time() - self._start_time,
            generation=self._generation,
        )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "phase": self._current_phase.value,
            "acquired": len(self._acquired),
            "target": len(self._target),
            "quality": self._quality,
            "generation": self._generation,
            "improvements": self._improvements,
            "is_mature": self._current_phase == BootstrapPhase.MATURITY and self._quality >= 0.8,
        }
