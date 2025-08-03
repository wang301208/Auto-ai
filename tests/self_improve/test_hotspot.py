from pathlib import Path

from autogpt.self_improve import DatabaseManager, Profiler


def slow_fn() -> int:
    total = 0
    for _ in range(1000):
        total += sum(range(100))
    return total


def test_hotspot_detection(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "improvement.db")
    with Profiler(db, "slow"):
        slow_fn()

    details = list(db.get_profile_details())
    slow_detail = next(item for item in details if "slow_fn" in item[2])
    cumtime = slow_detail[4]

    hotspots = list(db.get_hotspots(threshold=cumtime - 0.00001))
    assert any("slow_fn" in func for func, _ in hotspots)
