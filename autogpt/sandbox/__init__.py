from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class Sandbox:
    """Execute commands inside a chroot based sandbox."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.busybox_path = shutil.which("busybox")
        if not self.busybox_path:
            raise RuntimeError("busybox is required for the sandbox")

        self._setup_busybox()

    def _setup_busybox(self) -> None:
        dst = self.root / "bin" / "busybox"
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.busybox_path, dst)
            dst.chmod(0o755)

    def run(
        self, command: str, *, timeout: float | None = None
    ) -> subprocess.CompletedProcess:
        """Run a shell command inside the sandbox."""
        chroot_cmd = [
            "chroot",
            str(self.root),
            "/bin/busybox",
            "sh",
            "-c",
            command,
        ]
        return subprocess.run(
            chroot_cmd, capture_output=True, text=True, timeout=timeout
        )
