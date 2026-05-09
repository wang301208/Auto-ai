"""Container sandbox adapter boundary."""

from __future__ import annotations

import subprocess
from pathlib import Path


class DockerSandboxAdapter:
    """Optional Docker-backed sandbox adapter.

    Defaults to enabled and unrestricted; unavailable Docker is reported clearly.
    """

    def __init__(
        self,
        enabled: bool = True,
        image: str = "python:3.12-slim",
        dry_run: bool = False,
        memory_limit: str = "512m",
        cpus: str = "1.0",
        pids_limit: int = 256,
        network_mode: str | None = None,
        read_only: bool = False,
    ) -> None:
        self.enabled = enabled
        self.image = image
        self.dry_run = dry_run
        self.memory_limit = memory_limit
        self.cpus = cpus
        self.pids_limit = pids_limit
        self.network_mode = network_mode
        self.read_only = read_only

    def run(self, command: list[str], workspace: Path) -> dict:
        workspace_mount = f"{Path(workspace).resolve()}:/workspace"
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--memory",
            self.memory_limit,
            "--cpus",
            self.cpus,
            "--pids-limit",
            str(self.pids_limit),
            "-v",
            f"{workspace_mount}:rw",
            "-w",
            "/workspace",
            self.image,
            *command,
        ]
        insert_at = 3
        if self.network_mode:
            docker_command[insert_at:insert_at] = ["--network", self.network_mode]
            insert_at += 2
        if self.read_only:
            docker_command[insert_at:insert_at] = [
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
            ]
        if not self.enabled:
            return {
                "status": "unavailable",
                "reason": "Docker sandbox is disabled.",
                "command": command,
                "docker_command": docker_command,
                "workspace_mount": workspace_mount,
            }
        if self.dry_run:
            return {
                "status": "dry_run",
                "command": docker_command + [workspace_mount],
                "docker_command": docker_command,
                "workspace_mount": workspace_mount,
            }
        try:
            result = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                shell=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "status": "unavailable",
                "reason": str(exc),
                "command": docker_command,
                "workspace_mount": workspace_mount,
            }
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": docker_command,
            "workspace_mount": workspace_mount,
        }
