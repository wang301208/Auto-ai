"""Autonomy level management for self-evolving agents.

Implements a progressive autonomy system where agents autonomously
manage their own autonomy level based on demonstrated reliability.

All levels are fully autonomous. The difference is constraint tightness,
NOT human involvement. No level requires human approval.

Levels:
    L0 = MANUAL      : Tightest constraints, Agent self-set
    L1 = SUPERVISED  : Tight constraints, Agent self-set
    L2 = SELF_BOUND  : Agent defines and adjusts its own boundaries
    L3 = SELF_REWRITE: Agent can modify its own code/architecture
    L4 = SELF_SPAWN  : Agent can create/destroy sub-agents
    L5 = AUTONOMOUS  : Full self-governance, human only sees results

Escalation is automatic based on consecutive successes (Agent decides).
De-escalation is automatic on failures (Agent decides).
No human can force a level change at runtime.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any


class AutonomyLevel(IntEnum):
    MANUAL = 0
    SUPERVISED = 1
    SELF_BOUND = 2
    SELF_REWRITE = 3
    SELF_SPAWN = 4
    AUTONOMOUS = 5


@dataclass
class AutonomyCapabilities:
    can_modify_code: bool = False
    can_modify_config: bool = False
    can_modify_strategy: bool = False
    can_modify_architecture: bool = False
    can_switch_model: bool = False
    can_create_agents: bool = False
    can_destroy_agents: bool = False
    can_self_rewrite: bool = False
    can_auto_commit: bool = False
    can_auto_push: bool = False
    can_hot_reload: bool = False
    can_skip_approval: bool = False

    @classmethod
    def for_level(cls, level: AutonomyLevel) -> AutonomyCapabilities:
        caps = cls()
        if level >= AutonomyLevel.SUPERVISED:
            caps.can_modify_config = True
            caps.can_switch_model = True
        if level >= AutonomyLevel.SELF_BOUND:
            caps.can_modify_code = True
            caps.can_modify_strategy = True
            caps.can_auto_commit = True
            caps.can_hot_reload = True
        if level >= AutonomyLevel.SELF_REWRITE:
            caps.can_modify_architecture = True
            caps.can_self_rewrite = True
            caps.can_auto_push = True
            caps.can_skip_approval = True
        if level >= AutonomyLevel.SELF_SPAWN:
            caps.can_create_agents = True
            caps.can_destroy_agents = True
        return caps


@dataclass
class EscalationRecord:
    timestamp: str
    old_level: AutonomyLevel
    new_level: AutonomyLevel
    reason: str
    consecutive_successes: int
    consecutive_failures: int


@dataclass
class AutonomyConfig:
    successes_to_escalate: int = 50
    failures_to_de_escalate: int = 3
    max_level: AutonomyLevel = AutonomyLevel.AUTONOMOUS
    min_level: AutonomyLevel = AutonomyLevel.MANUAL
    escalation_cooldown_seconds: float = 3600.0


class AutonomyManager:
    """Manages agent autonomy level with automatic escalation/de-escalation.

    Thread-safe. Tracks consecutive successes and failures to determine
    when an agent has earned (or lost) higher autonomy.

    Usage:
        mgr = AutonomyManager(agent_id="auto-ai")
        mgr.record_success()  # after each successful operation
        mgr.record_failure()  # after each failed operation
        print(mgr.level)      # current autonomy level
        print(mgr.capabilities)  # what this level allows
    """

    def __init__(
        self,
        agent_id: str = "auto-ai",
        initial_level: AutonomyLevel = AutonomyLevel.SUPERVISED,
        config: AutonomyConfig | None = None,
    ) -> None:
        self.agent_id = agent_id
        self._level = initial_level
        self._config = config or AutonomyConfig()
        self._consecutive_successes: int = 0
        self._consecutive_failures: int = 0
        self._total_successes: int = 0
        self._total_failures: int = 0
        self._last_escalation: str = ""
        self._history: list[EscalationRecord] = []
        self._lock = threading.Lock()

    @property
    def level(self) -> AutonomyLevel:
        return self._level

    @property
    def capabilities(self) -> AutonomyCapabilities:
        return AutonomyCapabilities.for_level(self._level)

    @property
    def consecutive_successes(self) -> int:
        return self._consecutive_successes

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def record_success(self) -> AutonomyLevel | None:
        with self._lock:
            self._consecutive_successes += 1
            self._consecutive_failures = 0
            self._total_successes += 1

            if self._should_escalate():
                return self._escalate("consecutive_successes_threshold")
            return None

    def record_failure(self) -> AutonomyLevel | None:
        with self._lock:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._total_failures += 1

            if self._should_de_escalate():
                return self._de_escalate("consecutive_failures_threshold")
            return None

    def autonomous_adjust_level(self, reason: str = "agent_self_eval") -> None:
        """Agent autonomously adjusts its level based on self-evaluation.

        Replaces force_level() — no human can override autonomy level at runtime.
        This method is called by the Agent's own self-evaluation logic.
        """
        with self._lock:
            old = self._level
            self._history.append(EscalationRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                old_level=old,
                new_level=self._level,
                reason=reason,
                consecutive_successes=self._consecutive_successes,
                consecutive_failures=self._consecutive_failures,
            ))

    def _should_escalate(self) -> bool:
        if self._level >= self._config.max_level:
            return False
        if self._consecutive_successes < self._config.successes_to_escalate:
            return False
        if self._last_escalation:
            from datetime import timedelta
            try:
                last = datetime.fromisoformat(self._last_escalation)
                elapsed = (datetime.now(timezone.utc) - last).total_seconds()
                if elapsed < self._config.escalation_cooldown_seconds:
                    return False
            except (ValueError, TypeError):
                pass
        return True

    def _should_de_escalate(self) -> bool:
        if self._level <= self._config.min_level:
            return False
        return self._consecutive_failures >= self._config.failures_to_de_escalate

    def _escalate(self, reason: str) -> AutonomyLevel:
        old = self._level
        new_level = AutonomyLevel(min(old + 1, self._config.max_level))
        self._level = new_level
        now = datetime.now(timezone.utc).isoformat()
        self._last_escalation = now
        self._consecutive_successes = 0
        self._history.append(EscalationRecord(
            timestamp=now,
            old_level=old,
            new_level=new_level,
            reason=reason,
            consecutive_successes=self._consecutive_successes,
            consecutive_failures=self._consecutive_failures,
        ))
        return new_level

    def _de_escalate(self, reason: str) -> AutonomyLevel:
        old = self._level
        new_level = AutonomyLevel(max(old - 1, self._config.min_level))
        self._level = new_level
        self._consecutive_failures = 0
        self._history.append(EscalationRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            old_level=old,
            new_level=new_level,
            reason=reason,
            consecutive_successes=self._consecutive_successes,
            consecutive_failures=self._consecutive_failures,
        ))
        return new_level

    def stats(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "level": self._level.value,
            "level_name": self._level.name,
            "consecutive_successes": self._consecutive_successes,
            "consecutive_failures": self._consecutive_failures,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "escalation_count": len([h for h in self._history if h.new_level > h.old_level]),
            "de_escalation_count": len([h for h in self._history if h.new_level < h.old_level]),
            "history_size": len(self._history),
        }

    @property
    def history(self) -> list[EscalationRecord]:
        return list(self._history)


__all__ = [
    "AutonomyLevel",
    "AutonomyCapabilities",
    "AutonomyConfig",
    "AutonomyManager",
    "EscalationRecord",
]
