"""Patch agent capable of applying diffs and verifying with code checks."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .database import DatabaseManager


class PatchAgent:
    """Apply patches and run code quality checks."""

    def __init__(
        self,
        db: DatabaseManager | None = None,
        pause_file: Path | str | None = None,
    ) -> None:
        self.db = db
        self.pause_file = Path(pause_file or "self_improve.pause")

    def is_paused(self) -> bool:
        return self.pause_file.exists()

    def _record_attempt(self, success: bool) -> None:
        if self.db is None:
            return
        self.db.log_patch_attempt(success)
        last = [row[0] for row in self.db.get_last_patch_attempts(3)]
        if len(last) == 3 and all(not val for val in last):
            self.pause_file.write_text(datetime.utcnow().isoformat())

    def apply_diff(
        self, diff: str, *, cwd: Path | None = None, dry_run: bool = False
    ) -> None:
        if self.is_paused():
            raise RuntimeError("Self-improvement paused")

        files: set[Path] = set()
        old: str | None = None
        for line in diff.splitlines():
            if line.startswith("--- "):
                old = line[4:].split("\t", 1)[0]
            elif line.startswith("+++ "):
                new = line[4:].split("\t", 1)[0]
                target = new if new != "/dev/null" else old
                if target and target != "/dev/null":
                    files.add(Path(cwd or Path()) / target)

        backups = {f: f.read_bytes() for f in files if f.exists()}

        patch_path = shutil.which("patch")
        if patch_path:
            cmd = [patch_path, "-p0", "-N"]
            if dry_run:
                cmd.append("--dry-run")

            process = subprocess.run(
                cmd,
                input=diff.encode(),
                capture_output=True,
                text=False,
                cwd=str(cwd) if cwd else None,
            )
            if process.returncode != 0:
                for file_path, content in backups.items():
                    file_path.write_bytes(content)
                self._record_attempt(False)
                raise RuntimeError(f"Patch failed: {process.stderr.decode()}")

            self._record_attempt(True)
            return

        if dry_run:
            raise RuntimeError("dry_run not supported without system 'patch' command")

        try:
            import patch_ng
        except ImportError as exc:  # pragma: no cover - import error path
            self._record_attempt(False)
            raise RuntimeError(
                "Patch command not found and 'patch-ng' library is missing. "
                "Install the 'patch' utility or `pip install patch-ng`"
            ) from exc

        ps = patch_ng.fromstring(diff.encode())
        success = ps.apply(root=str(cwd) if cwd else None)
        if not success:
            for file_path, content in backups.items():
                file_path.write_bytes(content)
            self._record_attempt(False)
            raise RuntimeError("Patch failed using patch-ng library")

        self._record_attempt(True)

    def rewrite_function(
        self, file_path: Path, function_name: str, new_body: str
    ) -> None:
        lines = Path(file_path).read_text().splitlines()
        out_lines = []
        inside = False
        indent = ""
        for line in lines:
            if line.startswith("def " + function_name):
                inside = True
                base = line[: len(line) - len(line.lstrip())]
                indent = base + "    "
                out_lines.append(line)
                out_lines.extend(indent + part for part in new_body.splitlines())
                continue
            if inside and not line.startswith(indent):
                inside = False
            if not inside:
                out_lines.append(line)
        Path(file_path).write_text("\n".join(out_lines) + "\n")

    def verify(self, files: Sequence[Path]) -> None:
        str_files = [str(f) for f in files]
        for cmd in (
            ["black", "--check", *str_files],
            ["ruff", "check", *str_files],
            ["mypy", *str_files],
            ["pytest", "-q"],
        ):
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                raise RuntimeError(process.stdout + process.stderr)
