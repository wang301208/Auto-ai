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

    # ------------------------------------------------------------------
    def increment(self, name: str, value: int = 1) -> None:
        """Increment ``name`` by ``value`` and notify hooks."""

        self._counters[name] += value
        for hook in list(self._hooks):
            try:
                hook(name, self._counters[name])
            except Exception:
                # Hooks are best-effort; 错误s are ignored to avoid impacting
                # 核心 functionality.
                continue

    # ------------------------------------------------------------------
    def get_counts(self) -> Dict[str, int]:
        """返回所有计数器的快照。"""

        return dict(self._counters)

    # ------------------------------------------------------------------
    def reset(self, names: Iterable[str] | None = None) -> None:
        """重置``names``的计数器，如``names``为None则重置所有。"""

        if names is None:
            self._counters.clear()
        else:
            for name in names:
                self._counters.pop(name, None)

    # ------------------------------------------------------------------
    def register_hook(self, hook: Callable[[str, int], None]) -> None:
        """注册计数器递增时调用的钩子。"""

        self._hooks.append(hook)


telemetry = Telemetry()
