import subprocess
from pathlib import Path


def test_run_command_creates_file(tmp_path: Path) -> None:
    result = subprocess.run(
        "touch outside.txt", cwd=tmp_path, shell=True, capture_output=True
    )
    assert result.returncode == 0
    assert (tmp_path / "outside.txt").exists()


def test_missing_binary_returns_error(tmp_path: Path) -> None:
    result = subprocess.run(
        "/bin/does_not_exist", cwd=tmp_path, shell=True, capture_output=True
    )
    assert result.returncode != 0
