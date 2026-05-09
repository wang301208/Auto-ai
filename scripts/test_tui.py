#!/usr/bin/env python3
"""Check that the Local Agent terminal UI can run."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / "ui-tui"


def command_ok(command: list[str], cwd: Path | None = None) -> bool:
    try:
        subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def main() -> int:
    checks = {
        "node": command_ok(["node", "--version"]),
        "npm": command_ok(["npm", "--version"]),
        "ui dependencies": (UI_DIR / "node_modules").exists(),
        "python gateway": importlib.util.find_spec("tui_gateway.entry") is not None,
        "typescript": command_ok(["npx", "tsc", "--noEmit"], UI_DIR),
    }
    for name, ok in checks.items():
        print(f"{name}: {'ok' if ok else 'missing'}")
    if all(checks.values()):
        print("TUI checks passed. Start with: python scripts/launch_tui.py")
        return 0
    print("TUI checks failed. Run: cd ui-tui && npm install && npm run build")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
