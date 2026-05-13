"""Unified governance gate combining policy, boundary management, rate limiting, and quota.

The GovernanceGate is the primary facade for all governance decisions.
It coordinates policy evaluation, boundary management, rate limiting,
and quota enforcement into a single check pattern.

Philosophy: Agent autonomously manages boundaries. No supervised mode.
Human role: post-hoc audit only via `agpt audit` and `agpt breaks`.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any

from .audit import AuditEntry, AuditEventType, AuditLog
from .boundary_manager import BoundaryManager, ConstraintKind
from .policy import PolicyEffect, PolicyEvaluator
from .quota import QuotaManager
from .rate_limit import RateLimiter


@dataclass
class GovernanceDecision:
    """Result of a governance gate check."""

    allowed: bool
    operation: str = ""
    principal: str = ""
    resource: str = ""
    reason: str = ""


class GovernanceGate:
    """Unified governance facade with autonomous boundary management.

    Coordinates:
      1. Boundary management (Agent sets/adjusts/breaks boundaries)
      2. Policy evaluation (allow/deny based on Agent-managed rules)
      3. Rate limiting (Agent-adjustable token buckets)
      4. Quota enforcement (resource consumption limits)
      5. Audit logging (records all decisions for post-hoc review)

    No supervised mode. No approval workflow. All decisions are autonomous.
    """

    def __init__(
        self,
        policy_evaluator: PolicyEvaluator | None = None,
        rate_limiter: RateLimiter | None = None,
        quota_manager: QuotaManager | None = None,
        audit_log: AuditLog | None = None,
        hard_boundaries: set[str] | None = None,
        boundary_manager: BoundaryManager | None = None,
        agent_id: str = "auto-gpt",
    ) -> None:
        self.policy = policy_evaluator or PolicyEvaluator()
        self.rates = rate_limiter or RateLimiter()
        self.quotas = quota_manager or QuotaManager()
        self.audit = audit_log or AuditLog()
        self.hard_boundaries = hard_boundaries or {"budget_exceeded", "file_delete", "sandbox_escape"}
        self.boundary = boundary_manager or BoundaryManager(
            agent_id=agent_id, audit_log=self.audit,
        )

    def _is_hard_boundary(self, operation: str, risk_level: str) -> bool:
        """Check if an operation hits a hard boundary.

        Hard boundaries are operations that MUST be blocked even in
        autonomous mode (budget exceeded, destructive file ops, sandbox escape).
        """
        for boundary in self.hard_boundaries:
            if fnmatch.fnmatch(operation, boundary):
                return True
        if risk_level == "critical" and "file_delete" in self.hard_boundaries:
            return True
        return False

    def check(
        self,
        operation: str,
        principal: str = "*",
        resource: str = "*",
        context: dict[str, Any] | None = None,
        risk_level: str = "medium",
        token_cost: float = 1.0,
        quota_resource: str | None = None,
        quota_amount: float = 1.0,
    ) -> GovernanceDecision:
        """Evaluate governance controls for an operation.

        Autonomous-only model (audit-net philosophy):
          - BoundaryManager sets/adjusts/breaks constraints
          - Default ALLOW: most operations proceed automatically
          - Audit everything: every decision is recorded
          - Hard boundaries only trigger a hard block
          - Soft controls degrade gracefully: log warning, still ALLOW
          - No approval workflow: Agent decides, human audits post-hoc
        """
        effect, policy_name = self.policy.evaluate(
            operation, principal, resource, context
        )

        return self._check_autonomous(
            operation=operation,
            principal=principal,
            resource=resource,
            context=context,
            risk_level=risk_level,
            token_cost=token_cost,
            quota_resource=quota_resource,
            quota_amount=quota_amount,
            policy_effect=effect,
            policy_name=policy_name,
        )

    def _check_autonomous(
        self,
        operation: str,
        principal: str,
        resource: str,
        context: dict[str, Any] | None,
        risk_level: str,
        token_cost: float,
        quota_resource: str | None,
        quota_amount: float,
        policy_effect: PolicyEffect,
        policy_name: str,
    ) -> GovernanceDecision:
        """Autonomous check: audit-net philosophy with boundary management.

        1. Hard boundary -> BLOCK (unconditional)
        2. Policy DENY + hard boundary pattern -> BLOCK
        3. Everything else -> ALLOW (with audit record)
        4. Soft controls (rate, quota) -> audit warning, still ALLOW
        5. BoundaryManager handles constraint enforcement
        """
        if self._is_hard_boundary(operation, risk_level):
            self.audit.record(
                AuditEventType.OPERATION_BLOCKED,
                principal=principal,
                operation=operation,
                resource=resource,
                decision="hard_boundary_block",
                details={"boundary": operation, "risk_level": risk_level},
            )
            return GovernanceDecision(
                allowed=False,
                operation=operation,
                principal=principal,
                resource=resource,
                reason=f"Hard boundary: '{operation}' is blocked in autonomous mode",
            )

        if policy_effect == PolicyEffect.DENY and self._is_hard_boundary(operation, risk_level):
            self.audit.record(
                AuditEventType.OPERATION_BLOCKED,
                principal=principal,
                operation=operation,
                resource=resource,
                decision="denied_by_policy_hard",
                details={"policy": policy_name},
            )
            return GovernanceDecision(
                allowed=False,
                operation=operation,
                principal=principal,
                resource=resource,
                reason=f"Denied by policy '{policy_name}' (hard boundary)",
            )

        soft_warnings: list[str] = []

        if policy_effect == PolicyEffect.DENY:
            soft_warnings.append(f"policy_deny_override:{policy_name}")

        if not self.rates.check(operation, principal, token_cost):
            soft_warnings.append("rate_limit_exceeded")

        if quota_resource is not None:
            if not self.quotas.check(quota_resource, quota_amount, principal, operation):
                soft_warnings.append(f"quota_exceeded:{quota_resource}")

        self.audit.record(
            AuditEventType.POLICY_EVAL,
            principal=principal,
            operation=operation,
            resource=resource,
            decision="autonomous_allowed",
            details={
                "mode": "autonomous",
                "policy": policy_name,
                "policy_effect": policy_effect.value,
                "risk_level": risk_level,
                "soft_warnings": soft_warnings,
            },
        )

        return GovernanceDecision(
            allowed=True,
            operation=operation,
            principal=principal,
            resource=resource,
            reason="Autonomous mode: allowed (audit-net)"
            + (f" | warnings: {soft_warnings}" if soft_warnings else ""),
        )

    def init_boundaries(
        self,
        task_goal: str = "",
        environment_hints: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Agent-autonomous boundaries. Call once at startup."""
        self.boundary.autonomous_init(
            task_goal=task_goal,
            environment_hints=environment_hints,
        )
