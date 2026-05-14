"""Sandbox execution environment for AutoAI.

Provides isolated execution of agent commands with:
  - Filesystem access control (allow/deny lists)
  - Resource limits (CPU time, memory, timeout)
  - Network access control
  - Command whitelist enforcement
  - Platform-adaptive backends (subprocess cross-platform, seccomp on Linux)

Usage:
    from autoai.sandbox import SubprocessSandbox, SandboxConfig

    config = SandboxConfig(allowed_commands={"read_file", "write_file"})
    sandbox = SubprocessSandbox(config)
    result = await sandbox.execute("read_file", {"path": "test.txt"})
"""

from .base import SandboxBackend, SandboxConfig, SandboxResult, SandboxViolation
from .subprocess_sandbox import SubprocessSandbox

SeccompSandbox = None
try:
    from .seccomp_sandbox import SeccompSandbox
except (ImportError, Exception):
    pass

__all__ = [
    "SandboxBackend",
    "SandboxConfig",
    "SandboxResult",
    "SandboxViolation",
    "SubprocessSandbox",
    "SeccompSandbox",
]
