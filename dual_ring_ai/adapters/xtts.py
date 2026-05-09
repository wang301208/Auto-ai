"""XTTS text-to-speech adapter boundary."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class XTTSAdapter:
    """Command boundary for local XTTS synthesis."""

    enabled: bool = True
    dry_run: bool = False
    executable: str = "xtts"
    speaker_wav: str | Path | None = None
    language: str = "zh-cn"
    timeout: int = 180

    def synthesize(self, text: str, output_path: str | Path) -> dict[str, Any]:
        output_path = Path(output_path)
        command = [
            self.executable,
            "--text",
            text,
            "--out_path",
            str(output_path),
            "--language",
            self.language,
        ]
        if self.speaker_wav is not None:
            command.extend(["--speaker_wav", str(self.speaker_wav)])

        if not self.enabled:
            return {
                "status": "disabled",
                "reason": "XTTS is disabled.",
                "command": command,
            }
        if self.dry_run:
            return {"status": "dry_run", "command": command, "output_path": str(output_path)}

        output_path.parent.mkdir(parents=True, exist_ok=True)
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
                "output_path": str(output_path),
            }
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
            "output_path": str(output_path),
        }
