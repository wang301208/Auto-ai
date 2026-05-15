from __future__ import annotations

import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WASIViolationType(Enum):
    FD_READ_DENIED = "fd_read_denied"
    FD_WRITE_DENIED = "fd_write_denied"
    SOCK_OPEN_DENIED = "sock_open_denied"
    SOCK_SEND_DENIED = "sock_send_denied"
    ENV_GET_DENIED = "env_get_denied"
    PROC_EXEC_DENIED = "proc_exec_denied"
    MEMORY_EXCEEDED = "memory_exceeded"
    TIMEOUT_EXCEEDED = "timeout_exceeded"


@dataclass
class WASIViolation:
    violation_type: WASIViolationType
    detail: str
    component_id: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class WASISandboxConfig:
    allow_fs_read: bool = True
    allow_fs_write: bool = False
    allow_network: bool = False
    allow_env: bool = False
    allow_subprocess: bool = False
    max_memory_bytes: int = 10 * 1024 * 1024
    timeout_seconds: float = 30.0
    allowed_paths: set[str] = field(default_factory=set)
    denied_paths: set[str] = field(default_factory=lambda: {"/etc", "/root", "~/.ssh"})


class WASMSandbox:
    """WASM沙箱：基于WASI能力的安全执行环境。"""

    def __init__(self, config: WASISandboxConfig | None = None):
        self.config = config or WASISandboxConfig()
        self._violations: list[WASIViolation] = []
        self._execution_log: list[dict] = []

    def check_permission(self, component_id: str, permission: str, resource: str = "") -> bool:
        if permission == "fs_read":
            if not self.config.allow_fs_read:
                self._record_violation(component_id, WASIViolationType.FD_READ_DENIED, f"文件读取被拒: {resource}")
                return False
            if self._is_path_denied(resource):
                self._record_violation(component_id, WASIViolationType.FD_READ_DENIED, f"路径禁止读取: {resource}")
                return False
        elif permission == "fs_write":
            if not self.config.allow_fs_write:
                self._record_violation(component_id, WASIViolationType.FD_WRITE_DENIED, f"文件写入被拒: {resource}")
                return False
            if self._is_path_denied(resource):
                self._record_violation(component_id, WASIViolationType.FD_WRITE_DENIED, f"路径禁止写入: {resource}")
                return False
        elif permission == "network":
            if not self.config.allow_network:
                self._record_violation(component_id, WASIViolationType.SOCK_OPEN_DENIED, f"网络访问被拒: {resource}")
                return False
        elif permission == "env":
            if not self.config.allow_env:
                self._record_violation(component_id, WASIViolationType.ENV_GET_DENIED, f"环境变量访问被拒")
                return False
        elif permission == "subprocess":
            if not self.config.allow_subprocess:
                self._record_violation(component_id, WASIViolationType.PROC_EXEC_DENIED, f"子进程执行被拒: {resource}")
                return False
        return True

    def create_strict_config(self) -> WASISandboxConfig:
        return WASISandboxConfig(
            allow_fs_read=True,
            allow_fs_write=False,
            allow_network=False,
            allow_env=False,
            allow_subprocess=False,
            max_memory_bytes=5 * 1024 * 1024,
            timeout_seconds=10.0,
        )

    def create_moderate_config(self) -> WASISandboxConfig:
        return WASISandboxConfig(
            allow_fs_read=True,
            allow_fs_write=True,
            allow_network=True,
            allow_env=False,
            allow_subprocess=False,
            max_memory_bytes=20 * 1024 * 1024,
            timeout_seconds=30.0,
        )

    def create_permissive_config(self) -> WASISandboxConfig:
        return WASISandboxConfig(
            allow_fs_read=True,
            allow_fs_write=True,
            allow_network=True,
            allow_env=True,
            allow_subprocess=True,
            max_memory_bytes=50 * 1024 * 1024,
            timeout_seconds=60.0,
        )

    def _is_path_denied(self, path: str) -> bool:
        for denied in self.config.denied_paths:
            if path.startswith(denied) or path.startswith(f"~{denied}"):
                return True
        return False

    def _record_violation(self, component_id: str, vtype: WASIViolationType, detail: str) -> None:
        violation = WASIViolation(
            violation_type=vtype,
            detail=detail,
            component_id=component_id,
        )
        self._violations.append(violation)
        logger.warning(f"WASM沙箱违规: {vtype.value} - {detail}")

    def get_violations(self, component_id: str | None = None) -> list[WASIViolation]:
        if component_id:
            return [v for v in self._violations if v.component_id == component_id]
        return list(self._violations)

    def get_stats(self) -> dict:
        return {"total_violations": len(self._violations), "config": {
            "fs_read": self.config.allow_fs_read,
            "fs_write": self.config.allow_fs_write,
            "network": self.config.allow_network,
            "subprocess": self.config.allow_subprocess,
        }}
