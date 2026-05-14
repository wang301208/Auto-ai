from pathlib import Path
import pytest

from autoai.self_improve import DatabaseManager, PatchAgent


def test_pause_after_three_failures(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "improvement.db")
    pause_file = tmp_path / "pause.flag"
    patcher = PatchAgent(db=db, pause_file=pause_file)
    diff = "invalid diff"

    for _ in range(3):
        with pytest.raises(RuntimeError):
            patcher.apply_diff(diff, cwd=tmp_path)

    assert pause_file.exists()
    assert patcher.is_paused()
