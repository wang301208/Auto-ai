from __future__ import annotations

"""Lightweight telemetry utilities for AutoAI.

This module provides minimal in-memory counting of events and exposes hooks
for future integration with external monitoring or metrics backends. The
current implementation stores counters locally but allows registration of
callback hooks that can pipe metrics to third-party systems.
"""

from collections import Counter
from typing import Callable, Dict, Iterable


class Telemetry:
    """Simple telemetry collector.

    Counts occurrences of named events and notifies optional hooks whenever a
    counter is incremented. Hooks may be used to forward metrics to external
    monitoring services.
    """

    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self._hooks: list[Callable[[str, int], None]] = []

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value
        for hook in list(self._hooks):
            try:
                hook(name, self._counters[name])
            except Exception:
                continue

    def get_counts(self) -> Dict[str, int]:
        return dict(self._counters)

    def reset(self, names: Iterable[str] | None = None) -> None:
        if names is None:
            self._counters.clear()
        else:
            for name in names:
                self._counters.pop(name, None)

    def register_hook(self, hook: Callable[[str, int], None]) -> None:
        self._hooks.append(hook)


telemetry = Telemetry()

from autoai.telemetry.tracer import (
    TelemetryTracer,
    ThoughtSpan,
    DecisionSpan,
    ActionSpan,
    SpanKind,
    get_tracer,
)
from autoai.telemetry.metrics import MetricsCollector
