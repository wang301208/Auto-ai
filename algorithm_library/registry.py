"""Algorithm registry for versioned algorithm manifests.

Stores algorithm metadata (name, version, status, metrics) as JSON files
under algorithm_library/<name>_<version>/algorithm.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class AlgorithmStatus(Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class AlgorithmManifest:
    """Metadata record for a registered algorithm.

    Attributes:
        name: Algorithm identifier.
        version: Semantic version string.
        description: Human-readable description.
        source_module: Python module path of the algorithm class.
        status: Lifecycle status (candidate, active, deprecated, retired).
        metrics: Performance/quality metrics from evaluation.
        tags: Categorization tags for search/filter.
        rollback_to: Version to roll back to if this algorithm fails.
        evaluation_suite: Name of the evaluation suite used for validation.
        created_at: ISO timestamp of registration.
        promoted_at: ISO timestamp of last promotion to active.
    """

    name: str
    version: str
    description: str = ""
    source_module: str = ""
    status: AlgorithmStatus = AlgorithmStatus.CANDIDATE
    metrics: dict[str, float] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    rollback_to: str | None = None
    evaluation_suite: str = ""
    created_at: str = ""
    promoted_at: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = AlgorithmStatus(self.status)

    @property
    def dir_name(self) -> str:
        return f"{self.name}_{self.version}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "source_module": self.source_module,
            "status": self.status.value,
            "metrics": self.metrics,
            "tags": self.tags,
            "rollback_to": self.rollback_to,
            "evaluation_suite": self.evaluation_suite,
            "created_at": self.created_at,
            "promoted_at": self.promoted_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlgorithmManifest:
        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            source_module=data.get("source_module", ""),
            status=data.get("status", "candidate"),
            metrics=data.get("metrics", {}),
            tags=data.get("tags", []),
            rollback_to=data.get("rollback_to"),
            evaluation_suite=data.get("evaluation_suite", ""),
            created_at=data.get("created_at", ""),
            promoted_at=data.get("promoted_at"),
        )


class AlgorithmRegistry:
    """File-system backed registry of algorithm manifests.

    Storage layout:
        <root_path>/<name>_<version>/algorithm.json
    """

    def __init__(self, root_path: str | Path = "algorithm_library") -> None:
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def register(self, manifest: AlgorithmManifest) -> Path:
        """Register or update an algorithm manifest."""
        from datetime import datetime

        if not manifest.created_at:
            manifest.created_at = datetime.utcnow().isoformat()
        algo_dir = self.root_path / manifest.dir_name
        algo_dir.mkdir(parents=True, exist_ok=True)
        path = algo_dir / "algorithm.json"
        path.write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def get(self, name: str, version: str) -> AlgorithmManifest | None:
        """Retrieve a specific algorithm manifest."""
        path = self.root_path / f"{name}_{version}" / "algorithm.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AlgorithmManifest.from_dict(data)
        except Exception:
            return None

    def list_algorithms(
        self,
        status: AlgorithmStatus | None = None,
        tag: str | None = None,
    ) -> list[AlgorithmManifest]:
        """List all registered algorithms, optionally filtered."""
        results: list[AlgorithmManifest] = []
        for path in sorted(self.root_path.glob("*/algorithm.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                manifest = AlgorithmManifest.from_dict(data)
            except Exception:
                continue
            if status is not None and manifest.status != status:
                continue
            if tag is not None and tag not in manifest.tags:
                continue
            results.append(manifest)
        return results

    def get_active(self, name: str) -> AlgorithmManifest | None:
        """Get the currently active version of an algorithm."""
        for manifest in self.list_algorithms(status=AlgorithmStatus.ACTIVE):
            if manifest.name == name:
                return manifest
        return None

    def update_status(
        self, name: str, version: str, new_status: AlgorithmStatus
    ) -> AlgorithmManifest | None:
        """Update the lifecycle status of an algorithm."""
        manifest = self.get(name, version)
        if manifest is None:
            return None
        manifest.status = new_status
        if new_status == AlgorithmStatus.ACTIVE:
            from datetime import datetime
            manifest.promoted_at = datetime.utcnow().isoformat()
        self.register(manifest)
        return manifest

    def deprecate_previous_versions(self, name: str, active_version: str) -> None:
        """Set all other active versions of an algorithm to deprecated."""
        for manifest in self.list_algorithms(status=AlgorithmStatus.ACTIVE):
            if manifest.name == name and manifest.version != active_version:
                self.update_status(manifest.name, manifest.version, AlgorithmStatus.DEPRECATED)
