#!/usr/bin/env python3
"""Launch the Local Agent terminal UI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / "ui-tui"


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def ensure_ui_ready() -> None:
    if not (UI_DIR / "node_modules").exists():
        print("Installing TUI dependencies...")
        run(["npm", "install"], UI_DIR)
    if not (UI_DIR / "dist" / "entry.js").exists():
        print("Building TUI...")
        run(["npm", "run", "build"], UI_DIR)


def main() -> int:
    try:
        ensure_ui_ready()
        return subprocess.run(["node", "dist/entry.js"], cwd=UI_DIR).returncode
    except FileNotFoundError as exc:
        print(f"Missing executable: {exc.filename}")
        print("Install Node.js and Python, then run this script again.")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {' '.join(exc.cmd)}")
        return int(exc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
