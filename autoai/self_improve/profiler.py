"""简单的性能分析."""

from __future__ import annotations

import cProfile
import pstats
from time import perf_counter
from types import TracebackType
from typing import Optional

from .database import DatabaseManager


class Profiler:
    """计时代码段的上下文管理器."""

    def __init__(self, db: DatabaseManager, name: str) -> None:
        self.db = db
        self.name = name
        self._start: Optional[float] = None
        self._prof: Optional[cProfile.Profile] = None

    def __enter__(self) -> "Profiler":
        self._start = perf_counter()
        self._prof = cProfile.Profile()
        self._prof.enable()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._start is None:
            return
        if self._prof is not None:
            self._prof.disable()
        duration = perf_counter() - self._start
        self.db.log_profile(self.name, duration)
        if self._prof is not None:
            stats = pstats.Stats(self._prof)
            items = sorted(
                stats.stats.items(), key=lambda item: item[1][3], reverse=True  # type: ignore[attr-defined]
            )[:10]
            for (file, line, func), info in items:
                ncalls = info[1]
                cumtime = info[3]
                fname = f"{file}:{line}:{func}"
                self.db.log_profile_detail(self.name, fname, ncalls, cumtime)
