"""自愈引擎: Agent自主发现、诊断、修复bug。"""

from __future__ import annotations

import time
import traceback
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class IncidentType(Enum):
    EXCEPTION = "exception"
    PERFORMANCE = "performance"
    CONSISTENCY = "consistency"
    RESOURCE_LEAK = "resource_leak"
    DEADLOCK = "deadlock"
    DATA_CORRUPTION = "data_corruption"
    TEST_FAILURE = "test_failure"


class HealActionType(Enum):
    RESTART_MODULE = "restart_module"
    ROLLBACK_STATE = "rollback_state"
    APPLY_PATCH = "apply_patch"
    DEGRADE = "degrade"
    REALLOCATE = "reallocate"
    RETRY = "retry"
    ESCALATE = "escalate"


@dataclass
class HealIncident:
    """自愈事件: Agent发现的异常。"""
    incident_id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    module: str
    description: str
    stack_trace: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: float = 0.0

    @property
    def age_seconds(self) -> float:
        end = self.resolved_at if self.resolved_at else time.time()
        return end - self.detected_at

    @property
    def is_urgent(self) -> bool:
        return self.severity.value >= 3


@dataclass
class HealAction:
    """自愈动作: 对事件的响应。"""
    action_id: str
    incident_id: str
    action_type: HealActionType
    target: str
    description: str
    estimated_success_rate: float = 0.5
    cost: float = 0.1
    executed: bool = False
    success: bool = False
    executed_at: float = 0.0

    @property
    def is_low_cost(self) -> bool:
        return self.cost < 0.3


@dataclass
class HealOutcome:
    """自愈结果。"""
    incident_id: str
    actions_taken: list[str]
    resolved: bool
    total_time_ms: float
    remaining_severity: IncidentSeverity | None = None
    lessons: list[str] = field(default_factory=list)


