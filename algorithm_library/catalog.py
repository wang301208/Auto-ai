"""Algorithm catalog for discovery and search.

Provides a unified view of all registered algorithms with
search, filter, and recommendation capabilities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .registry import AlgorithmManifest, AlgorithmRegistry, AlgorithmStatus


@dataclass
class CatalogEntry:
    """Extended catalog entry with computed fields."""

    manifest: AlgorithmManifest
    is_active: bool = False
    has_rollback: bool = False
    available_versions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "description": self.manifest.description,
            "status": self.manifest.status.value,
            "tags": self.manifest.tags,
            "metrics": self.manifest.metrics,
            "is_active": self.is_active,
            "has_rollback": self.has_rollback,
            "available_versions": self.available_versions,
        }


class AlgorithmCatalog:
    """Discovery and search interface over the algorithm registry.

    Provides higher-level query capabilities beyond simple filtering,
    including tag-based search, metric-based ranking, and
    algorithm recommendation.
    """

    def __init__(self, registry: AlgorithmRegistry | None = None) -> None:
        self.registry = registry or AlgorithmRegistry()

    def list_all(self) -> list[CatalogEntry]:
        manifests = self.registry.list_algorithms()
        version_map: dict[str, list[str]] = {}
        for m in manifests:
            version_map.setdefault(m.name, []).append(m.version)
        entries: list[CatalogEntry] = []
        for m in manifests:
            entries.append(
                CatalogEntry(
                    manifest=m,
                    is_active=m.status == AlgorithmStatus.ACTIVE,
                    has_rollback=m.rollback_to is not None,
                    available_versions=version_map.get(m.name, [m.version]),
                )
            )
        return entries

    def search(
        self,
        query: str = "",
        tags: list[str] | None = None,
        status: AlgorithmStatus | None = None,
    ) -> list[CatalogEntry]:
        query_lower = query.lower()
        entries = self.list_all()
        results: list[CatalogEntry] = []
        for entry in entries:
            if query_lower:
                searchable = (
                    f"{entry.manifest.name} {entry.manifest.description} "
                    f"{' '.join(entry.manifest.tags)}"
                ).lower()
                if query_lower not in searchable:
                    continue
            if tags:
                if not all(t in entry.manifest.tags for t in tags):
                    continue
            if status is not None and entry.manifest.status != status:
                continue
            results.append(entry)
        return results

    def get_active_versions(self) -> dict[str, CatalogEntry]:
        result: dict[str, CatalogEntry] = {}
        for entry in self.list_all():
            if entry.is_active:
                result[entry.manifest.name] = entry
        return result

    def rank_by_metric(
        self,
        metric_name: str,
        descending: bool = True,
        status: AlgorithmStatus | None = AlgorithmStatus.ACTIVE,
    ) -> list[CatalogEntry]:
        entries = self.list_all()
        if status is not None:
            entries = [e for e in entries if e.manifest.status == status]
        scored: list[tuple[float, CatalogEntry]] = []
        for entry in entries:
            value = entry.manifest.metrics.get(metric_name, float("-inf"))
            scored.append((value, entry))
        scored.sort(key=lambda x: x[0], reverse=descending)
        return [entry for _, entry in scored]

    def recommend_alternative(
        self,
        name: str,
        version: str,
    ) -> CatalogEntry | None:
        """Recommend the best alternative algorithm for the same task.

        Finds active algorithms sharing the same tags as the given algorithm,
        ranked by composite score.
        """
        manifest = self.registry.get(name, version)
        if manifest is None:
            return None
        candidates: list[CatalogEntry] = []
        for entry in self.list_all():
            if not entry.is_active:
                continue
            if entry.manifest.name == name and entry.manifest.version == version:
                continue
            shared_tags = set(entry.manifest.tags) & set(manifest.tags)
            if shared_tags:
                candidates.append(entry)
        if not candidates:
            return None
        candidates.sort(
            key=lambda e: sum(e.manifest.metrics.values()), reverse=True
        )
        return candidates[0]

    def export_catalog(self, path: Path) -> None:
        data = [entry.to_dict() for entry in self.list_all()]
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
