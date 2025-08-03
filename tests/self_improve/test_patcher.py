import shutil
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from autogpt.self_improve.patcher import PatchAgent


def test_apply_diff_rolls_back_on_failure(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("line1\nline2\nline3\n")

    diff = (
        "--- file.txt\n"
        "+++ file.txt\n"
        "@@ -1 +1 @@\n"
        "-line1\n"
        "+LINE1\n"
        "@@ -2 +2 @@\n"
        "-lineX\n"
        "+line2\n"
    )

    agent = PatchAgent()
    with pytest.raises(RuntimeError):
        agent.apply_diff(diff, cwd=tmp_path)
    assert file_path.read_text() == "line1\nline2\nline3\n"


def test_apply_diff_dry_run(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("line1\nline2\n")

    diff = "".join(
        [
            "--- file.txt\n",
            "+++ file.txt\n",
            "@@ -1 +1 @@\n",
            "-line1\n",
            "+LINE1\n",
        ]
    )

    agent = PatchAgent()
    agent.apply_diff(diff, cwd=tmp_path, dry_run=True)
    assert file_path.read_text() == "line1\nline2\n"


def test_verify_runs_tests(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    agent = PatchAgent()
    file_path = tmp_path / "file.py"
    file_path.write_text("print('hi')\n")

    calls: list[list[str]] = []

    def fake_run(  # type: ignore[no-untyped-def]
        cmd, capture_output=True, text=True, **kwargs
    ):
        calls.append(cmd)

        class Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        return Proc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    agent.verify([file_path])

    assert ["pytest", "-q"] in calls


def test_apply_diff_uses_system_patch(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("line1\n")

    diff = "".join(
        [
            "--- file.txt\n",
            "+++ file.txt\n",
            "@@ -1 +1 @@\n",
            "-line1\n",
            "+LINE1\n",
        ]
    )

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)

        class Proc:
            returncode = 0
            stderr = b""

        return Proc()

    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/patch")
    monkeypatch.setattr(subprocess, "run", fake_run)
    agent = PatchAgent()
    agent.apply_diff(diff, cwd=tmp_path)

    assert calls and calls[0][0].endswith("patch")


def test_apply_diff_falls_back_to_python_patch(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("line1\n")

    diff = "".join(
        [
            "--- file.txt\n",
            "+++ file.txt\n",
            "@@ -1 +1 @@\n",
            "-line1\n",
            "+LINE1\n",
        ]
    )

    monkeypatch.setattr(shutil, "which", lambda _: None)
    agent = PatchAgent()
    agent.apply_diff(diff, cwd=tmp_path)

    assert file_path.read_text() == "LINE1\n"
