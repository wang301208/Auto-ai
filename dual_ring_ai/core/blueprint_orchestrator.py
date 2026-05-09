"""Filesystem-backed organizational blueprint loader."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .agent_blueprint import AgentBlueprint


class BlueprintOrchestrator:
    """Load and hot-reload agent blueprints from a local charter directory."""

    def __init__(self, charter_path: str | Path) -> None:
        self.charter_path = Path(charter_path)
        self._signatures: dict[Path, str] = {}
        self._roles_by_path: dict[Path, str] = {}
        self._blueprints: dict[str, AgentBlueprint] = {}

    def load_blueprints(self) -> dict[str, AgentBlueprint]:
        """Load all YAML blueprints and remember their modification times."""
        loaded: dict[str, AgentBlueprint] = {}
        for path in self._blueprint_paths():
            blueprint = AgentBlueprint.load(path)
            loaded[blueprint.role_name] = blueprint
            self._signatures[path] = self._signature(path)
            self._roles_by_path[path] = blueprint.role_name
        self._blueprints = loaded
        return dict(self._blueprints)

    def reload_changed(self) -> dict[str, AgentBlueprint]:
        """Reload changed blueprints and return the full current map."""
        if not self._blueprints:
            return self.load_blueprints()

        current_paths = set(self._blueprint_paths())
        for removed_path in set(self._signatures) - current_paths:
            self._signatures.pop(removed_path, None)
            role_name = self._roles_by_path.pop(removed_path, None)
            if role_name is not None:
                self._blueprints.pop(role_name, None)

        for path in self._blueprint_paths():
            signature = self._signature(path)
            if self._signatures.get(path) == signature:
                continue
            blueprint = AgentBlueprint.load(path)
            self._blueprints[blueprint.role_name] = blueprint
            self._signatures[path] = signature
            self._roles_by_path[path] = blueprint.role_name
        return dict(self._blueprints)

    def _blueprint_paths(self) -> list[Path]:
        return sorted(self.charter_path.glob("*.yaml")) + sorted(
            self.charter_path.glob("*.yml")
        )

    @staticmethod
    def _signature(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
