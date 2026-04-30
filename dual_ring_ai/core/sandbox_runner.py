"""Local bounded runner for generated skills."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .skill_lifecycle import SandboxPolicy


@dataclass
class SandboxRunResult:
    return_code: int
    output: dict[str, Any]
    stderr: str
    command: list[str]
    workspace: Path


class SandboxRunner:
    """Run a skill with policy checks and argv-only subprocess execution."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def run_skill(
        self,
        skill_dir: str | Path,
        parameters: dict[str, Any],
        policy: SandboxPolicy,
        timeout: int,
    ) -> SandboxRunResult:
        policy_errors = policy.validate()
        skill_dir = Path(skill_dir)
        main_file = skill_dir / "main.py"
        command = self._build_command(main_file, parameters)

        if policy_errors:
            return SandboxRunResult(
                return_code=126,
                output={"status": "blocked", "errors": policy_errors},
                stderr="; ".join(policy_errors),
                command=command,
                workspace=self.workspace_path,
            )

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(skill_dir),
            shell=False,
        )
        try:
            output = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            output = {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout.strip(),
            }
        return SandboxRunResult(
            return_code=result.returncode,
            output=output,
            stderr=result.stderr,
            command=command,
            workspace=self.workspace_path,
        )

    def _build_command(self, main_file: Path, parameters: dict[str, Any]) -> list[str]:
        command = [sys.executable, str(main_file)]
        for key, value in parameters.items():
            command.extend([f"--{key}", str(value)])
        return command
