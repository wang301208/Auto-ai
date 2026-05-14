"""Inline ANSI color constants. Replaces colorama.Fore/Back/Style.

Uses standard ANSI escape codes. On Windows 10+, ANSI is natively supported.
For older Windows, `os.system('')` enables ANSI processing.
"""
from __future__ import annotations

import os
import sys


def _enable_ansi_on_windows():
    if sys.platform == "win32":
        try:
            os.system("")
        except Exception:
            pass


_enable_ansi_on_windows()


class _AnsiConsts:
    """ANSI转义码字符串常量的命名空间。"""

    RESET_ALL = "\033[0m"
    BRIGHT = "\033[1m"
    DIM = "\033[2m"
    NORMAL = "\033[22m"

    class Fore:
        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"
        LIGHTBLACK_EX = "\033[90m"
        LIGHTRED_EX = "\033[91m"
        LIGHTGREEN_EX = "\033[92m"
        LIGHTYELLOW_EX = "\033[93m"
        LIGHTBLUE_EX = "\033[94m"
        LIGHTMAGENTA_EX = "\033[95m"
        LIGHTCYAN_EX = "\033[96m"
        LIGHTWHITE_EX = "\033[97m"
        RESET = "\033[39m"

    class Back:
        BLACK = "\033[40m"
        RED = "\033[41m"
        GREEN = "\033[42m"
        YELLOW = "\033[43m"
        BLUE = "\033[44m"
        MAGENTA = "\033[45m"
        CYAN = "\033[46m"
        WHITE = "\033[47m"
        LIGHTBLACK_EX = "\033[100m"
        LIGHTRED_EX = "\033[101m"
        LIGHTGREEN_EX = "\033[102m"
        LIGHTYELLOW_EX = "\033[103m"
        LIGHTBLUE_EX = "\033[104m"
        LIGHTMAGENTA_EX = "\033[105m"
        LIGHTCYAN_EX = "\033[106m"
        LIGHTWHITE_EX = "\033[107m"
        RESET = "\033[49m"


Fore = _AnsiConsts.Fore()
Back = _AnsiConsts.Back()


class Style:
    RESET_ALL = _AnsiConsts.RESET_ALL
    BRIGHT = _AnsiConsts.BRIGHT
    DIM = _AnsiConsts.DIM
    NORMAL = _AnsiConsts.NORMAL


__all__ = ["Fore", "Back", "Style"]
