"""Container sandbox adapter boundary."""

from __future__ import annotations

import subprocess
from pathlib import Path


class DockerSandboxAdapter:
    """Optional Docker-backed sandbox adapter.

    Defaults to disabled to avoid assuming Docker is installed or safe to run.
    """

    def __init__(self, enabled: bool = False, image: str = "python:3.12-slim") -> None:
        self.enabled = enabled
        self.image = image

    def run(self, command: list[str], workspace: Path) -> dict:
        if not self.enabled:
            return {
                "status": "unavailable",
                "reason": "Docker sandbox is disabled.",
                "command": command,
            }

        docker_command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{Path(workspace).resolve()}:/workspace",
            "-w",
            "/workspace",
            self.image,
            *command,
        ]
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            shell=False,
            timeout=120,
        )
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": docker_command,
        }
