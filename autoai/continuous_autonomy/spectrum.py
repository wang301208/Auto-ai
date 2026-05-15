from __future__ import annotations

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AutonomyDimension(Enum):
    CODE_MODIFY = "code_modify"
    CONFIG_MODIFY = "config_modify"
    STRATEGY_MODIFY = "strategy_modify"
    ARCHITECTURE_MODIFY = "architecture_modify"
    SELF_SPAWN = "self_spawn"
    SELF_TERMINATE = "self_terminate"
    SHELL_EXECUTE = "shell_execute"
    NETWORK_ACCESS = "network_access"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    BUDGET_CONTROL = "budget_control"
    POLICY_MODIFY = "policy_modify"
    AGENT_COMMUNICATE = "agent_communicate"
    MEMORY_MANAGE = "memory_manage"
    MODEL_SELECT = "model_select"


class RiskLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DimensionState:
    """单一维度的自主度状态。"""
    dimension: AutonomyDimension
    value: float = 0.5
    min_value: float = 0.0
    max_value: float = 1.0
    risk_at_max: RiskLevel = RiskLevel.MEDIUM
    context_modifier: float = 1.0
    success_streak: int = 0
    failure_streak: int = 0
    last_adjusted: float = 0.0

    @property
    def effective_value(self) -> float:
        raw = self.value * self.context_modifier
        return max(self.min_value, min(self.max_value, raw))

    def adjust_for_success(self, delta: float = 0.02) -> None:
        self.success_streak += 1
        self.failure_streak = 0
        boost = delta * (1 + math.log1p(self.success_streak))
        self.value = min(self.max_value, self.value + boost)
        self.last_adjusted = time.time()

    def adjust_for_failure(self, delta: float = 0.05) -> None:
        self.failure_streak += 1
        self.success_streak = 0
        penalty = delta * (1 + math.log1p(self.failure_streak))
        self.value = max(self.min_value, self.value - penalty)
        self.last_adjusted = time.time()


@dataclass
class AutonomyProfile:
    """Agent的完整自主度光谱: 每个维度独立, 基于上下文动态调整。"""
    agent_id: str
    dimensions: dict[AutonomyDimension, DimensionState] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def get_value(self, dimension: AutonomyDimension) -> float:
        state = self.dimensions.get(dimension)
        return state.effective_value if state else 0.5

    def get_overall_autonomy(self) -> float:
        if not self.dimensions:
            return 0.5
        values = [d.effective_value for d in self.dimensions.values()]
        return sum(values) / len(values)

    def get_risk_profile(self) -> dict[RiskLevel, list[str]]:
        result: dict[RiskLevel, list[str]] = {r: [] for r in RiskLevel}
        for dim, state in self.dimensions.items():
            if state.effective_value > 0.7:
                result[state.risk_at_max].append(dim.value)
        return result

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "dimensions": {
                d.value: {"value": s.effective_value, "risk": s.risk_at_max.value}
                for d, s in self.dimensions.items()
            },
            "overall": self.get_overall_autonomy(),
        }


DEFAULT_PROFILES = {
    "conservative": {
        AutonomyDimension.CODE_MODIFY: (0.1, RiskLevel.HIGH),
        AutonomyDimension.SHELL_EXECUTE: (0.2, RiskLevel.HIGH),
        AutonomyDimension.FILE_DELETE: (0.0, RiskLevel.CRITICAL),
        AutonomyDimension.NETWORK_ACCESS: (0.3, RiskLevel.MEDIUM),
        AutonomyDimension.SELF_SPAWN: (0.1, RiskLevel.HIGH),
        AutonomyDimension.POLICY_MODIFY: (0.0, RiskLevel.CRITICAL),
        AutonomyDimension.STRATEGY_MODIFY: (0.3, RiskLevel.MEDIUM),
        AutonomyDimension.CONFIG_MODIFY: (0.2, RiskLevel.MEDIUM),
    },
    "balanced": {
        AutonomyDimension.CODE_MODIFY: (0.5, RiskLevel.HIGH),
        AutonomyDimension.SHELL_EXECUTE: (0.4, RiskLevel.HIGH),
        AutonomyDimension.FILE_DELETE: (0.2, RiskLevel.CRITICAL),
        AutonomyDimension.NETWORK_ACCESS: (0.6, RiskLevel.MEDIUM),
        AutonomyDimension.SELF_SPAWN: (0.5, RiskLevel.HIGH),
        AutonomyDimension.POLICY_MODIFY: (0.1, RiskLevel.CRITICAL),
        AutonomyDimension.STRATEGY_MODIFY: (0.7, RiskLevel.MEDIUM),
        AutonomyDimension.CONFIG_MODIFY: (0.6, RiskLevel.MEDIUM),
    },
    "radical": {
        AutonomyDimension.CODE_MODIFY: (0.9, RiskLevel.HIGH),
        AutonomyDimension.SHELL_EXECUTE: (0.8, RiskLevel.HIGH),
        AutonomyDimension.FILE_DELETE: (0.4, RiskLevel.CRITICAL),
        AutonomyDimension.NETWORK_ACCESS: (0.9, RiskLevel.MEDIUM),
        AutonomyDimension.SELF_SPAWN: (0.9, RiskLevel.HIGH),
        AutonomyDimension.POLICY_MODIFY: (0.3, RiskLevel.CRITICAL),
        AutonomyDimension.STRATEGY_MODIFY: (0.95, RiskLevel.MEDIUM),
        AutonomyDimension.CONFIG_MODIFY: (0.9, RiskLevel.MEDIUM),
    },
}


