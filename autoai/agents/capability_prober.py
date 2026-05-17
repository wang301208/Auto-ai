"""
能力边界探测 - 定期探测自身能力边界，发现"不知道什么"
让代理能够意识到自己的能力限制和知识盲区
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CapabilityStatus(Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    UNTESTED = "untested"


class CapabilityCategory(Enum):
    LANGUAGE = "language"
    TOOL = "tool"
    API = "api"
    MODEL = "model"
    RESOURCE = "resource"
    KNOWLEDGE = "knowledge"
    SKILL = "skill"


@dataclass
class Capability:
    name: str
    category: CapabilityCategory
    status: CapabilityStatus
    confidence: float
    last_tested: datetime | None = None
    test_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.test_count == 0:
            return 0.0
        return self.success_count / self.test_count


@dataclass
class BoundaryFinding:
    capability_name: str
    category: CapabilityCategory
    boundary_type: str  # "hard_limit", "soft_limit", "unknown_area"
    description: str
    confidence: float
    suggested_action: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class CapabilityProber:
    def __init__(
        self,
        probe_interval: float = 3600.0,
        min_confidence: float = 0.7,
        test_timeout: float = 30.0,
    ):
        self.probe_interval = probe_interval
        self.min_confidence = min_confidence
        self.test_timeout = test_timeout

        self._capabilities: dict[str, Capability] = {}
        self._probers: dict[str, Callable] = {}
        self._boundaries: list[BoundaryFinding] = []
        self._last_probe: datetime | None = None
        self._probe_count: int = 0

    def register_capability(
        self,
        name: str,
        category: CapabilityCategory,
        tester: Callable | None = None,
        initial_confidence: float = 0.5,
        limitations: list[str] | None = None,
    ) -> None:
        self._capabilities[name] = Capability(
            name=name,
            category=category,
            status=CapabilityStatus.UNTESTED,
            confidence=initial_confidence,
            limitations=limitations or [],
        )
        if tester is not None:
            self._probers[name] = tester
        logger.debug(f"[CapabilityProber] Registered capability: {name}")

    def probe(self, capability_name: str | None = None) -> list[Capability]:
        probed: list[Capability] = []
        to_probe = [capability_name] if capability_name else list(self._capabilities.keys())

        for name in to_probe:
            if name not in self._capabilities:
                continue

            cap = self._capabilities[name]
            tester = self._probers.get(name)

            if tester is None:
                cap.status = CapabilityStatus.UNKNOWN
                probed.append(cap)
                continue

            try:
                result = tester()
                cap.test_count += 1
                cap.last_tested = datetime.now(UTC)

                if result.get("available", False):
                    cap.status = CapabilityStatus.AVAILABLE
                    cap.success_count += 1
                    cap.confidence = min(1.0, cap.confidence + 0.1)
                elif result.get("degraded", False):
                    cap.status = CapabilityStatus.DEGRADED
                    cap.success_count += 1
                    cap.confidence = (cap.confidence + 0.5) / 2
                else:
                    cap.status = CapabilityStatus.UNAVAILABLE
                    cap.failure_count += 1
                    cap.confidence = max(0.0, cap.confidence - 0.1)

                if result.get("limitations"):
                    for lim in result["limitations"]:
                        if lim not in cap.limitations:
                            cap.limitations.append(lim)

                probed.append(cap)
                logger.info(f"[CapabilityProber] {name}: {cap.status.value} (confidence={cap.confidence:.2f})")

            except Exception as e:
                cap.status = CapabilityStatus.UNAVAILABLE
                cap.failure_count += 1
                cap.confidence = max(0.0, cap.confidence - 0.2)
                probed.append(cap)
                logger.warning(f"[CapabilityProber] {name} probe failed: {e}")

        self._last_probe = datetime.now(UTC)
        self._probe_count += 1
        return probed

    def discover_boundaries(self) -> list[BoundaryFinding]:
        findings: list[BoundaryFinding] = []

        for name, cap in self._capabilities.items():
            if cap.confidence < self.min_confidence and cap.status != CapabilityStatus.UNTESTED:
                findings.append(BoundaryFinding(
                    capability_name=name,
                    category=cap.category,
                    boundary_type="soft_limit",
                    description=f"Low confidence ({cap.confidence:.2f}) in capability",
                    confidence=1.0 - cap.confidence,
                    suggested_action=f"Improve {name} through practice or training",
                ))

            if cap.status == CapabilityStatus.UNAVAILABLE:
                findings.append(BoundaryFinding(
                    capability_name=name,
                    category=cap.category,
                    boundary_type="hard_limit",
                    description=f"Capability {name} is not available",
                    confidence=0.9,
                    suggested_action=f"Find alternative to {name} or acquire dependency",
                ))

            if cap.test_count == 0:
                findings.append(BoundaryFinding(
                    capability_name=name,
                    category=cap.category,
                    boundary_type="unknown_area",
                    description=f"Capability {name} has never been tested",
                    confidence=0.5,
                    suggested_action=f"Test {name} to determine its boundaries",
                ))

            if cap.limitations:
                for lim in cap.limitations:
                    findings.append(BoundaryFinding(
                        capability_name=name,
                        category=cap.category,
                        boundary_type="soft_limit",
                        description=f"Limited: {lim}",
                        confidence=0.8,
                        suggested_action=f"Work around limitation: {lim}",
                    ))

            if cap.success_rate < 0.5 and cap.test_count >= 3:
                findings.append(BoundaryFinding(
                    capability_name=name,
                    category=cap.category,
                    boundary_type="soft_limit",
                    description=f"Low success rate ({cap.success_rate:.1%}) indicates unreliability",
                    confidence=0.7,
                    suggested_action=f"Improve {name} reliability or avoid using it",
                ))

        self._boundaries.extend(findings)
        if len(self._boundaries) > 1000:
            self._boundaries = self._boundaries[-500:]

        return findings

    def get_capability(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def get_capabilities_by_category(self, category: CapabilityCategory) -> list[Capability]:
        return [cap for cap in self._capabilities.values() if cap.category == category]

    def get_available_capabilities(self) -> list[str]:
        return [
            name for name, cap in self._capabilities.items()
            if cap.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.DEGRADED)
            and cap.confidence >= self.min_confidence
        ]

    def get_unknown_areas(self) -> list[str]:
        return [
            name for name, cap in self._capabilities.items()
            if cap.status == CapabilityStatus.UNKNOWN
            or cap.test_count == 0
        ]

    def check_capability_available(self, name: str) -> tuple[bool, str]:
        cap = self._capabilities.get(name)
        if cap is None:
            return False, f"Capability {name} is not registered"
        if cap.status == CapabilityStatus.UNAVAILABLE:
            return False, f"Capability {name} is unavailable"
        if cap.confidence < self.min_confidence:
            return False, f"Capability {name} has low confidence ({cap.confidence:.2f})"
        return True, "Capability is available"

    def get_report(self) -> dict[str, Any]:
        by_category: dict[str, list[str]] = {}
        for cap in self._capabilities.values():
            cat = cap.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(cap.name)

        by_status: dict[str, int] = {}
        for cap in self._capabilities.values():
            status = cap.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_capabilities": len(self._capabilities),
            "by_category": by_category,
            "by_status": by_status,
            "available_count": len(self.get_available_capabilities()),
            "unknown_count": len(self.get_unknown_areas()),
            "boundary_findings": len(self._boundaries),
            "last_probe": self._last_probe.isoformat() if self._last_probe else None,
            "probe_count": self._probe_count,
            "recent_boundaries": [
                {
                    "capability": b.capability_name,
                    "type": b.boundary_type,
                    "description": b.description,
                }
                for b in self._boundaries[-10:]
            ],
        }

    def suggest_improvements(self) -> list[dict[str, Any]]:
        suggestions = []

        for name, cap in self._capabilities.items():
            if cap.confidence < self.min_confidence and cap.test_count > 0:
                suggestions.append({
                    "capability": name,
                    "action": "improve",
                    "reason": f"Confidence too low ({cap.confidence:.2f})",
                    "suggestion": f"Practice {name} more to increase success rate",
                })

            if cap.test_count == 0:
                suggestions.append({
                    "capability": name,
                    "action": "test",
                    "reason": "Never tested",
                    "suggestion": f"Run probe on {name} to determine capability",
                })

            if cap.status == CapabilityStatus.DEGRADED:
                suggestions.append({
                    "capability": name,
                    "action": "repair",
                    "reason": "Capability is degraded",
                    "suggestion": f"Investigate why {name} is degraded",
                })

        return suggestions
