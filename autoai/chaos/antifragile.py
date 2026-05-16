"""反脆弱引擎: 主动注入故障，系统在故障中变强。

纳西姆·塔勒布的反脆弱理论:
- 脆弱: 故障使其变弱
- 韧性: 故障不影响
- 反脆弱: 故障使其变强

本引擎让Agent通过持续混沌实验变得反脆弱。
"""

from __future__ import annotations

import time
import random
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
from autoai.autonomy_core.real_executor import RealExecutor
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class FaultType(Enum):
    MODULE_KILL = "module_kill"
    MESSAGE_DELAY = "message_delay"
    MEMORY_LOSS = "memory_loss"
    BELIEF_CORRUPTION = "belief_corruption"
    NETWORK_PARTITION = "network_partition"
    RESOURCE_STARVATION = "resource_starvation"
    GOAL_CONFLICT = "goal_conflict"
    KNOWLEDGE_ERASURE = "knowledge_erasure"
    TIMING_ATTACK = "timing_attack"


class RecoveryStatus(Enum):
    RECOVERED = "recovered"
    DEGRADED = "degraded"
    FAILED = "failed"
    CASCADING_FAILURE = "cascading_failure"


@dataclass
class FaultInjection:
    """故障注入: 一次混沌实验。"""
    injection_id: str
    fault_type: FaultType
    target: str
    intensity: float = 1.0
    duration_ms: float = 100.0
    description: str = ""
    injected_at: float = field(default_factory=time.time)

    @property
    def is_mild(self) -> bool:
        return self.intensity <= 0.3

    @property
    def is_severe(self) -> bool:
        return self.intensity >= 0.8


@dataclass
class RecoveryReport:
    """恢复报告: 故障注入后的恢复状态。"""
    injection_id: str
    fault_type: FaultType
    status: RecoveryStatus
    recovery_time_ms: float = 0.0
    modules_affected: list[str] = field(default_factory=list)
    data_loss: bool = False
    cascading: bool = False
    resilience_delta: float = 0.0
    lessons_learned: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_antifragile(self) -> bool:
        return self.resilience_delta > 0


@dataclass
class ResilienceProfile:
    """韧性剖面: Agent对各类型故障的抵抗力。"""
    fault_resilience: dict[str, float] = field(default_factory=dict)
    total_injections: int = 0
    total_recoveries: int = 0
    total_degradations: int = 0
    total_failures: int = 0
    avg_recovery_time_ms: float = 0.0
    antifragile_count: int = 0

    @property
    def overall_resilience(self) -> float:
        if not self.fault_resilience:
            return 0.5
        return sum(self.fault_resilience.values()) / len(self.fault_resilience)

    @property
    def antifragile_ratio(self) -> float:
        return self.antifragile_count / self.total_injections if self.total_injections > 0 else 0.0

    def update(self, report: RecoveryReport) -> None:
        self.total_injections += 1
        ft_key = report.fault_type.value
        current = self.fault_resilience.get(ft_key, 0.5)
        if report.status == RecoveryStatus.RECOVERED:
            self.total_recoveries += 1
            delta = 0.05 if not report.is_antifragile else 0.1
            self.fault_resilience[ft_key] = min(1.0, current + delta)
            if report.is_antifragile:
                self.antifragile_count += 1
        elif report.status == RecoveryStatus.DEGRADED:
            self.total_degradations += 1
            self.fault_resilience[ft_key] = max(0.0, current - 0.02)
        elif report.status == RecoveryStatus.FAILED:
            self.total_failures += 1
            self.fault_resilience[ft_key] = max(0.0, current - 0.05)
        elif report.status == RecoveryStatus.CASCADING_FAILURE:
            self.total_failures += 1
            self.fault_resilience[ft_key] = max(0.0, current - 0.1)
        if report.recovery_time_ms > 0:
            total_time = self.avg_recovery_time_ms * (self.total_injections - 1) + report.recovery_time_ms
            self.avg_recovery_time_ms = total_time / self.total_injections


