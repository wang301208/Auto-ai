"""
风险预评估 - 在执行操作前评估潜在风险
与 RebellionEngine（事后评估）互补，提供事前风险评估
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    DATA_LOSS = "data_loss"
    SYSTEM_STABILITY = "system_stability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    REVERSIBILITY = "reversibility"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY = "dependency"
    STATE_CORRUPTION = "state_corruption"


@dataclass
class RiskFactor:
    category: RiskCategory
    level: RiskLevel
    description: str
    probability: float
    impact: float
    mitigation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    operation_id: str
    operation_type: str
    operation_desc: str
    overall_risk: RiskLevel
    risk_score: float
    factors: list[RiskFactor]
    should_proceed: bool
    requires_approval: bool
    recommendations: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class RiskAssessor:
    def __init__(
        self,
        risk_threshold: float = 0.7,
        critical_threshold: float = 0.9,
        auto_approve_low: bool = True,
        require_approval_high: bool = True,
    ):
        self.risk_threshold = risk_threshold
        self.critical_threshold = critical_threshold
        self.auto_approve_low = auto_approve_low
        self.require_approval_high = require_approval_high

        self._assessors: dict[str, Callable] = {}
        self._mitigations: dict[RiskCategory, Callable] = {}
        self._history: list[RiskAssessment] = []
        self._max_history = 500

    def register_assessor(self, operation_type: str, assessor: Callable) -> None:
        self._assessors[operation_type] = assessor

    def register_mitigation(self, category: RiskCategory, mitigation: Callable) -> None:
        self._mitigations[category] = mitigation

    def assess(
        self,
        operation_type: str,
        operation_desc: str,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        operation_id = f"{operation_type}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        params = params or {}
        context = context or {}
        factors: list[RiskFactor] = []

        if operation_type in self._assessors:
            try:
                custom_factors = self._assessors[operation_type](params, context)
                if custom_factors:
                    factors.extend(custom_factors)
            except Exception as e:
                logger.warning(f"[RiskAssessor] Custom assessor failed: {e}")

        factors.extend(self._default_assess(operation_type, params, context))

        risk_score = self._calculate_risk_score(factors)
        overall_risk = self._determine_risk_level(risk_score)

        should_proceed = risk_score < self.critical_threshold
        requires_approval = risk_score >= self.risk_threshold and self.require_approval_high

        recommendations = self._generate_recommendations(factors, overall_risk)

        assessment = RiskAssessment(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_desc=operation_desc,
            overall_risk=overall_risk,
            risk_score=risk_score,
            factors=factors,
            should_proceed=should_proceed,
            requires_approval=requires_approval,
            recommendations=recommendations,
        )

        self._history.append(assessment)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        log_level = logging.WARNING if risk_score >= self.risk_threshold else logging.INFO
        logger.log(log_level, f"[RiskAssessor] {operation_type}: risk={overall_risk.value} score={risk_score:.2f}")

        return assessment

    def _default_assess(
        self, operation_type: str, params: dict[str, Any], context: dict[str, Any]
    ) -> list[RiskFactor]:
        factors: list[RiskFactor] = []

        if operation_type in ("file_delete", "file_overwrite", "database_drop"):
            factors.append(RiskFactor(
                category=RiskCategory.DATA_LOSS,
                level=RiskLevel.HIGH,
                description="Operation may cause irreversible data loss",
                probability=0.9,
                impact=0.95,
                mitigation="Create backup before operation",
            ))

        if operation_type in ("system_config_change", "service_restart", "kernel_module_load"):
            factors.append(RiskFactor(
                category=RiskCategory.SYSTEM_STABILITY,
                level=RiskLevel.HIGH,
                description="Operation may affect system stability",
                probability=0.6,
                impact=0.8,
                mitigation="Test in isolated environment first",
            ))

        if operation_type in ("execute_shell", "run_script", "code_injection"):
            factors.append(RiskFactor(
                category=RiskCategory.SECURITY,
                level=RiskLevel.CRITICAL,
                description="Operation involves arbitrary code execution",
                probability=0.8,
                impact=0.95,
                mitigation="Sandbox execution, validate input",
            ))

        if params.get("batch_size", 1) > 100:
            factors.append(RiskFactor(
                category=RiskCategory.PERFORMANCE,
                level=RiskLevel.MEDIUM,
                description="Large batch operation may degrade performance",
                probability=0.5,
                impact=0.4,
                mitigation="Split into smaller batches",
            ))

        if operation_type in ("self_modify", "code_change", "hot_reload"):
            factors.append(RiskFactor(
                category=RiskCategory.REVERSIBILITY,
                level=RiskLevel.MEDIUM,
                description="Self-modification may be hard to reverse",
                probability=0.7,
                impact=0.6,
                mitigation="Use version control, create rollback point",
            ))

        if params.get("recursive", False) or params.get("depth", 0) > 10:
            factors.append(RiskFactor(
                category=RiskCategory.RESOURCE_EXHAUSTION,
                level=RiskLevel.MEDIUM,
                description="Deep recursion may exhaust resources",
                probability=0.4,
                impact=0.7,
                mitigation="Set explicit depth limits, monitor resources",
            ))

        if context.get("network_required", False) and not context.get("network_available", True):
            factors.append(RiskFactor(
                category=RiskCategory.DEPENDENCY,
                level=RiskLevel.HIGH,
                description="Network dependency not available",
                probability=0.9,
                impact=0.8,
                mitigation="Enable offline mode or wait for network",
            ))

        return factors

    def _calculate_risk_score(self, factors: list[RiskFactor]) -> float:
        if not factors:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        level_weights = {
            RiskLevel.NEGLIGIBLE: 0.1,
            RiskLevel.LOW: 0.3,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 1.0,
        }

        for factor in factors:
            weight = level_weights[factor.level]
            risk = factor.probability * factor.impact
            total_score += risk * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _determine_risk_level(self, score: float) -> RiskLevel:
        if score < 0.1:
            return RiskLevel.NEGLIGIBLE
        elif score < 0.3:
            return RiskLevel.LOW
        elif score < 0.5:
            return RiskLevel.MEDIUM
        elif score < 0.7:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_recommendations(self, factors: list[RiskFactor], level: RiskLevel) -> list[str]:
        recommendations = []

        for factor in factors:
            if factor.mitigation and factor.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                recommendations.append(f"[{factor.category.value}] {factor.mitigation}")

        if level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recommendations.append("Consider running in dry-run mode first")
            recommendations.append("Ensure rollback mechanism is available")

        if not recommendations:
            recommendations.append("Operation appears safe to proceed")

        return recommendations

    def apply_mitigation(self, category: RiskCategory, params: dict[str, Any]) -> bool:
        if category not in self._mitigations:
            logger.warning(f"[RiskAssessor] No mitigation registered for {category.value}")
            return False
        try:
            return self._mitigations[category](params)
        except Exception as e:
            logger.error(f"[RiskAssessor] Mitigation failed: {e}")
            return False

    def get_statistics(self) -> dict[str, Any]:
        if not self._history:
            return {"total_assessments": 0}

        risk_distribution = {}
        for level in RiskLevel:
            risk_distribution[level.value] = sum(
                1 for a in self._history if a.overall_risk == level
            )

        return {
            "total_assessments": len(self._history),
            "risk_distribution": risk_distribution,
            "blocked_operations": sum(1 for a in self._history if not a.should_proceed),
            "approval_required": sum(1 for a in self._history if a.requires_approval),
            "average_risk_score": sum(a.risk_score for a in self._history) / len(self._history),
        }

    def get_recent_assessments(self, n: int = 10) -> list[RiskAssessment]:
        return self._history[-n:]
