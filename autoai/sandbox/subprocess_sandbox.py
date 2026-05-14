"""基于子进程的沙箱 — 跨平台（Windows/Linux/macOS）。

在子进程中运行命令，具有以下特性：
  - 预执行验证（命令白名单、路径检查）
  - 超时强制执行
  - 输出大小限制
  - 工作目录限制
  - 环境隔离
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from .base import SandboxBackend, SandboxConfig, SandboxResult, SandboxViolation, ViolationType


class SubprocessSandbox(SandboxBackend):
    """跨平台子进程沙箱."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        super().__init__(config)

    async def execute(
        self,
        command: str,
        args: dict[str, Any],
        timeout: float | None = None,
    ) -> SandboxResult:
        violations: list[SandboxViolation] = []
        start = time.monotonic()

        cmd_violation = self.check_command(command)
        if cmd_violation:
            violations.append(cmd_violation)
            return SandboxResult(
                success=False,
                error=f"Command blocked: {command}",
                violations=violations,
                duration_seconds=time.monotonic() - start,
            )

        path_arg = args.get("path", args.get("filename", ""))
        if path_arg:
            path_violation = self.check_path(str(path_arg))
            if path_violation:
                violations.append(path_violation)
                return SandboxResult(
                    success=False,
                    error=f"Path denied: {path_arg}",
                    violations=violations,
                    duration_seconds=time.monotonic() - start,
                )

        effective_timeout = timeout or self.config.timeout_seconds

        if command in ("execute_code", "execute_shell") and not self.config.allow_subprocess:
            violations.append(SandboxViolation(
                type=ViolationType.COMMAND_BLOCKED,
                detail="Subprocess execution not allowed in sandbox",
                command=command,
            ))
            return SandboxResult(
                success=False,
                error="Subprocess execution blocked",
                violations=violations,
                duration_seconds=time.monotonic() - start,
            )

        try:
            result = await self._run_in_subprocess(command, args, effective_timeout)
            result.violations = violations
            result.duration_seconds = time.monotonic() - start
            return result
        except asyncio.TimeoutError:
            violations.append(SandboxViolation(
                type=ViolationType.TIMEOUT,
                detail=f"Execution timed out after {effective_timeout}s",
                command=command,
            ))
            return SandboxResult(
                success=False,
                error=f"Timeout after {effective_timeout}s",
                violations=violations,
                duration_seconds=time.monotonic() - start,
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                error=str(e),
                violations=violations,
                duration_seconds=time.monotonic() - start,
            )

    def validate_command(self, command: str) -> list[SandboxViolation]:
        violations = []
        v = self.check_command(command)
        if v:
            violations.append(v)
        return violations

    def validate_path(self, path: str) -> list[SandboxViolation]:
        violations = []
        v = self.check_path(path)
        if v:
            violations.append(v)
        return violations

    async def _run_in_subprocess(
        self,
        command: str,
        args: dict[str, Any],
        timeout: float,
    ) -> SandboxResult:
        code = args.get("code", args.get("command", ""))
        if not code:
            return SandboxResult(success=True, output="", metadata={"command": command})

        cwd = self.config.workspace_dir or os.getcwd()
        env = dict(os.environ)
        if not self.config.allow_network:
            env.pop("HTTP_PROXY", None)
            env.pop("HTTPS_PROXY", None)
            env.pop("http_proxy", None)
            env.pop("https_proxy", None)

        try:
            proc = await asyncio.create_subprocess_exec(
                *self._build_exec_args(code),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
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

        except FileNotFoundError:
            return SandboxResult(
                success=False,
                error="Python interpreter not found",
            )

    @staticmethod
    def _build_exec_args(code: str) -> list[str]:
        import sys
        return [sys.executable, "-c", code]


__all__ = ["SubprocessSandbox"]
