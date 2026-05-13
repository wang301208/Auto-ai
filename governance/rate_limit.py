"""Rate limiting with token bucket algorithm.

Supports per-principal, per-operation rate limits with configurable
burst capacity and refill rates.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RateLimitRule:
    """Definition of a rate limit.

    Attributes:
        operation: Glob pattern for the operation this rule applies to.
        principal: Glob pattern for the requesting agent/role.
        max_burst: Maximum number of tokens in the bucket (burst capacity).
        refill_rate: Tokens added per second.
        scope: Key scope for the bucket: "global", "principal", "operation", or "both".
    """

    operation: str = "*"
    principal: str = "*"
    max_burst: float = 10.0
    refill_rate: float = 1.0
    scope: str = "both"


class TokenBucket:
    """A single token bucket with thread-safe consume/refill."""

    def __init__(self, max_burst: float, refill_rate: float) -> None:
        self.max_burst = max_burst
        self.refill_rate = refill_rate
        self._tokens: float = max_burst
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_burst, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait_and_consume(self, tokens: float = 1.0, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            if deadline is not None and time.monotonic() >= deadline:
                return False
            deficit = tokens - self._tokens
            wait_time = deficit / self.refill_rate if self.refill_rate > 0 else 1.0
            time.sleep(min(wait_time, 0.1))

    @property
    def available(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


class RateLimiter:
    """Multi-rule rate limiter with per-scope token buckets.

    Agent can autonomously adjust rules via adjust_rule().
    No human configuration needed at runtime.
    """

    def __init__(self) -> None:
        self._rules: list[RateLimitRule] = []
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def add_rule(self, rule: RateLimitRule) -> None:
        self._rules.append(rule)

    def adjust_rule(self, operation: str, new_refill_rate: float | None = None, new_max_burst: float | None = None) -> bool:
        """Agent-autonomous rate limit adjustment.

        No human approval needed. Adjustment is recorded in audit log
        by the caller (PolicyEvolver or BoundaryManager).
        """
        import fnmatch as _fnmatch

        with self._lock:
            for i, rule in enumerate(self._rules):
                if _fnmatch.fnmatch(operation, rule.operation):
                    refill = new_refill_rate if new_refill_rate is not None else rule.refill_rate
                    burst = new_max_burst if new_max_burst is not None else rule.max_burst
                    self._rules[i] = RateLimitRule(
                        operation=rule.operation,
                        principal=rule.principal,
                        max_burst=burst,
                        refill_rate=refill,
                        scope=rule.scope,
                    )
                    self._buckets.clear()
                    return True
        return False

    def _bucket_key(
        self, rule: RateLimitRule, operation: str, principal: str
    ) -> str:
        if rule.scope == "global":
            return f"{rule.operation}:{rule.principal}"
        elif rule.scope == "principal":
            return f"{rule.operation}:{principal}"
        elif rule.scope == "operation":
            return f"{operation}:{rule.principal}"
        else:
            return f"{operation}:{principal}"

    def _get_bucket(self, key: str, rule: RateLimitRule) -> TokenBucket:
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(rule.max_burst, rule.refill_rate)
        return self._buckets[key]

    def check(
        self,
        operation: str,
        principal: str = "*",
        tokens: float = 1.0,
    ) -> bool:
        import fnmatch

        with self._lock:
            for rule in self._rules:
                if not fnmatch.fnmatch(operation, rule.operation):
                    continue
                if not fnmatch.fnmatch(principal, rule.principal):
                    continue
                key = self._bucket_key(rule, operation, principal)
                bucket = self._get_bucket(key, rule)
                if not bucket.consume(tokens):
                    return False
        return True

    def wait(
        self,
        operation: str,
        principal: str = "*",
        tokens: float = 1.0,
        timeout: float | None = None,
    ) -> bool:
        import fnmatch

        applicable: list[tuple[TokenBucket, RateLimitRule]] = []
        with self._lock:
            for rule in self._rules:
                if not fnmatch.fnmatch(operation, rule.operation):
                    continue
                if not fnmatch.fnmatch(principal, rule.principal):
                    continue
                key = self._bucket_key(rule, operation, principal)
                bucket = self._get_bucket(key, rule)
                applicable.append((bucket, rule))
        for bucket, rule in applicable:
            if not bucket.wait_and_consume(tokens, timeout):
                return False
        return True
