"""Agent blueprint metadata with pluggable thinking engine support."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ThinkingEngineRef:
    """Reference to a versioned algorithm used by an agent."""

    name: str
    version: str
    evaluation_suite: str


@dataclass
class AgentBlueprint:
    """Serializable agent blueprint."""

    role_name: str
    version: str
    agent_class: str
    thinking_engine: ThinkingEngineRef
    authorized_plugins: list[str] = field(default_factory=list)
    subscribed_events: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "AgentBlueprint":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        thinking_engine = ThinkingEngineRef(**data.pop("thinking_engine"))
        return cls(thinking_engine=thinking_engine, **data)

    def save(self, path: str | Path) -> None:
        output = asdict(self)
        Path(path).write_text(
            yaml.safe_dump(output, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