class ContinuousAutonomy:
    """连续自主度光谱: 替代离散L0-L8等级, 每维度独立连续值[0,1]。

    核心理念: 自主度不是全局开关, 而是每个能力维度上的连续光谱,
    基于上下文(任务风险/成功率/历史)动态调整。
    """

    def __init__(self, agent_id: str, profile_name: str = "balanced"):
        self.agent_id = agent_id
        self.profile = AutonomyProfile(agent_id=agent_id)
        self._load_profile(profile_name)
        self._adjustment_log: list[dict] = []
        logger.info(f"连续自主度初始化: agent={agent_id}, profile={profile_name}, overall={self.profile.get_overall_autonomy():.2f}")

    def _load_profile(self, profile_name: str) -> None:
        profile_data = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["balanced"])
        for dim, (value, risk) in profile_data.items():
            self.profile.dimensions[dim] = DimensionState(
                dimension=dim, value=value, risk_at_max=risk,
            )
        for dim in AutonomyDimension:
            if dim not in self.profile.dimensions:
                self.profile.dimensions[dim] = DimensionState(
                    dimension=dim, value=0.5, risk_at_max=RiskLevel.MEDIUM,
                )

    def can(self, dimension: AutonomyDimension, threshold: float = 0.5) -> bool:
        """检查Agent在指定维度上是否有足够的自主度。"""
        value = self.profile.get_value(dimension)
        return value >= threshold

    def get_value(self, dimension: AutonomyDimension) -> float:
        return self.profile.get_value(dimension)

    def adjust_for_context(self, dimension: AutonomyDimension, context_risk: float) -> None:
        """基于上下文风险调整自主度。"""
        state = self.profile.dimensions.get(dimension)
        if not state:
            return
        if context_risk > 0.7:
            state.context_modifier = max(0.1, 1.0 - context_risk * 0.8)
        else:
            state.context_modifier = 1.0
        self.profile.last_updated = time.time()

    def record_success(self, dimension: AutonomyDimension) -> None:
        state = self.profile.dimensions.get(dimension)
        if state:
            state.adjust_for_success()
            self._adjustment_log.append({
                "dimension": dimension.value, "direction": "up",
                "new_value": state.effective_value, "timestamp": time.time(),
            })

    def record_failure(self, dimension: AutonomyDimension) -> None:
        state = self.profile.dimensions.get(dimension)
        if state:
            state.adjust_for_failure()
            self._adjustment_log.append({
                "dimension": dimension.value, "direction": "down",
                "new_value": state.effective_value, "timestamp": time.time(),
            })

    def set_dimension(self, dimension: AutonomyDimension, value: float) -> None:
        state = self.profile.dimensions.get(dimension)
        if state:
            state.value = max(state.min_value, min(state.max_value, value))
            state.last_adjusted = time.time()

    def get_status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "overall_autonomy": self.profile.get_overall_autonomy(),
            "risk_profile": {r.value: dims for r, dims in self.profile.get_risk_profile().items()},
            "dimensions": self.profile.to_dict()["dimensions"],
            "adjustments": len(self._adjustment_log),
        }

    def to_legacy_level(self) -> int:
        """兼容: 将连续光谱映射回离散L0-L8等级。"""
        overall = self.profile.get_overall_autonomy()
        if overall < 0.1:
            return 0
        if overall < 0.2:
            return 1
        if overall < 0.35:
            return 2
        if overall < 0.45:
            return 3
        if overall < 0.55:
            return 4
        if overall < 0.65:
            return 5
        if overall < 0.75:
            return 6
        if overall < 0.85:
            return 7
        return 8
