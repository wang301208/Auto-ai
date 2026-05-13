"""Base interface for all algorithms in the library.

Every algorithm must inherit from AlgorithmBase and implement
the execute() method. The base class provides standard hooks
for validation, profiling, and error handling.
"""

from __future__ import annotations

import time
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlgorithmContext:
    """Runtime context passed to algorithm execution.

    Attributes:
        inputs: Primary input data for the algorithm.
        config: Algorithm-specific configuration overrides.
        metadata: Auxiliary metadata (e.g. request_id, principal).
        workspace: Optional workspace path for file-based algorithms.
    """

    inputs: Any = None
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    workspace: str | None = None


@dataclass
class AlgorithmResult:
    """Standard result container for algorithm execution.

    Attributes:
        output: Primary output of the algorithm.
        metrics: Performance/quality metrics collected during execution.
        artifacts: Secondary outputs (files, logs, visualizations).
        latency_ms: Execution wall-clock time in milliseconds.
        success: Whether execution completed without error.
        error: Error message if execution failed.
    """

    output: Any = None
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None

    @classmethod
    def failure(cls, error: str, latency_ms: float = 0.0) -> AlgorithmResult:
        return cls(success=False, error=error, latency_ms=latency_ms)


class AlgorithmBase(metaclass=ABCMeta):
    """Abstract base class for all algorithms.

    Subclasses must implement:
      - name: class attribute identifying the algorithm
      - version: class attribute for versioning
      - description: human-readable description
      - execute(): core algorithm logic

    Optional overrides:
      - validate_inputs(): pre-execution input validation
      - on_before_execute(): pre-execution hook
      - on_after_execute(): post-execution hook
    """

    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    tags: list[str] = []

    @abstractmethod
    def execute(self, context: AlgorithmContext) -> AlgorithmResult:
        """Execute the algorithm with the given context.

        This is the primary method that subclasses must implement.
        """
        ...

    def validate_inputs(self, context: AlgorithmContext) -> list[str]:
        """Validate inputs before execution. Return list of error messages."""
        return []

    def on_before_execute(self, context: AlgorithmContext) -> AlgorithmContext:
        """Hook called before execute(). Can modify context."""
        return context

    def on_after_execute(
        self, context: AlgorithmContext, result: AlgorithmResult
    ) -> AlgorithmResult:
        """Hook called after execute(). Can modify result."""
        return result

    def run(self, context: AlgorithmContext) -> AlgorithmResult:
        """Full execution pipeline: validate -> before -> execute -> after.

        This is the public entry point. It wraps execute() with
        validation, timing, and lifecycle hooks.
        """
        errors = self.validate_inputs(context)
        if errors:
            return AlgorithmResult.failure(
                f"Input validation failed: {'; '.join(errors)}"
            )

        context = self.on_before_execute(context)

        start = time.monotonic()
        try:
            result = self.execute(context)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return AlgorithmResult.failure(str(e), latency_ms=latency)
        latency = (time.monotonic() - start) * 1000
        result.latency_ms = latency

        result = self.on_after_execute(context, result)
        return result

    def manifest(self) -> dict[str, Any]:
        """Return algorithm metadata for registry registration."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "class": f"{self.__class__.__module__}.{self.__class__.__qualname__}",
        }
