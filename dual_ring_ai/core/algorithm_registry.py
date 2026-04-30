"""Filesystem-backed registry for versioned thinking algorithms."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AlgorithmManifest:
    """Metadata for a thinking engine implementation."""

    name: str
    version: str
    description: str
    source_module: str
    status: str
    metrics: dict[str, float]
    rollback_to: str | None
    evaluation_suite: str


class AlgorithmRegistry:
    """Store algorithm manifests under `algorithm_library/<name>_<version>`."""

    def __init__(self, root_path: str | Path = "algorithm_library") -> None:
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def register(self, manifest: AlgorithmManifest) -> Path:
        target_dir = self._manifest_dir(manifest.name, manifest.version)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "algorithm.json").write_text(
            json.dumps(asdict(manifest), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target_dir

    def get(self, name: str, version: str) -> AlgorithmManifest:
        manifest_path = self._manifest_dir(name, version) / "algorithm.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return AlgorithmManifest(**data)

    def list_algorithms(self) -> list[AlgorithmManifest]:
        manifests: list[AlgorithmManifest] = []
        for manifest_path in sorted(self.root_path.glob("*/algorithm.json")):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifests.append(AlgorithmManifest(**data))
        return manifests

    def _manifest_dir(self, name: str, version: str) -> Path:
        return self.root_path / f"{name}_{version}"
