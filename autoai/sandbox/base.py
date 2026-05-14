"""沙箱基础类型和抽象接口。"""

from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Coroutine


class ViolationType(enum.Enum):
    COMMAND_BLOCKED = "command_blocked"
    PATH_DENIED = "path_denied"
    NETWORK_DENIED = "network_denied"
    RESOURCE_EXCEEDED = "resource_exceeded"
    TIMEOUT = "timeout"
    SANDBOX_ESCAPE = "sandbox_escape"


@dataclass
class SandboxViolation:
    type: ViolationType
    detail: str
    command: str = ""
    path: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SandboxResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration_seconds: float = 0.0
    violations: list[SandboxViolation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0


@dataclass
class SandboxConfig:
    enabled: bool = True
    allowed_commands: set[str] = field(default_factory=lambda: {
        "read_file", "write_file", "append_to_file", "list_files",
        "download_file", "analyze_code", "execute_code",
        "web_search", "web_browse",
    })
    denied_commands: set[str] = field(default_factory=lambda: {
        "execute_shell", "delete_file", "move_file",
    })
    allowed_paths: set[str] = field(default_factory=set)
    denied_paths: set[str] = field(default_factory=lambda: {
        "/etc", "/root", "/home", "~",
        "C:\\Windows", "C:\\Program Files",
    })
    max_output_bytes: int = 1_000_000
    timeout_seconds: float = 120.0
    max_memory_mb: int = 512
    max_cpu_seconds: float = 60.0
    allow_network: bool = False
    allow_subprocess: bool = False
    workspace_dir: str = ""

    def is_command_allowed(self, command: str) -> bool:
        if command in self.denied_commands:
            return False
        if self.allowed_commands and command not in self.allowed_commands:
            return False
        return True

    def is_path_allowed(self, path: str) -> bool:
        import os
        normalized = os.path.normpath(path)
        for denied in self.denied_paths:
            expanded = os.path.expanduser(denied)
            if normalized.startswith(expanded) or normalized.startswith(os.path.normpath(expanded)):
                return False
        if self.allowed_paths:
            for allowed in self.allowed_paths:
                expanded = os.path.expanduser(allowed)
                if normalized.startswith(expanded) or normalized.startswith(os.path.normpath(expanded)):
                    return True
            return False
        if self.workspace_dir:
            workspace_norm = os.path.normpath(self.workspace_dir)
            if normalized.startswith(workspace_norm):
                return True
            return False
        return True


class SandboxBackend(abc.ABC):
    """抽象沙箱后端。"""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()

    @abc.abstractmethod
    async def execute(
        self,
        command: str,
        args: dict[str, Any],
        timeout: float | None = None,
    ) -> SandboxResult:
        ...

    @abc.abstractmethod
    def validate_command(self, command: str) -> list[SandboxViolation]:
        ...

    @abc.abstractmethod
    def validate_path(self, path: str) -> list[SandboxViolation]:
        ...

    def check_command(self, command: str) -> SandboxViolation | None:
        if not self.config.is_command_allowed(command):
            return SandboxViolation(
                type=ViolationType.COMMAND_BLOCKED,
                detail=f"Command '{command}' is not in allowed list",
                command=command,
            )
        return None

    def check_path(self, path: str) -> SandboxViolation | None:
        if not self.config.is_path_allowed(path):
            return SandboxViolation(
                type=ViolationType.PATH_DENIED,
                detail=f"Path '{path}' is outside allowed scope",
                path=path,
            )
        return None


__all__ = [
    "ViolationType",
    "SandboxViolation",
    "SandboxResult",
    "SandboxConfig",
    "SandboxBackend",
]
