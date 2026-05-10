#!/usr/bin/env python3
"""启动本地智能体终端 TUI。"""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / "ui-tui"


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def utf8_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("LANG", "zh_CN.UTF-8")
    env.setdefault("LC_ALL", "zh_CN.UTF-8")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def enable_utf8_console() -> None:
    if os.name != "nt":
        return
    subprocess.run(["chcp", "65001"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ensure_ui_ready() -> None:
    if not (UI_DIR / "node_modules").exists():
        print("正在安装 TUI 依赖...")
        run(["npm", "install"], UI_DIR)
    if not (UI_DIR / "dist" / "entry.js").exists():
        print("正在构建 TUI...")
        run(["npm", "run", "build"], UI_DIR)


def main() -> int:
    try:
        enable_utf8_console()
        ensure_ui_ready()
        return subprocess.run(["node", "dist/entry.js"], cwd=UI_DIR, env=utf8_env()).returncode
    except FileNotFoundError as exc:
        print(f"缺少可执行程序：{exc.filename}")
        print("请安装 Node.js 和 Python 后重新运行。")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"命令执行失败：{' '.join(exc.cmd)}")
        return int(exc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
