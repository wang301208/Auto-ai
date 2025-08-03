from pathlib import Path

from autogpt.sandbox import Sandbox


def test_write_outside_denied(tmp_path: Path):
    sandbox_root = tmp_path / "root"
    sandbox = Sandbox(sandbox_root)
    sandbox.run("touch /outside.txt")
    assert (sandbox_root / "outside.txt").exists()
    assert not (tmp_path / "outside.txt").exists()


def test_missing_host_binary(tmp_path: Path):
    sandbox_root = tmp_path / "root"
    sandbox = Sandbox(sandbox_root)
    result = sandbox.run("/bin/true")
    assert result.returncode != 0
