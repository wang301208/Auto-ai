"""Algorithm evaluation framework.

Provides structured evaluation suites for comparing algorithm variants
against baseline metrics with configurable thresholds.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .base import AlgorithmBase, AlgorithmContext, AlgorithmResult


@dataclass(frozen=True)
class MetricThreshold:
    """Threshold definition for an evaluation metric.

    Attributes:
        name: Metric name (e.g. "f1_score", "latency_ms", "accuracy").
        min_value: Minimum acceptable value (for higher-is-better metrics).
        max_value: Maximum acceptable value (for lower-is-better metrics).
        direction: "maximize" or "minimize".
        weight: Relative weight for composite scoring.
    """

    name: str
    min_value: float | None = None
    max_value: float | None = None
    direction: str = "maximize"
    weight: float = 1.0

    def passes(self, value: float) -> bool:
        if self.direction == "maximize":
            if self.min_value is not None and value < self.min_value:
                return False
        else:
            if self.max_value is not None and value > self.max_value:
                return False
        return True

    def score(self, value: float) -> float:
        if self.direction == "maximize":
            if self.min_value is not None:
                return max(0.0, (value - self.min_value) * self.weight)
            return value * self.weight
        else:
            if self.max_value is not None:
                return max(0.0, (self.max_value - value) * self.weight)
            return -value * self.weight


@dataclass
class EvaluationReport:
    """Result of evaluating an algorithm against a suite.

    Attributes:
        algorithm_name: Name of the evaluated algorithm.
        algorithm_version: Version of the evaluated algorithm.
        suite_name: Name of the evaluation suite.
        metrics: Collected metric values.
        thresholds_passed: Whether each threshold was met.
        overall_pass: Whether all thresholds were met.
        composite_score: Weighted sum of metric scores.
        latency_ms: Total evaluation wall-clock time.
        created_at: ISO timestamp of evaluation.
        details: Additional details or artifacts.
    """

    algorithm_name: str = ""
    algorithm_version: str = ""
    suite_name: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    thresholds_passed: dict[str, bool] = field(default_factory=dict)
    overall_pass: bool = True
    composite_score: float = 0.0
    latency_ms: float = 0.0
    created_at: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm_name": self.algorithm_name,
            "algorithm_version": self.algorithm_version,
            "suite_name": self.suite_name,
            "metrics": self.metrics,
            "thresholds_passed": self.thresholds_passed,
            "overall_pass": self.overall_pass,
            "composite_score": self.composite_score,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
            "details": self.details,
        }

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )


@dataclass
class EvaluationSuite:
    """A named collection of thresholds for algorithm evaluation.

    Attributes:
        name: Suite identifier.
        description: Human-readable description.
        thresholds: List of metric thresholds.
        dataset_path: Path to evaluation dataset (optional).
        custom_evaluator: Optional callable for custom evaluation logic.
    """

    name: str
    description: str = ""
    thresholds: list[MetricThreshold] = field(default_factory=list)
    dataset_path: Path | None = None
    custom_evaluator: Callable | None = None

    def evaluate(
        self,
        algorithm: AlgorithmBase,
        context: AlgorithmContext,
    ) -> EvaluationReport:
        """Run the algorithm and evaluate results against thresholds."""
        start = time.monotonic()

        result = algorithm.run(context)

        metrics = dict(result.metrics)
        thresholds_passed: dict[str, bool] = {}
        composite = 0.0
        overall = True

        for threshold in self.thresholds:
            value = metrics.get(threshold.name)
            if value is not None:
                passed = threshold.passes(value)
                thresholds_passed[threshold.name] = passed
                if not passed:
                    overall = False
                composite += threshold.score(value)
            else:
                thresholds_passed[threshold.name] = False
                overall = False

        if self.custom_evaluator is not None:
            try:
                custom_metrics = self.custom_evaluator(result, metrics)
                metrics.update(custom_metrics)
            except Exception:
                pass

        latency = (time.monotonic() - start) * 1000

        return EvaluationReport(
            algorithm_name=algorithm.name,
            algorithm_version=algorithm.version,
            suite_name=self.name,
            metrics=metrics,
            thresholds_passed=thresholds_passed,
            overall_pass=overall,
            composite_score=composite,
            latency_ms=latency,
        )

    def compare(
        self,
        baseline: AlgorithmBase,
        candidate: AlgorithmBase,
        context: AlgorithmContext,
    ) -> dict[str, Any]:
        """Evaluate baseline and candidate, return comparison deltas."""
        baseline_report = self.evaluate(baseline, context)
        candidate_report = self.evaluate(candidate, context)
        deltas: dict[str, float] = {}
        for key in baseline_report.metrics:
            if key in candidate_report.metrics:
                deltas[key] = candidate_report.metrics[key] - baseline_report.metrics[key]
        recommendation = "promote_candidate"
        if not candidate_report.overall_pass:
            recommendation = "keep_baseline"
        elif baseline_report.composite_score > candidate_report.composite_score:
            recommendation = "keep_baseline"
        return {
            "baseline": baseline_report.to_dict(),
            "candidate": candidate_report.to_dict(),
            "deltas": deltas,
            "recommendation": recommendation,
        }