class AntiFragileEngine(FullAutonomyMixin):
    """反脆弱引擎: 持续混沌实验使Agent变强。"""

    def __init__(self, agent_id: str = "default", intensity: float = 0.5, use_learnable: bool = False):
        self._init_full_autonomy()
        self._agent_id = agent_id
        self._base_intensity = intensity
        self._profile = ResilienceProfile()
        self._injection_history: list[FaultInjection] = []
        self._recovery_history: list[RecoveryReport] = []
        self._lessons: dict[str, list[str]] = {}
        self._injection_count: int = 0
        self._chaos_active: bool = False
        self._use_learnable = use_learnable
        self._param_space: ParamSpace | None = None
        self._param_learner: ParamLearner | None = None
        self._real_executor: RealExecutor | None = None
        if use_learnable:
            self._init_learnable()

    def _init_learnable(self) -> None:
        self._param_space = ParamSpace("antifragile")
        self._param_space.declare("weakest_target_prob", 0.6, 0.3, 0.9, lr=0.01)
        self._param_space.declare("recovered_delta", 0.05, 0.01, 0.15, lr=0.005)
        self._param_space.declare("antifragile_delta", 0.1, 0.03, 0.2, lr=0.005)
        self._param_space.declare("degraded_delta", 0.02, 0.005, 0.1, lr=0.005)
        self._param_space.declare("failed_delta", 0.05, 0.01, 0.15, lr=0.005)
        self._param_learner = ParamLearner(self._param_space)
        self._real_executor = RealExecutor()

    def enable_learnable(self) -> None:
        if not self._use_learnable:
            self._use_learnable = True
            self._init_learnable()

    def select_fault(self, modules: list[str] | None = None) -> FaultInjection:
        """选择下一个要注入的故障。"""
        available = list(FaultType)
        weakest = self._find_weakest_fault_type()
        target_prob = 0.6
        if self._use_learnable and self._param_space:
            target_prob = self._param_space.get("weakest_target_prob")
        if weakest and random.random() < target_prob:
            fault_type = weakest
        else:
            fault_type = random.choice(available)
        target = random.choice(modules) if modules else "core"
        intensity = self._calculate_intensity(fault_type)
        self._injection_count += 1
        injection = FaultInjection(
            injection_id=f"chaos_{self._injection_count}",
            fault_type=fault_type,
            target=target,
            intensity=intensity,
            duration_ms=random.uniform(50, 500),
            description=f"混沌注入: {fault_type.value}@{target} 强度{intensity:.2f}",
        )
        self._injection_history.append(injection)
        return injection

    def _find_weakest_fault_type(self) -> FaultType | None:
        if not self._profile.fault_resilience:
            return None
        weakest_val = min(self._profile.fault_resilience.values())
        if weakest_val >= 0.8:
            return None
        for ft, val in self._profile.fault_resilience.items():
            if val == weakest_val:
                try:
                    return FaultType(ft)
                except ValueError:
                    pass
        return None

    def _calculate_intensity(self, fault_type: FaultType) -> float:
        current_resilience = self._profile.fault_resilience.get(fault_type.value, 0.5)
        intensity = self._base_intensity * (1.0 + (1.0 - current_resilience))
        return min(1.0, max(0.1, intensity + random.uniform(-0.1, 0.1)))

    def inject_and_observe(self, injection: FaultInjection) -> RecoveryReport:
        """注入故障并观察恢复。"""
        start = time.time()
        affected = self._simulate_fault_effect(injection)
        recovery_status = self._determine_recovery(injection, affected)
        recovery_time = self._estimate_recovery_time(injection, recovery_status)
        data_loss = injection.fault_type in (
            FaultType.MEMORY_LOSS, FaultType.KNOWLEDGE_ERASURE
        ) and injection.intensity > 0.5
        cascading = (
            len(affected) > 2
            and injection.intensity > 0.7
            and recovery_status == RecoveryStatus.FAILED
        )
        resilience_delta = self._compute_resilience_delta(injection, recovery_status)
        lessons = self._extract_lessons(injection, recovery_status, affected)
        for lesson in lessons:
            self._lessons.setdefault(injection.fault_type.value, []).append(lesson)
        report = RecoveryReport(
            injection_id=injection.injection_id,
            fault_type=injection.fault_type,
            status=recovery_status,
            recovery_time_ms=recovery_time,
            modules_affected=affected,
            data_loss=data_loss,
            cascading=cascading,
            resilience_delta=resilience_delta,
            lessons_learned=lessons,
        )
        self._recovery_history.append(report)
        self._profile.update(report)
        return report

    def _simulate_fault_effect(self, injection: FaultInjection) -> list[str]:
        base_affected = [injection.target]
        if injection.intensity > 0.5:
            base_affected.append(f"{injection.target}_dependent")
        if injection.intensity > 0.8:
            base_affected.append(f"{injection.target}_cascading")
        return base_affected

    def _determine_recovery(self, injection: FaultInjection, affected: list[str]) -> RecoveryStatus:
        resilience = self._profile.fault_resilience.get(injection.fault_type.value, 0.5)
        roll = random.random()
        if roll < resilience * 0.8:
            return RecoveryStatus.RECOVERED
        elif roll < resilience + 0.15:
            return RecoveryStatus.DEGRADED
        elif len(affected) > 2 and injection.intensity > 0.7:
            return RecoveryStatus.CASCADING_FAILURE
        else:
            return RecoveryStatus.FAILED

    def _estimate_recovery_time(self, injection: FaultInjection, status: RecoveryStatus) -> float:
        base = injection.duration_ms
        multipliers = {
            RecoveryStatus.RECOVERED: 1.0,
            RecoveryStatus.DEGRADED: 3.0,
            RecoveryStatus.FAILED: 10.0,
            RecoveryStatus.CASCADING_FAILURE: 50.0,
        }
        return base * multipliers.get(status, 1.0)

    def _compute_resilience_delta(self, injection: FaultInjection, status: RecoveryStatus) -> float:
        if status == RecoveryStatus.RECOVERED:
            recovery_bonus = 0.02
            intensity_bonus = injection.intensity * 0.03
            return recovery_bonus + intensity_bonus
        elif status == RecoveryStatus.DEGRADED:
            return -0.01
        elif status == RecoveryStatus.FAILED:
            return -0.03
        else:
            return -0.05

    def _extract_lessons(
        self,
        injection: FaultInjection,
        status: RecoveryStatus,
        affected: list[str],
    ) -> list[str]:
        lessons = []
        if status == RecoveryStatus.RECOVERED:
            lessons.append(f"{injection.fault_type.value}: 恢复成功，韧性增强")
        elif status == RecoveryStatus.DEGRADED:
            lessons.append(f"{injection.fault_type.value}: 降级运行，需冗余备份")
        elif status == RecoveryStatus.FAILED:
            lessons.append(f"{injection.fault_type.value}: 恢复失败，需自动修复")
        elif status == RecoveryStatus.CASCADING_FAILURE:
            lessons.append(f"{injection.fault_type.value}: 级联故障，需断路器模式")
        if len(affected) > 1:
            lessons.append(f"高影响范围: {len(affected)}模块受影响，需隔离")
        return lessons

    def run_chaos_cycle(
        self,
        modules: list[str] | None = None,
        num_injections: int = 3,
    ) -> dict[str, Any]:
        """运行一个完整混沌周期。"""
        self._chaos_active = True
        results = []
        for _ in range(num_injections):
            injection = self.select_fault(modules)
            report = self.inject_and_observe(injection)
            results.append(report)
        self._chaos_active = False
        recovered = sum(1 for r in results if r.status == RecoveryStatus.RECOVERED)
        antifragile = sum(1 for r in results if r.is_antifragile)
        return {
            "injections": num_injections,
            "recovered": recovered,
            "antifragile_events": antifragile,
            "overall_resilience": self._profile.overall_resilience,
            "avg_recovery_ms": self._profile.avg_recovery_time_ms,
        }

    @property
    def profile(self) -> ResilienceProfile:
        return self._profile

    @property
    def lessons(self) -> dict[str, list[str]]:
        return dict(self._lessons)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agent_id": self._agent_id,
            "total_injections": self._profile.total_injections,
            "overall_resilience": self._profile.overall_resilience,
            "antifragile_ratio": self._profile.antifragile_ratio,
            "avg_recovery_ms": self._profile.avg_recovery_time_ms,
            "recoveries": self._profile.total_recoveries,
            "degradations": self._profile.total_degradations,
            "failures": self._profile.total_failures,
            "lessons_learned": sum(len(v) for v in self._lessons.values()),
            "chaos_active": self._chaos_active,
            "fault_resilience": dict(self._profile.fault_resilience),
        }
