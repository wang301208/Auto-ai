"""Python-side terminal UI placeholders for the retained TUI integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TUIConfig:
    """Configuration for terminal UI sessions."""

    prompt: str = "助手"


class TerminalUI:
    """Minimal Python handle for terminal UI integrations."""

    def __init__(self, config: TUIConfig | None = None, runtime: Any | None = None) -> None:
        self.config = config or TUIConfig()
        self.runtime = runtime

    def handle_text(self, text: str) -> dict[str, Any]:
        if self.runtime is None:
            return {"text": text, "status": "received"}
        return self.runtime.handle_interaction(text)


def create_tui(config: TUIConfig | None = None, runtime: Any | None = None) -> TerminalUI:
    """Create the retained terminal UI integration object."""

    return TerminalUI(config=config, runtime=runtime)
