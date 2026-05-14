"""Policy auto-evolution engine.

Analyzes audit log data to automatically adjust governance parameters:
- Rate limit refill rates and burst capacities
- Quota limits based on consumption patterns

Philosophy: the system learns from its own operational data. All adjustments
are applied immediately (self-evolve, self-apply). No human approval needed.
Adjustments are audited for post-hoc review.

All adjustments are bounded to prevent runaway evolution.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .audit import AuditEntry, AuditEventType, AuditLog
from .policy import PolicyEffect, PolicyEvaluator, Policy, PolicyRule
from .quota import QuotaDefinition, QuotaManager
from .rate_limit import RateLimitRule, RateLimiter


@dataclass
class EvolutionConfig:
    """Configuration bounds for policy evolution.

    All adjustments are clamped to these ranges to prevent runaway evolution.
    """
    min_refill_rate: float = 0.1
    max_refill_rate: float = 100.0
    min_burst: float = 1.0
    max_burst: float = 1000.0
    min_quota_limit: float = 10.0
    max_quota_multiplier: float = 5.0
    rate_adjust_factor: float = 1.2
    quota_adjust_factor: float = 1.1
    risk_promotion_threshold: float = 0.95
    risk_demotion_threshold: float = 0.3
    min_sample_size: int = 20
    cooldown_seconds: float = 3600.0


@dataclass
class EvolutionResult:
    """Result of a single evolution step."""
    timestamp: str = ""
    adjustments: list[dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class PolicyEvolver:
    """Auto-evolve governance parameters based on operational data.

    Usage:
        evolver = PolicyEvolver(gate=gate, audit_log=gate.audit)
        result = evolver.evolve()

    The evolver reads recent audit entries, computes statistics,
    and applies bounded adjustments to rate limits, quotas, and
    approval thresholds.
    """

    def __init__(
        self,
        gate: Any | None = None,
        audit_log: AuditLog | None = None,
        config: EvolutionConfig | None = None,
    ) -> None:
        from .gate import GovernanceGate
        self.gate: GovernanceGate | None = gate
        self.audit = audit_log or (gate.audit if gate else AuditLog())
        self.config = config or EvolutionConfig()
        self._last_evolution: str = ""
        self._lock = threading.Lock()

    def evolve(self, lookback_hours: float = 24.0) -> EvolutionResult:
        """Run one evolution step based on recent audit data.

        Returns an EvolutionResult describing what was adjusted.
        Thread-safe: only one evolution can run at a time.
        """
        with self._lock:
            if not self._check_cooldown():
                return EvolutionResult(
                    skipped=True,
                    reason="Cooldown period not elapsed since last evolution",
                )

            if self.gate is None:
                return EvolutionResult(
                    skipped=True,
                    reason="No governance gate attached",
                )

            since = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
            entries = self.audit.query(since=since, limit=10000)

            if len(entries) < self.config.min_sample_size:
                return EvolutionResult(
                    skipped=True,
                    reason=f"Insufficient data: {len(entries)} < {self.config.min_sample_size}",
                )

            adjustments: list[dict[str, Any]] = []
            adjustments.extend(self._evolve_rate_limits(entries))
            adjustments.extend(self._evolve_quotas(entries))

            if adjustments:
                self._last_evolution = datetime.now(timezone.utc).isoformat()
                for adj in adjustments:
                    self.audit.record(
                        AuditEventType.POLICY_AUTO_ADJUSTED,
                        operation="policy_evolution",
                        decision="adjusted",
                        details=adj,
                    )

            return EvolutionResult(adjustments=adjustments)

    def _check_cooldown(self) -> bool:
        if not self._last_evolution:
            return True
        last = datetime.fromisoformat(self._last_evolution)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed >= self.config.cooldown_seconds

    def _evolve_rate_limits(self, entries: list[AuditEntry]) -> list[dict[str, Any]]:
        """Adjust rate limit parameters based on hit patterns.

        Strategy:
        - If a rate limit is frequently exceeded but all operations were
          allowed (autonomous override), increase refill_rate by the factor.
        - If a rate limit is never exceeded, optionally decrease burst
          to reclaim capacity (conservative: skip).
        """
        if self.gate is None:
            return []

        adjustments: list[dict[str, Any]] = []
        rate_limited = [e for e in entries if e.event_type == "rate_limited"]
        autonomous_overrides = [
            e for e in entries
            if e.event_type == "policy_eval"
            and e.details.get("mode") == "autonomous"
            and "rate_limit_exceeded" in e.details.get("soft_warnings", [])
        ]

        if not rate_limited and not autonomous_overrides:
            return adjustments

        for rule in list(self.gate.rates._rules):
            matching_overrides = [
                o for o in autonomous_overrides
                if o.operation == rule.operation or o.operation == "*"
            ]
            if len(matching_overrides) >= self.config.min_sample_size:
                old_rate = rule.refill_rate
                new_rate = min(
                    old_rate * self.config.rate_adjust_factor,
                    self.config.max_refill_rate,
                )
                if new_rate != old_rate:
                    idx = self.gate.rates._rules.index(rule)
                    self.gate.rates._rules[idx] = RateLimitRule(
                        operation=rule.operation,
                        principal=rule.principal,
                        max_burst=rule.max_burst,
                        refill_rate=new_rate,
                        scope=rule.scope,
                    )
                    self.gate.rates._buckets.clear()
                    adjustments.append({
                        "type": "rate_limit_refill",
                        "operation": rule.operation,
                        "principal": rule.principal,
                        "old_refill_rate": old_rate,
                        "new_refill_rate": new_rate,
                        "evidence_count": len(matching_overrides),
                    })

        return adjustments

    def _evolve_quotas(self, entries: list[AuditEntry]) -> list[dict[str, Any]]:
        """Adjust quota limits based on consumption patterns.

        Strategy:
        - If quota is frequently exceeded but operations are allowed
          (autonomous override), increase the limit by the factor.
        - Cap at max_quota_multiplier * original_limit.
        """
        if self.gate is None:
            return []

        adjustments: list[dict[str, Any]] = []
        quota_exceeded = [e for e in entries if e.event_type == "quota_exceeded"]
        autonomous_overrides = [
            e for e in entries
            if e.event_type == "policy_eval"
            and e.details.get("mode") == "autonomous"
            and any(
                w.startswith("quota_exceeded:")
                for w in e.details.get("soft_warnings", [])
            )
        ]

        if not quota_exceeded and not autonomous_overrides:
            return adjustments

        for resource, definition in list(self.gate.quotas._definitions.items()):
            matching = [
                o for o in autonomous_overrides
                if any(
                    w == f"quota_exceeded:{resource}"
                    for w in o.details.get("soft_warnings", [])
                )
            ]
            if len(matching) >= self.config.min_sample_size // 2:
                old_limit = definition.limit
                new_limit = min(
                    old_limit * self.config.quota_adjust_factor,
                    old_limit * self.config.max_quota_multiplier,
                )
                if new_limit > old_limit:
                    self.gate.quotas._definitions[resource] = QuotaDefinition(
                        resource=definition.resource,
                        limit=new_limit,
                        period_seconds=definition.period_seconds,
                        scope=definition.scope,
                        operation=definition.operation,
                        principal=definition.principal,
                    )
                    adjustments.append({
                        "type": "quota_limit",
                        "resource": resource,
                        "old_limit": old_limit,
                        "new_limit": new_limit,
                        "evidence_count": len(matching),
                    })

        return adjustments

    def get_evolution_summary(self, lookback_hours: float = 168.0) -> dict[str, Any]:
        """Get a summary of evolution adjustments over the lookback period."""
        since = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
        entries = self.audit.query(
            event_type=AuditEventType.POLICY_AUTO_ADJUSTED,
            since=since,
            limit=1000,
        )
        by_type: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            adj_type = entry.details.get("type", "unknown")
            by_type.setdefault(adj_type, []).append(entry.details)
        return {
            "total_adjustments": len(entries),
            "by_type": by_type,
            "last_evolution": self._last_evolution,
        }

    def evolve_from_cycle(self, fixed_count: int = 0, failed_count: int = 0) -> list[dict[str, Any]]:
        """Trigger policy evolution from a self-improvement cycle outcome.

        If fixes are succeeding, loosen rate limits slightly.
        If fixes are failing, tighten approval by adding risk levels.
        """
        adjustments: list[dict[str, Any]] = []

        if fixed_count > 0 and failed_count == 0:
            if self.gate is not None:
                for i, rule in enumerate(list(self.gate.rates._rules)):
                    old_rate = rule.refill_rate
                    new_rate = min(
                        old_rate * 1.05,
                        self.config.max_refill_rate,
                    )
                    if new_rate != old_rate:
                        from .rate_limit import RateLimitRule
                        self.gate.rates._rules[i] = RateLimitRule(
                            operation=rule.operation,
                            principal=rule.principal,
                            max_burst=rule.max_burst,
                            refill_rate=new_rate,
                            scope=rule.scope,
                        )
                        adjustments.append({
                            "type": "rate_limit_relax",
                            "operation": rule.operation,
                            "old_refill_rate": old_rate,
                            "new_refill_rate": new_rate,
                            "reason": "all_fixes_succeeded",
                        })
                self.gate.rates._buckets.clear()

        elif failed_count > fixed_count:
            if self.gate is not None:
                for rule in list(self.gate.rates._rules):
                    old_rate = rule.refill_rate
                    new_rate = max(
                        old_rate * 0.8,
                        self.config.min_refill_rate,
                    )
                    if new_rate != old_rate:
                        from .rate_limit import RateLimitRule
                        idx = self.gate.rates._rules.index(rule)
                        self.gate.rates._rules[idx] = RateLimitRule(
                            operation=rule.operation,
                            principal=rule.principal,
                            max_burst=rule.max_burst,
                            refill_rate=new_rate,
                            scope=rule.scope,
                        )
                        adjustments.append({
                            "type": "rate_limit_tighten",
                            "operation": rule.operation,
                            "old_refill_rate": old_rate,
                            "new_refill_rate": new_rate,
                            "reason": "more_failures_than_fixes",
                        })
                self.gate.rates._buckets.clear()

        if adjustments:
            self.audit.record(
                AuditEventType.POLICY_AUTO_ADJUSTED,
                principal="policy_evolver",
                operation="evolve_from_cycle",
                details={
                    "fixed_count": fixed_count,
                    "failed_count": failed_count,
                    "adjustments": adjustments,
                },
            )

        return adjustments
