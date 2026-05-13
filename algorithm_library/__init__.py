"""Algorithm Library for AutoGPT.

Provides algorithm registration, versioning, lifecycle management,
evaluation, and promotion workflows. Integrates with the governance
module for approval-gated algorithm evolution.
"""

from .registry import AlgorithmRegistry, AlgorithmManifest, AlgorithmStatus
from .base import AlgorithmBase, AlgorithmContext, AlgorithmResult
from .evaluation import EvaluationSuite, EvaluationReport, MetricThreshold
from .lifecycle import AlgorithmLifecycle, LifecycleTransition
from .catalog import AlgorithmCatalog

__all__ = [
    "AlgorithmRegistry",
    "AlgorithmManifest",
    "AlgorithmStatus",
    "AlgorithmBase",
    "AlgorithmContext",
    "AlgorithmResult",
    "EvaluationSuite",
    "EvaluationReport",
    "MetricThreshold",
    "AlgorithmLifecycle",
    "LifecycleTransition",
    "AlgorithmCatalog",
]