class SelfHealEngine:
    """自愈引擎: Agent自主修复。"""

    def __init__(self, agent_id: str = "default"):
        self._agent_id = agent_id
        self._incidents: dict[str, HealIncident] = {}
        self._actions: list[HealAction] = []
        self._outcomes: list[HealOutcome] = []
        self._incident_count: int = 0
        self._resolved_count: int = 0
        self._escalated_count: int = 0
        self._total_heal_time_ms: float = 0.0
        self._heal_strategies: dict[IncidentType, list[HealActionType]] = {
            IncidentType.EXCEPTION: [HealActionType.RETRY, HealActionType.RESTART_MODULE, HealActionType.ROLLBACK_STATE],
            IncidentType.PERFORMANCE: [HealActionType.REALLOCATE, HealActionType.DEGRADE],
            IncidentType.CONSISTENCY: [HealActionType.ROLLBACK_STATE, HealActionType.APPLY_PATCH],
            IncidentType.RESOURCE_LEAK: [HealActionType.RESTART_MODULE, HealActionType.REALLOCATE],
            IncidentType.DEADLOCK: [HealActionType.RESTART_MODULE],
            IncidentType.DATA_CORRUPTION: [HealActionType.ROLLBACK_STATE, HealActionType.APPLY_PATCH],
            IncidentType.TEST_FAILURE: [HealActionType.ROLLBACK_STATE, HealActionType.ESCALATE],
        }

    def detect_incident(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        module: str,
        description: str,
        stack_trace: str = "",
        context: dict[str, Any] | None = None,
    ) -> HealIncident:
        """检测并记录事件。"""
        self._incident_count += 1
        incident_id = f"inc_{self._incident_count}"
        incident = HealIncident(
            incident_id=incident_id,
            incident_type=incident_type,
            severity=severity,
            module=module,
            description=description,
            stack_trace=stack_trace,
            context=context or {},
        )
        self._incidents[incident_id] = incident
        logger.info(f"自愈: 检测事件 [{severity.value}] {module}: {description[:60]}")
        return incident

    def diagnose(self, incident: HealIncident) -> list[HealAction]:
        """诊断: 为事件决定修复动作序列。"""
        strategies = self._heal_strategies.get(incident.incident_type, [HealActionType.RETRY])
        actions = []
        for i, action_type in enumerate(strategies):
            success_rate = max(0.1, 0.8 - i * 0.2)
            cost = 0.1 + i * 0.2
            action = HealAction(
                action_id=f"act_{incident.incident_id}_{i}",
                incident_id=incident.incident_id,
                action_type=action_type,
                target=incident.module,
                description=self._describe_action(action_type, incident),
                estimated_success_rate=success_rate,
                cost=cost,
            )
            actions.append(action)
        return actions

    def _describe_action(self, action_type: HealActionType, incident: HealIncident) -> str:
        descriptions = {
            HealActionType.RESTART_MODULE: f"重启模块 {incident.module}",
            HealActionType.ROLLBACK_STATE: f"回滚 {incident.module} 到上一致状态",
            HealActionType.APPLY_PATCH: f"为 {incident.module} 生成并应用补丁",
            HealActionType.DEGRADE: f"降级 {incident.module} 运行模式",
            HealActionType.REALLOCATE: f"重新分配 {incident.module} 资源",
            HealActionType.RETRY: f"重试 {incident.module} 失败操作",
            HealActionType.ESCALATE: f"升级 {incident.module} 事件到更高层",
        }
        return descriptions.get(action_type, f"对 {incident.module} 执行 {action_type.value}")

    def execute_heal(self, incident: HealIncident) -> HealOutcome:
        """执行自愈: 诊断→按序执行动作→验证。"""
        start = time.time()
        actions = self.diagnose(incident)
        actions_taken = []
        resolved = False
        for action in actions:
            action.executed = True
            action.executed_at = time.time()
            success = self._simulate_action(action, incident)
            action.success = success
            self._actions.append(action)
            actions_taken.append(action.action_id)
            if success:
                resolved = True
                break
            if action.action_type == HealActionType.ESCALATE:
                self._escalated_count += 1
        if resolved:
            incident.resolved = True
            incident.resolved_at = time.time()
            self._resolved_count += 1
        total_ms = (time.time() - start) * 1000
        self._total_heal_time_ms += total_ms
        remaining = None if resolved else incident.severity
        lessons = self._extract_lessons(incident, actions, resolved)
        outcome = HealOutcome(
            incident_id=incident.incident_id,
            actions_taken=actions_taken,
            resolved=resolved,
            total_time_ms=total_ms,
            remaining_severity=remaining,
            lessons=lessons,
        )
        self._outcomes.append(outcome)
        return outcome

    def _simulate_action(self, action: HealAction, incident: HealIncident) -> bool:
        roll = hash(f"{action.action_id}:{time.time()}") % 100
        threshold = action.estimated_success_rate * 100
        return roll < threshold

    def _extract_lessons(self, incident: HealIncident, actions: list[HealAction], resolved: bool) -> list[str]:
        lessons = []
        if resolved:
            successful = [a for a in actions if a.success]
            if successful:
                lessons.append(f"{incident.incident_type.value}: {successful[0].action_type.value}成功")
        else:
            lessons.append(f"{incident.incident_type.value}: 所有自愈动作失败，需升级")
        if incident.severity.value >= 3:
            lessons.append(f"高严重度事件: {incident.module} 需要加固")
        return lessons

    def auto_heal_cycle(self) -> dict[str, Any]:
        """运行自愈周期: 扫描未解决事件并修复。"""
        unresolved = [i for i in self._incidents.values() if not i.resolved]
        unresolved.sort(key=lambda i: i.severity.value, reverse=True)
        results = []
        for incident in unresolved[:5]:
            outcome = self.execute_heal(incident)
            results.append(outcome)
        return {
            "checked": len(unresolved),
            "healed": sum(1 for o in results if o.resolved),
            "escalated": sum(1 for o in results if not o.resolved),
            "total_time_ms": sum(o.total_time_ms for o in results),
        }

    @property
    def stats(self) -> dict[str, Any]:
        heal_rate = self._resolved_count / self._incident_count if self._incident_count > 0 else 0.0
        return {
            "agent_id": self._agent_id,
            "total_incidents": self._incident_count,
            "resolved": self._resolved_count,
            "escalated": self._escalated_count,
            "heal_rate": heal_rate,
            "avg_heal_time_ms": (
                self._total_heal_time_ms / self._resolved_count
                if self._resolved_count > 0 else 0.0
            ),
            "pending_incidents": sum(1 for i in self._incidents.values() if not i.resolved),
        }
