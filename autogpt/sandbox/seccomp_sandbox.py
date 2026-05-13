"""Seccomp-based sandbox — Linux only.

Uses seccomp-bpf (via libseccomp/python-seccomp) to restrict system calls
within the sandboxed process. Falls back gracefully on non-Linux platforms.

This module is optional — import will fail if python-seccomp is not installed.
The __init__.py handles ImportError gracefully.
"""

from __future__ import annotations

import asyncio
import os
import platform
import time
from typing import Any

from .base import SandboxBackend, SandboxConfig, SandboxResult, SandboxViolation, ViolationType
from .subprocess_sandbox import SubprocessSandbox

_IS_LINUX = platform.system() == "Linux"

try:
    import seccomp as _seccomp_module
    _HAS_SECCOMP = True
except ImportError:
    _HAS_SECCOMP = False


class SeccompSandbox(SandboxBackend):
    """Linux seccomp-bpf sandbox.

    If seccomp is unavailable (non-Linux or python-seccomp not installed),
    falls back to SubprocessSandbox with stricter defaults.
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        super().__init__(config)
        self._fallback: SubprocessSandbox | None = None
        if not (_IS_LINUX and _HAS_SECCOMP):
            fallback_config = SandboxConfig(
                enabled=config.enabled if config else True,
                allowed_commands=config.allowed_commands if config else SandboxConfig().allowed_commands,
                denied_commands=config.denied_commands if config else SandboxConfig().denied_commands,
                allowed_paths=config.allowed_paths if config else set(),
                denied_paths=config.denied_paths if config else SandboxConfig().denied_paths,
                max_output_bytes=config.max_output_bytes if config else 1_000_000,
                timeout_seconds=config.timeout_seconds if config else 120.0,
                allow_network=config.allow_network if config else False,
                allow_subprocess=False,
                workspace_dir=config.workspace_dir if config else "",
            )
            self._fallback = SubprocessSandbox(fallback_config)

    async def execute(
        self,
        command: str,
        args: dict[str, Any],
        timeout: float | None = None,
    ) -> SandboxResult:
        if self._fallback:
            return await self._fallback.execute(command, args, timeout)

        violations: list[SandboxViolation] = []
        start = time.monotonic()

        cmd_v = self.check_command(command)
        if cmd_v:
            violations.append(cmd_v)
            return SandboxResult(success=False, error=f"Blocked: {command}", violations=violations)

        path_arg = args.get("path", args.get("filename", ""))
        if path_arg:
            pv = self.check_path(str(path_arg))
            if pv:
                violations.append(pv)
                return SandboxResult(success=False, error=f"Path denied: {path_arg}", violations=violations)

        effective_timeout = timeout or self.config.timeout_seconds

        try:
            result = await self._run_with_seccomp(command, args, effective_timeout)
            result.violations = violations
            result.duration_seconds = time.monotonic() - start
            return result
        except asyncio.TimeoutError:
            violations.append(SandboxViolation(type=ViolationType.TIMEOUT, detail="Seccomp exec timeout", command=command))
            return SandboxResult(success=False, error="Timeout", violations=violations)
        except Exception as e:
            return SandboxResult(success=False, error=str(e), violations=violations)

    def validate_command(self, command: str) -> list[SandboxViolation]:
        v = self.check_command(command)
        return [v] if v else []

    def validate_path(self, path: str) -> list[SandboxViolation]:
        v = self.check_path(path)
        return [v] if v else []

    async def _run_with_seccomp(
        self,
        command: str,
        args: dict[str, Any],
        timeout: float,
    ) -> SandboxResult:
        code = args.get("code", args.get("command", ""))
        if not code:
            return SandboxResult(success=True, output="")

        import sys
        wrapped_code = self._wrap_with_seccomp(code)

        cwd = self.config.workspace_dir or os.getcwd()
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", wrapped_code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        output = stdout.decode("utf-8", errors="replace")[:self.config.max_output_bytes]
        error_out = stderr.decode("utf-8", errors="replace")[:self.config.max_output_bytes]

        return SandboxResult(
            success=proc.returncode == 0,
            output=output,
            error=error_out,
            exit_code=proc.returncode or 0,
        )

    @staticmethod
    def _wrap_with_seccomp(code: str) -> str:
        if not _HAS_SECCOMP:
            return code
        wrapper = '''
import seccomp
import sys

filt = seccomp.Filter()
filt.add_rule(seccomp.KILL, "execve")
filt.add_rule(seccomp.KILL, "fork")
filt.add_rule(seccomp.KILL, "vfork")
filt.add_rule(seccomp.ALLOW, "read")
filt.add_rule(seccomp.ALLOW, "write")
filt.add_rule(seccomp.ALLOW, "open")
filt.add_rule(seccomp.ALLOW, "close")
filt.add_rule(seccomp.ALLOW, "mmap")
filt.add_rule(seccomp.ALLOW, "munmap")
filt.add_rule(seccomp.ALLOW, "brk")
filt.add_rule(seccomp.ALLOW, "exit_group")
filt.load()

'''
        return wrapper + "\n" + code


__all__ = ["SeccompSandbox"]
