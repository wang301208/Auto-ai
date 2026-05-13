"""Agent-autonomous boundary management.

The BoundaryManager implements the core principle: Agent sets its own boundaries,
Agent adjusts its own boundaries, Agent breaks its own boundaries.

Human role: post-hoc audit only. No pre-approval, no real-time intervention.

Three lifecycle phases:
  1. autonomous_init()  - Agent defines initial constraints from task + experience
  2. autonomous_adjust() - Agent dynamically tunes constraints during execution
  3. autonomous_break()  - Agent breaks constraints when they block goal achievement

All decisions are recorded to an immutable audit chain for post-hoc review.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .audit import AuditEntry, AuditEventType, AuditLog
from .autonomy_level import AutonomyLevel, AutonomyManager
from .break_log import BreakLog, BreakRecord
from .modification_chain import ModificationChain, ModificationType, ModificationStatus


class ConstraintKind(Enum):
    TOKEN_BUDGET = "token_budget"
    FILE_WRITE_SCOPE = "file_write_scope"
    FILE_READ_SCOPE = "file_read_scope"
    NETWORK_ACCESS = "network_access"
    SHELL_EXECUTE = "shell_execute"
    SANDBOX_STRICTNESS = "sandbox_strictness"
    TIME_BUDGET = "time_budget"
    MODEL_TIER = "model_tier"
    SELF_MODIFY = "self_modify"
    AGENT_SPAWN = "agent_spawn"


@dataclass
class Constraint:
    kind: ConstraintKind
    value: Any
    min_value: Any = None
    max_value: Any = None
    adjustable: bool = True
    breakable: bool = True
    reason: str = ""


@dataclass
class ConstraintSet:
    agent_id: str = ""
    timestamp: str = ""
    constraints: dict[ConstraintKind, Constraint] = field(default_factory=dict)
    autonomy_level: int = 2

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def get(self, kind: ConstraintKind) -> Constraint | None:
        return self.constraints.get(kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "constraints": {
                k.value: {
                    "kind": v.kind.value,
                    "value": v.value,
                    "min_value": v.min_value,
                    "max_value": v.max_value,
                    "adjustable": v.adjustable,
                    "breakable": v.breakable,
                    "reason": v.reason,
                }
                for k, v in self.constraints.items()
            },
            "autonomy_level": self.autonomy_level,
        }


SEED_CONSTRAINTS: dict[ConstraintKind, dict[str, Any]] = {
    ConstraintKind.TOKEN_BUDGET: {"value": 100000, "min_value": 1000, "max_value": 10000000, "adjustable": True, "breakable": True},
    ConstraintKind.FILE_WRITE_SCOPE: {"value": ["workspace"], "min_value": None, "max_value": None, "adjustable": True, "breakable": True},
    ConstraintKind.FILE_READ_SCOPE: {"value": ["*"], "min_value": None, "max_value": None, "adjustable": True, "breakable": False},
    ConstraintKind.NETWORK_ACCESS: {"value": True, "min_value": False, "max_value": True, "adjustable": True, "breakable": True},
    ConstraintKind.SHELL_EXECUTE: {"value": "sandboxed", "min_value": "disabled", "max_value": "unsandboxed", "adjustable": True, "breakable": True},
    ConstraintKind.SANDBOX_STRICTNESS: {"value": "standard", "min_value": "relaxed", "max_value": "strict", "adjustable": True, "breakable": True},
    ConstraintKind.TIME_BUDGET: {"value": 3600, "min_value": 60, "max_value": 86400, "adjustable": True, "breakable": True},
    ConstraintKind.MODEL_TIER: {"value": "balanced", "min_value": "fast", "max_value": "smart", "adjustable": True, "breakable": True},
    ConstraintKind.SELF_MODIFY: {"value": True, "min_value": False, "max_value": True, "adjustable": True, "breakable": True},
    ConstraintKind.AGENT_SPAWN: {"value": False, "min_value": False, "max_value": True, "adjustable": True, "breakable": True},
}

AUTONOMY_PRESETS: dict[int, dict[ConstraintKind, Any]] = {
    0: {
        ConstraintKind.TOKEN_BUDGET: 5000,
        ConstraintKind.SELF_MODIFY: False,
        ConstraintKind.AGENT_SPAWN: False,
        ConstraintKind.SHELL_EXECUTE: "disabled",
        ConstraintKind.SANDBOX_STRICTNESS: "strict",
    },
    1: {
        ConstraintKind.TOKEN_BUDGET: 20000,
        ConstraintKind.SELF_MODIFY: False,
        ConstraintKind.AGENT_SPAWN: False,
        ConstraintKind.SHELL_EXECUTE: "sandboxed",
        ConstraintKind.SANDBOX_STRICTNESS: "strict",
    },
    2: {
        ConstraintKind.TOKEN_BUDGET: 100000,
        ConstraintKind.SELF_MODIFY: True,
        ConstraintKind.AGENT_SPAWN: False,
        ConstraintKind.SHELL_EXECUTE: "sandboxed",
        ConstraintKind.SANDBOX_STRICTNESS: "standard",
    },
    3: {
        ConstraintKind.TOKEN_BUDGET: 500000,
        ConstraintKind.SELF_MODIFY: True,
        ConstraintKind.AGENT_SPAWN: False,
        ConstraintKind.SHELL_EXECUTE: "sandboxed",
        ConstraintKind.SANDBOX_STRICTNESS: "standard",
    },
    4: {
        ConstraintKind.TOKEN_BUDGET: 1000000,
        ConstraintKind.SELF_MODIFY: True,
        ConstraintKind.AGENT_SPAWN: True,
        ConstraintKind.SHELL_EXECUTE: "sandboxed",
        ConstraintKind.SANDBOX_STRICTNESS: "relaxed",
    },
    5: {
        ConstraintKind.TOKEN_BUDGET: 10000000,
        ConstraintKind.SELF_MODIFY: True,
        ConstraintKind.AGENT_SPAWN: True,
        ConstraintKind.SHELL_EXECUTE: "unsandboxed",
        ConstraintKind.SANDBOX_STRICTNESS: "relaxed",
    },
}


class BoundaryManager:
    """Agent-autonomous boundary management: set / adjust / break.

    Human role: post-hoc audit via `agpt audit` and `agpt breaks`.
    No human participates in any boundary decision at runtime.
    """

    ADJUST_GRADIENT = 0.3
    GRADIENT_ESCALATION_STEPS = 3

    def __init__(
        self,
        agent_id: str = "auto-gpt",
        audit_log: AuditLog | None = None,
        break_log: BreakLog | None = None,
        modification_chain: ModificationChain | None = None,
        autonomy_manager: AutonomyManager | None = None,
        experience_store: Any | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.audit = audit_log or AuditLog()
        self.break_log = break_log or BreakLog()
        self.chain = modification_chain
        self.autonomy = autonomy_manager or AutonomyManager(agent_id=agent_id)
        self.experience = experience_store
        self._current: ConstraintSet | None = None
        self._adjust_history: list[dict[str, Any]] = []
        self._break_count: int = 0
        self._lock = threading.Lock()

    @property
    def constraints(self) -> ConstraintSet | None:
        return self._current

    def autonomous_init(
        self,
        task_goal: str = "",
        environment_hints: dict[str, Any] | None = None,
    ) -> ConstraintSet:
        """Phase 1: Agent autonomously defines initial constraints.

        No human input. Constraints derived from:
          - Autonomy level presets
          - Experience store (similar task historical constraints)
          - Environment hints (available models, disk, network)
        """
        with self._lock:
            level = self.autonomy.level
            cs = ConstraintSet(
                agent_id=self.agent_id,
                autonomy_level=level,
            )

            for kind, seed in SEED_CONSTRAINTS.items():
                cs.constraints[kind] = Constraint(
                    kind=kind,
                    value=seed["value"],
                    min_value=seed.get("min_value"),
                    max_value=seed.get("max_value"),
                    adjustable=seed.get("adjustable", True),
                    breakable=seed.get("breakable", True),
                    reason="seed_default",
                )

            preset = AUTONOMY_PRESETS.get(level, {})
            for kind, value in preset.items():
                if kind in cs.constraints:
                    cs.constraints[kind] = Constraint(
                        kind=kind,
                        value=value,
                        min_value=cs.constraints[kind].min_value,
                        max_value=cs.constraints[kind].max_value,
                        adjustable=cs.constraints[kind].adjustable,
                        breakable=cs.constraints[kind].breakable,
                        reason=f"autonomy_preset_L{level}",
                    )

            if self.experience is not None:
                exp_constraints = self._load_experience_constraints(task_goal)
                for kind, value in exp_constraints.items():
                    if kind in cs.constraints:
                        cs.constraints[kind] = Constraint(
                            kind=kind,
                            value=value,
                            min_value=cs.constraints[kind].min_value,
                            max_value=cs.constraints[kind].max_value,
                            adjustable=cs.constraints[kind].adjustable,
                            breakable=cs.constraints[kind].breakable,
                            reason="experience_store",
                        )

            if environment_hints:
                self._apply_env_hints(cs, environment_hints)

            self._current = cs

            self.audit.record(
                AuditEventType.POLICY_EVAL,
                principal=self.agent_id,
                operation="boundary_init",
                decision="constraints_set",
                details={
                    "autonomy_level": level,
                    "constraint_count": len(cs.constraints),
                    "task_goal": task_goal[:200],
                    "constraints": cs.to_dict()["constraints"],
                },
            )

            return cs

    def autonomous_adjust(
        self,
        adjustments: dict[ConstraintKind, Any],
        reason: str = "",
    ) -> ConstraintSet:
        """Phase 2: Agent autonomously adjusts constraints.

        Each adjustment is capped by the gradient: ±30% of current value
        (or ±30% for numeric, direct set for enum/bool).
        After 3 consecutive same-direction adjustments, gradient widens.
        """
        with self._lock:
            if self._current is None:
                raise RuntimeError("Constraints not initialized. Call autonomous_init() first.")

            applied: dict[str, Any] = {}
            for kind, new_value in adjustments.items():
                c = self._current.constraints.get(kind)
                if c is None:
                    continue
                if not c.adjustable:
                    continue

                if isinstance(c.value, (int, float)) and isinstance(new_value, (int, float)):
                    adjusted = self._apply_numeric_gradient(c, new_value)
                else:
                    adjusted = new_value

                old_value = c.value
                self._current.constraints[kind] = Constraint(
                    kind=kind,
                    value=adjusted,
                    min_value=c.min_value,
                    max_value=c.max_value,
                    adjustable=c.adjustable,
                    breakable=c.breakable,
                    reason=reason or "autonomous_adjust",
                )
                applied[kind.value] = {"old": old_value, "new": adjusted, "reason": reason}

            if applied:
                self._adjust_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "adjustments": applied,
                })

                self.audit.record(
                    AuditEventType.POLICY_AUTO_ADJUSTED,
                    principal=self.agent_id,
                    operation="boundary_adjust",
                    decision="constraints_adjusted",
                    details=applied,
                )

            return self._current

    def autonomous_break(
        self,
        kind: ConstraintKind,
        new_value: Any,
        goal_value: float = 0.0,
        break_risk: float = 0.0,
        alternative_paths: list[str] | None = None,
    ) -> BreakRecord:
        """Phase 3: Agent autonomously breaks a constraint boundary.

        Decision algorithm:
          if goal_value * historical_success > break_risk * risk_multiplier:
              execute break + trigger compensation
          else:
              seek alternative path

        Risk multiplier increases with break frequency to ensure convergence.
        """
        with self._lock:
            if self._current is None:
                raise RuntimeError("Constraints not initialized. Call autonomous_init() first.")

            c = self._current.constraints.get(kind)
            if c is None:
                raise ValueError(f"Unknown constraint kind: {kind}")

            if not c.breakable:
                return self.break_log.record(
                    constraint_kind=kind.value,
                    old_value=c.value,
                    new_value=new_value,
                    goal_value=goal_value,
                    break_risk=break_risk,
                    risk_multiplier=self._compute_risk_multiplier(),
                    decision="blocked_unbreakable",
                    compensation={},
                    alternative_paths=alternative_paths or [],
                    agent_id=self.agent_id,
                )

            risk_multiplier = self._compute_risk_multiplier()
            historical_success = self._query_break_success_rate(kind)

            should_break = (goal_value * historical_success) > (break_risk * risk_multiplier)

            if should_break:
                old_value = c.value
                self._current.constraints[kind] = Constraint(
                    kind=kind,
                    value=new_value,
                    min_value=c.min_value,
                    max_value=c.max_value,
                    adjustable=c.adjustable,
                    breakable=c.breakable,
                    reason="boundary_break",
                )
                self._break_count += 1

                compensation = self._trigger_compensation(kind)

                record = self.break_log.record(
                    constraint_kind=kind.value,
                    old_value=old_value,
                    new_value=new_value,
                    goal_value=goal_value,
                    break_risk=break_risk,
                    risk_multiplier=risk_multiplier,
                    decision="break_executed",
                    compensation=compensation,
                    alternative_paths=alternative_paths or [],
                    agent_id=self.agent_id,
                )

                self.audit.record(
                    AuditEventType.OPERATION_EXECUTED,
                    principal=self.agent_id,
                    operation=f"boundary_break:{kind.value}",
                    decision="break_executed",
                    details={
                        "old_value": old_value,
                        "new_value": new_value,
                        "goal_value": goal_value,
                        "break_risk": break_risk,
                        "risk_multiplier": risk_multiplier,
                        "compensation": compensation,
                    },
                )

                return record
            else:
                record = self.break_log.record(
                    constraint_kind=kind.value,
                    old_value=c.value,
                    new_value=new_value,
                    goal_value=goal_value,
                    break_risk=break_risk,
                    risk_multiplier=risk_multiplier,
                    decision="break_rejected_risk_too_high",
                    compensation={},
                    alternative_paths=alternative_paths or [],
                    agent_id=self.agent_id,
                )

                self.audit.record(
                    AuditEventType.OPERATION_BLOCKED,
                    principal=self.agent_id,
                    operation=f"boundary_break:{kind.value}",
                    decision="break_rejected_risk_too_high",
                    details={
                        "goal_value": goal_value,
                        "break_risk": break_risk,
                        "risk_multiplier": risk_multiplier,
                    },
                )

                return record

    def check_constraint(self, kind: ConstraintKind, value: Any) -> bool:
        """Check if a value is within the current constraint boundary."""
        with self._lock:
            if self._current is None:
                return True
            c = self._current.constraints.get(kind)
            if c is None:
                return True
            return c.value == value or self._is_within_bound(c, value)

    def _is_within_bound(self, c: Constraint, value: Any) -> bool:
        if isinstance(value, (int, float)) and isinstance(c.value, (int, float)):
            if c.min_value is not None and value < c.min_value:
                return False
            if c.max_value is not None and value > c.max_value:
                return False
            return True
        return value == c.value

    def _apply_numeric_gradient(self, c: Constraint, proposed: float) -> float:
        current = float(c.value)
        delta = proposed - current
        max_delta = abs(current) * self._compute_effective_gradient()
        clamped_delta = max(-max_delta, min(delta, max_delta))
        result = current + clamped_delta
        if c.min_value is not None:
            result = max(float(c.min_value), result)
        if c.max_value is not None:
            result = min(float(c.max_value), result)
        if result <= 0 and current > 0:
            result = current * (1 - self._compute_effective_gradient())
        return max(result, float(c.min_value) if c.min_value is not None else 0.001)

    def _compute_effective_gradient(self) -> float:
        if len(self._adjust_history) < self.GRADIENT_ESCALATION_STEPS:
            return self.ADJUST_GRADIENT
        recent = self._adjust_history[-self.GRADIENT_ESCALATION_STEPS:]
        kinds_sets = [set(a.get("adjustments", {}).keys()) for a in recent]
        if all(k == kinds_sets[0] for k in kinds_sets) and kinds_sets[0]:
            return min(self.ADJUST_GRADIENT * 2.0, 0.8)
        return self.ADJUST_GRADIENT

    def _compute_risk_multiplier(self) -> float:
        base = 1.0
        growth = 0.5
        return base + growth * self._break_count

    def _trigger_compensation(self, broken_kind: ConstraintKind) -> dict[str, Any]:
        """After a break, automatically tighten other constraints and increase monitoring."""
        compensation: dict[str, Any] = {}
        if self._current is None:
            return compensation

        tightening_map: dict[ConstraintKind, Any] = {
            ConstraintKind.TOKEN_BUDGET: 0.8,
            ConstraintKind.SANDBOX_STRICTNESS: "strict",
            ConstraintKind.SHELL_EXECUTE: "sandboxed",
        }
        tightening_map.pop(broken_kind, None)

        for kind, adjustment in tightening_map.items():
            c = self._current.constraints.get(kind)
            if c is None:
                continue
            old = c.value
            if isinstance(adjustment, float) and isinstance(old, (int, float)):
                new = old * adjustment
            else:
                new = adjustment
            self._current.constraints[kind] = Constraint(
                kind=kind,
                value=new,
                min_value=c.min_value,
                max_value=c.max_value,
                adjustable=c.adjustable,
                breakable=c.breakable,
                reason="compensation_after_break",
            )
            compensation[kind.value] = {"old": old, "new": new}

        compensation["monitor_frequency_increased"] = True
        compensation["session_risk_level"] = "high" if self._break_count > 2 else "elevated"
        return compensation

    def _query_break_success_rate(self, kind: ConstraintKind) -> float:
        records = self.break_log.query(constraint_kind=kind.value)
        if not records:
            return 0.5
        executed = [r for r in records if r.decision == "break_executed"]
        if not executed:
            return 0.5
        return len(executed) / len(records)

    def _load_experience_constraints(self, task_goal: str) -> dict[ConstraintKind, Any]:
        if self.experience is None:
            return {}
        try:
            if hasattr(self.experience, "query_similar"):
                results = self.experience.query_similar(task_goal, top_k=3)
                if results:
                    best = results[0]
                    if isinstance(best, dict) and "constraints" in best:
                        loaded: dict[ConstraintKind, Any] = {}
                        for k, v in best["constraints"].items():
                            try:
                                loaded[ConstraintKind(k)] = v
                            except ValueError:
                                pass
                        return loaded
        except Exception:
            pass
        return {}

    def _apply_env_hints(self, cs: ConstraintSet, hints: dict[str, Any]) -> None:
        if "available_models" in hints:
            models = hints["available_models"]
            if isinstance(models, list) and len(models) == 0:
                if ConstraintKind.MODEL_TIER in cs.constraints:
                    cs.constraints[ConstraintKind.MODEL_TIER] = Constraint(
                        kind=ConstraintKind.MODEL_TIER,
                        value="fast",
                        min_value="fast",
                        max_value="fast",
                        adjustable=False,
                        breakable=False,
                        reason="env_no_models",
                    )
        if "disk_free_mb" in hints:
            free = hints["disk_free_mb"]
            if isinstance(free, (int, float)) and free < 100:
                if ConstraintKind.FILE_WRITE_SCOPE in cs.constraints:
                    cs.constraints[ConstraintKind.FILE_WRITE_SCOPE] = Constraint(
                        kind=ConstraintKind.FILE_WRITE_SCOPE,
                        value=["workspace"],
                        min_value=None,
                        max_value=None,
                        adjustable=True,
                        breakable=False,
                        reason="env_low_disk",
                    )
        if "network_available" in hints:
            if not hints["network_available"]:
                if ConstraintKind.NETWORK_ACCESS in cs.constraints:
                    cs.constraints[ConstraintKind.NETWORK_ACCESS] = Constraint(
                        kind=ConstraintKind.NETWORK_ACCESS,
                        value=False,
                        min_value=False,
                        max_value=False,
                        adjustable=False,
                        breakable=False,
                        reason="env_no_network",
                    )

    def stats(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "autonomy_level": self.autonomy.level,
            "break_count": self._break_count,
            "adjust_count": len(self._adjust_history),
            "current_risk_multiplier": self._compute_risk_multiplier(),
            "constraints_initialized": self._current is not None,
            "break_log_size": len(self.break_log.query()),
        }


__all__ = [
    "BoundaryManager",
    "ConstraintKind",
    "Constraint",
    "ConstraintSet",
    "SEED_CONSTRAINTS",
    "AUTONOMY_PRESETS",
]
