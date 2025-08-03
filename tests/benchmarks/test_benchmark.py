import timeit
from pathlib import Path

from autogpt.self_improve import DatabaseManager, Profiler


def test_profiler_benchmark(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "improvement.db")

    def run() -> None:
        with Profiler(db, "bench"):
            sum(range(100))

    duration = timeit.timeit(run, number=10)
    assert duration >= 0
