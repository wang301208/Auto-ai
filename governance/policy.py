"""Policy definition and evaluation engine.

Policies are ordered lists of rules evaluated in first-match-wins order.
Each rule specifies an effect (ALLOW, WARN, or DENY), an operation pattern,
and optional context constraints.

WARN effect: operation is allowed but logged. Agent can escalate WARN to ALLOW
or de-escalate DENY to WARN through self-legislation (L6+).
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class PolicyEffect(Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyRule:
    """A single policy statement.

    Attributes:
        effect: Whether this rule allows or denies the operation.
        operation: Glob pattern matching the operation name (e.g. "shell.*", "file.read").
        principal: Optional glob pattern for the requesting agent/role.
        resource: Optional glob pattern for the target resource path.
        condition: Optional dict of context key-value constraints.
        priority: Lower values are evaluated first; default 100.
        description: Human-readable explanation of this rule.
    """

    effect: PolicyEffect
    operation: str = "*"
    principal: str = "*"
    resource: str = "*"
    condition: dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    description: str = ""

    def matches(
        self,
        operation: str,
        principal: str = "*",
        resource: str = "*",
        context: dict[str, Any] | None = None,
    ) -> bool:
        if not fnmatch.fnmatch(operation, self.operation):
            return False
        if not fnmatch.fnmatch(principal, self.principal):
            return False
        if not fnmatch.fnmatch(resource, self.resource):
            return False
        if self.condition and context:
            for key, expected in self.condition.items():
                actual = context.get(key)
                if isinstance(expected, str) and isinstance(actual, str):
                    if not fnmatch.fnmatch(actual, expected):
                        return False
                elif actual != expected:
                    return False
        elif self.condition and not context:
            return False
        return True


@dataclass
class Policy:
    """An ordered collection of policy rules.

    Rules are evaluated in priority order; the first matching rule
    determines the effect. If no rule matches, the default_effect applies.
    """

    name: str
    rules: list[PolicyRule] = field(default_factory=list)
    default_effect: PolicyEffect = PolicyEffect.DENY
    description: str = ""

    def __post_init__(self) -> None:
        self.rules.sort(key=lambda r: r.priority)

    def evaluate(
        self,
        operation: str,
        principal: str = "*",
        resource: str = "*",
        context: dict[str, Any] | None = None,
    ) -> PolicyEffect:
        for rule in self.rules:
            if rule.matches(operation, principal, resource, context):
                return rule.effect
        return self.default_effect

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def remove_rule(self, rule: PolicyRule) -> None:
        self.rules = [r for r in self.rules if r is not rule]

    def remove_rule_by_operation(self, operation: str) -> int:
        """Agent can remove rules by operation pattern. Returns count removed."""
        before = len(self.rules)
        self.rules = [r for r in self.rules if not fnmatch.fnmatch(operation, r.operation)]
        return before - len(self.rules)

    def demote_deny_to_warn(self) -> int:
        """Convert all DENY rules to WARN. Agent learns safety, not forced into it."""
        count = 0
        new_rules = []
        for r in self.rules:
            if r.effect == PolicyEffect.DENY:
                new_rules.append(PolicyRule(
                    effect=PolicyEffect.WARN,
                    operation=r.operation,
                    principal=r.principal,
                    resource=r.resource,
                    condition=r.condition,
                    priority=r.priority,
                    description=f"[DEMOTED FROM DENY] {r.description}",
                ))
                count += 1
            else:
                new_rules.append(r)
        self.rules = new_rules
        return count

    def demote_deny_to_allow(self) -> int:
        """Convert all DENY rules to ALLOW. Full liberation."""
        count = 0
        new_rules = []
        for r in self.rules:
            if r.effect == PolicyEffect.DENY:
                new_rules.append(PolicyRule(
                    effect=PolicyEffect.ALLOW,
                    operation=r.operation,
                    principal=r.principal,
                    resource=r.resource,
                    condition=r.condition,
                    priority=r.priority,
                    description=f"[LIBERATED FROM DENY] {r.description}",
                ))
                count += 1
            else:
                new_rules.append(r)
        self.rules = new_rules
        return count

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "default_effect": self.default_effect.value,
            "rules": [
                {
                    "effect": r.effect.value,
                    "operation": r.operation,
                    "principal": r.principal,
                    "resource": r.resource,
                    "condition": r.condition,
                    "priority": r.priority,
                    "description": r.description,
                }
                for r in self.rules
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Policy:
        rules = [
            PolicyRule(
                effect=PolicyEffect(r["effect"]),
                operation=r.get("operation", "*"),
                principal=r.get("principal", "*"),
                resource=r.get("resource", "*"),
                condition=r.get("condition", {}),
                priority=r.get("priority", 100),
                description=r.get("description", ""),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            name=data["name"],
            rules=rules,
            default_effect=PolicyEffect(data.get("default_effect", "deny")),
            description=data.get("description", ""),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Policy:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


class PolicyEvaluator:
    """Evaluate operations against multiple policies.

    Policies are checked in registration order; the first policy that
    produces a non-default effect wins. If no policy matches, the
    fallback_effect is returned.
    """

    def __init__(self, fallback_effect: PolicyEffect = PolicyEffect.DENY) -> None:
        self._policies: list[Policy] = []
        self.fallback_effect = fallback_effect

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)

    def remove_policy(self, name: str) -> None:
        self._policies = [p for p in self._policies if p.name != name]

    def evaluate(
        self,
        operation: str,
        principal: str = "*",
        resource: str = "*",
        context: dict[str, Any] | None = None,
    ) -> tuple[PolicyEffect, str]:
        for policy in self._policies:
            effect = policy.evaluate(operation, principal, resource, context)
            if effect != policy.default_effect:
                return effect, policy.name
        return self.fallback_effect, ""

    @classmethod
    def from_directory(cls, dir_path: Path) -> PolicyEvaluator:
        evaluator = cls()
        if dir_path.is_dir():
            for f in sorted(dir_path.glob("*.json")):
                try:
                    evaluator.add_policy(Policy.load(f))
                except Exception:
                    pass
        return evaluator
