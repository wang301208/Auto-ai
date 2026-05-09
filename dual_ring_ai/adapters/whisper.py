"""Whisper speech-to-text adapter boundary."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WhisperAdapter:
    """Command boundary for local Whisper transcription.

    It runs when enabled. Dry-run mode exposes the exact command that would
    be executed so humans can audit the integration.
    """

    enabled: bool = True
    dry_run: bool = False
    executable: str = "whisper"
    model: str = "base"
    language: str | None = None
    timeout: int = 180

    def transcribe(self, audio_path: str | Path) -> dict[str, Any]:
        audio_path = Path(audio_path)
        command = [
            self.executable,
            str(audio_path),
            "--model",
            self.model,
            "--output_format",
            "json",
        ]
        if self.language:
            command.extend(["--language", self.language])

        if not self.enabled:
            return {
                "status": "disabled",
                "reason": "Whisper is disabled.",
                "command": command,
            }
        if self.dry_run:
            return {"status": "dry_run", "command": command}
        if not audio_path.exists():
            return {
                "status": "failed",
                "reason": f"audio file not found: {audio_path}",
                "command": command,
            }

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=False,
                timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "status": "unavailable",
                "reason": str(exc),
                "command": command,
            }
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
        }
