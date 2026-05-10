#!/usr/bin/env python3
"""检查本地智能体终端 TUI 是否可运行。"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / "ui-tui"
sys.path.insert(0, str(PROJECT_ROOT))


def executable(name: str) -> str:
    if os.name == "nt" and not name.lower().endswith((".exe", ".cmd", ".bat")):
        for suffix in (".cmd", ".exe", ".bat"):
            resolved = shutil.which(f"{name}{suffix}")
            if resolved:
                return resolved
    return shutil.which(name) or name


def command_ok(command: list[str], cwd: Path | None = None) -> bool:
    try:
        command = [executable(command[0]), *command[1:]]
        subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def main() -> int:
    checks = {
        "node": command_ok(["node", "--version"]),
        "npm": command_ok(["npm", "--version"]),
        "TUI 依赖": (UI_DIR / "node_modules").exists(),
        "Python 网关": importlib.util.find_spec("tui_gateway.entry") is not None,
        "TypeScript": command_ok(["npx", "tsc", "--noEmit"], UI_DIR),
    }
    for name, ok in checks.items():
        print(f"{name}: {'正常' if ok else '缺失'}")
    if all(checks.values()):
        print("TUI 检查通过。启动命令：python scripts/launch_tui.py")
        return 0
    print("TUI 检查失败。请运行：cd ui-tui && npm install && npm run build")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
