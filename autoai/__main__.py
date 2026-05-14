"""Auto-AI：一个由GPT驱动的AI助手"""
import os
import sys


def _ensure_utf8_terminal() -> None:
    """力 UTF-8 encoding on Windows terminals to prevent Chinese garbled text.

    On Windows the default console code page is typically GBK (cp936),
    which cannot render many UTF-8 characters (e.g. CJK, emoji).
    This function:
      1. Reconfigures sys.stdout/stderr/stdin to use utf-8 with 替换 errors
      2. Sets PYTHONIOENCODING for child processes
      3. On Windows, switches the console code page to 65001 (UTF-8)
    """
    if sys.platform == "win32":
        try:
            os.system("chcp 65001 >nul 2>&1")
        except Exception:
            pass

    for stream_name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass


_ensure_utf8_terminal()

import autoai.app.cli  # noqa: E402

if __name__ == "__main__":
    autoai.app.cli.main()
