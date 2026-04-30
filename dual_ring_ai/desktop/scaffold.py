"""Scaffold metadata for a future Tauri desktop shell."""

from __future__ import annotations

import json
from pathlib import Path


class DesktopScaffold:
    """Write a minimal desktop contract without requiring Node or Rust."""

    COMMANDS = [
        "get_status",
        "list_approvals",
        "decide_approval",
        "list_algorithm_proposals",
    ]

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path)

    def write_contract(self, api_base_url: str) -> dict:
        src_tauri = self.root_path / "src-tauri"
        src_tauri.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": "dual-ring-ai-desktop",
            "api_base_url": api_base_url,
            "commands": self.COMMANDS,
        }
        (src_tauri / "dual-ring-contract.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (self.root_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "dual-ring-ai-desktop",
                    "private": True,
                    "scripts": {
                        "dev": "tauri dev",
                        "build": "tauri build",
                    },
                    "dependencies": {},
                    "devDependencies": {},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return manifest
