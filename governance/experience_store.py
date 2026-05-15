"""Experience Store: Persistent memory of fix patterns for cross-task reuse.

When an agent successfully fixes an issue, the fix pattern is abstracted
and stored. Next time a similar issue is encountered, the agent can
instantly apply the learned pattern instead of re-discovering the fix.

This is the core of "Agent gets smarter over time":
    fix_success → abstract_pattern → store → next_similar_issue → instant_apply

Patterns are keyed by:
    - issue_type (lint/bug/test/perf/security)
    - language (python/javascript/etc)
    - symptom_pattern (regex matching the error message/output)
    - fix_action (the actual patch or command that fixed it)

Storage: JSONL file with atomic writes, thread-safe.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from enum import Enum


class IssueType(Enum):
    LINT = "lint"
    BUG = "bug"
    TEST = "test"
    PERF = "perf"
    SECURITY = "security"
    REFACTOR = "refactor"
    TODO = "todo"
    UNKNOWN = "unknown"


@dataclass
class FixPattern:
    pattern_id: str
    issue_type: IssueType
    language: str
    symptom_pattern: str
    fix_action: str
    target_pattern: str
    success_count: int = 1
    failure_count: int = 0
    last_used: str = ""
    created_at: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.last_used:
            self.last_used = self.created_at

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "issue_type": self.issue_type.value,
            "language": self.language,
            "symptom_pattern": self.symptom_pattern,
            "fix_action": self.fix_action,
            "target_pattern": self.target_pattern,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FixPattern:
        return cls(
            pattern_id=d["pattern_id"],
            issue_type=IssueType(d["issue_type"]),
            language=d["language"],
            symptom_pattern=d["symptom_pattern"],
            fix_action=d["fix_action"],
            target_pattern=d["target_pattern"],
            success_count=d.get("success_count", 1),
            failure_count=d.get("failure_count", 0),
            last_used=d.get("last_used", ""),
            created_at=d.get("created_at", ""),
            confidence=d.get("confidence", 1.0),
            metadata=d.get("metadata", {}),
        )


class ExperienceStore:
    """Persistent store of fix patterns with matching and scoring.

    Usage:
        store = ExperienceStore(workspace=Path("."))
        store.record_success(
            issue_type="lint",
            symptom="unused variable 'x'",
            fix_action="removed unused variable",
            language="python",
        )
        patterns = store.match(symptom="unused variable 'y'")
        # → returns the pattern above because symptom matches
    """

    def __init__(self, workspace: Path | None = None, store_file: str = "experience_store.jsonl") -> None:
        self._patterns: dict[str, FixPattern] = {}
        self._lock = threading.Lock()
        self._workspace = workspace
        if workspace is not None:
            self._store_path = workspace / store_file
            self._load()
        else:
            self._store_path = None

    def record_success(
        self,
        issue_type: IssueType | str,
        symptom: str,
        fix_action: str,
        language: str = "python",
        target_pattern: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> FixPattern:
        it = issue_type if isinstance(issue_type, IssueType) else IssueType(issue_type)
        key = self._make_key(it, language, symptom)

        with self._lock:
            if key in self._patterns:
                p = self._patterns[key]
                p.success_count += 1
                p.last_used = datetime.now(timezone.utc).isoformat()
                p.confidence = min(1.0, p.confidence + 0.05)
                if metadata:
                    p.metadata.update(metadata)
            else:
                p = FixPattern(
                    pattern_id=key,
                    issue_type=it,
                    language=language,
                    symptom_pattern=symptom,
                    fix_action=fix_action,
                    target_pattern=target_pattern,
                    confidence=0.5,
                    metadata=metadata or {},
                )
                self._patterns[key] = p

            self._persist(p)
            return p

    def record_failure(self, issue_type: IssueType | str, symptom: str, language: str = "python") -> None:
        it = issue_type if isinstance(issue_type, IssueType) else IssueType(issue_type)
        key = self._make_key(it, language, symptom)

        with self._lock:
            if key in self._patterns:
                p = self._patterns[key]
                p.failure_count += 1
                p.confidence = max(0.0, p.confidence - 0.1)
                self._persist(p)

    def match(
        self,
        symptom: str,
        issue_type: IssueType | str | None = None,
        language: str | None = None,
        min_confidence: float = 0.3,
        limit: int = 5,
    ) -> list[FixPattern]:
        import re as _re

        with self._lock:
            candidates = list(self._patterns.values())

        scored: list[tuple[float, FixPattern]] = []
        for p in candidates:
            if p.confidence < min_confidence:
                continue
            if issue_type is not None:
                it = issue_type if isinstance(issue_type, IssueType) else IssueType(issue_type)
                if p.issue_type != it:
                    continue
            if language is not None and p.language != language:
                continue

            score = 0.0
            if p.symptom_pattern and symptom:
                if p.symptom_pattern.lower() in symptom.lower():
                    score += 0.5
                try:
                    if _re.search(p.symptom_pattern, symptom, _re.IGNORECASE):
                        score += 0.3
                except _re.error:
                    pass

            score += p.confidence * 0.2
            score += p.success_rate * 0.2

            if score > 0.1:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_pattern(self, pattern_id: str) -> FixPattern | None:
        return self._patterns.get(pattern_id)

    @property
    def size(self) -> int:
        return len(self._patterns)

    def stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        total_success = 0
        total_failure = 0
        for p in self._patterns.values():
            by_type[p.issue_type.value] = by_type.get(p.issue_type.value, 0) + 1
            total_success += p.success_count
            total_failure += p.failure_count
        return {
            "total_patterns": len(self._patterns),
            "by_type": by_type,
            "total_success_applications": total_success,
            "total_failure_applications": total_failure,
        }

    def _make_key(self, issue_type: IssueType, language: str, symptom: str) -> str:
        import hashlib
        raw = f"{issue_type.value}:{language}:{symptom[:100]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def merge_from(self, other: ExperienceStore, min_confidence: float = 0.5, dedup: bool = True) -> int:
        """Merge patterns from another ExperienceStore (cross-project migration).

        Only merges patterns above min_confidence. If dedup=True, skips
        patterns with identical symptom_pattern+language that already exist locally.
        Returns count of merged patterns.
        """
        merged = 0
        with self._lock:
            for key, pattern in other._patterns.items():
                if pattern.confidence < min_confidence:
                    continue
                if dedup:
                    existing = any(
                        p.symptom_pattern == pattern.symptom_pattern
                        and p.language == pattern.language
                        for p in self._patterns.values()
                    )
                    if existing:
                        continue
                if key in self._patterns:
                    existing = self._patterns[key]
                    existing.success_count += pattern.success_count
                    existing.failure_count += pattern.failure_count
                    total = existing.success_count + existing.failure_count
                    existing.confidence = existing.success_count / total if total > 0 else 0.0
                    existing.metadata.setdefault("merged_from", []).append(pattern.metadata.get("project", "unknown"))
                else:
                    import copy
                    new_p = copy.deepcopy(pattern)
                    new_p.confidence = min(pattern.confidence, 0.7)
                    new_p.metadata["migrated"] = True
                    self._patterns[key] = new_p
                merged += 1
            if merged > 0:
                self._persist_all()
        return merged

    def generalize_patterns(self, similarity_threshold: float = 0.8) -> int:
        """Generalize similar patterns by merging overlapping symptom_patterns.

        When two patterns have the same issue_type+language and overlapping
        symptom patterns, merge the less confident into the more confident.
        Returns count of merged pairs.
        """
        import re as _re
        merged_count = 0
        with self._lock:
            patterns_by_key: dict[tuple, list[FixPattern]] = {}
            for p in self._patterns.values():
                k = (p.issue_type, p.language)
                patterns_by_key.setdefault(k, []).append(p)

            for key_group, group in patterns_by_key.items():
                if len(group) < 2:
                    continue
                i = 0
                while i < len(group):
                    j = i + 1
                    while j < len(group):
                        p1, p2 = group[i], group[j]
                        if p1.symptom_pattern and p2.symptom_pattern:
                            shorter = min(len(p1.symptom_pattern), len(p2.symptom_pattern))
                            longer = max(len(p1.symptom_pattern), len(p2.symptom_pattern))
                            if shorter / longer >= similarity_threshold:
                                if p1.confidence >= p2.confidence:
                                    p1.success_count += p2.success_count
                                    p1.failure_count += p2.failure_count
                                    self._patterns.pop(p2.pattern_id, None)
                                else:
                                    p2.success_count += p1.success_count
                                    p2.failure_count += p1.failure_count
                                    self._patterns.pop(p1.pattern_id, None)
                                group.pop(j)
                                merged_count += 1
                                continue
                        j += 1
                    i += 1

            if merged_count > 0:
                self._persist_all()
        return merged_count

    def denoise(self, min_applications: int = 1, max_failure_rate: float = 0.95) -> int:
        """Remove noisy patterns: rarely used and almost always failing.

        A pattern is noisy if:
            - total applications < min_applications
            - OR failure_rate > max_failure_rate
        Returns count of removed patterns.
        """
        removed = 0
        with self._lock:
            to_remove = []
            for pid, p in self._patterns.items():
                total = p.success_count + p.failure_count
                if total < min_applications:
                    to_remove.append(pid)
                elif total > 0 and (p.failure_count / total) > max_failure_rate:
                    to_remove.append(pid)

            for pid in to_remove:
                del self._patterns[pid]
                removed += 1

            if removed > 0:
                self._persist_all()
        return removed

    def query_similar(self, symptom: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Query for similar patterns, returning dict format for BoundaryManager compatibility."""
        patterns = self.match(symptom=symptom, limit=top_k)
        return [
            {
                "pattern_id": p.pattern_id,
                "issue_type": p.issue_type.value,
                "symptom": p.symptom_pattern,
                "fix_action": p.fix_action,
                "confidence": p.confidence,
                "success_rate": p.success_rate,
                "constraints": p.metadata.get("constraints", {}),
            }
            for p in patterns
        ]

    def _persist(self, pattern: FixPattern) -> None:
        self._persist_all()

    def _persist_all(self) -> None:
        if self._store_path is None:
            return
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        all_data = {}
        for pid, p in self._patterns.items():
            all_data[pid] = p.to_dict()
        tmp = self._store_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        tmp.replace(self._store_path)

    def export_patterns(self) -> list[dict[str, Any]]:
        """Export all patterns for cross-project sharing."""
        with self._lock:
            return [p.to_dict() for p in self._patterns.values()]

    def import_patterns(self, patterns: list[dict[str, Any]], source_project: str = "unknown") -> int:
        """Import patterns from another project. Returns count imported."""
        imported = 0
        for pdict in patterns:
            pdict.setdefault("metadata", {})["project"] = source_project
            p = FixPattern.from_dict(pdict)
            with self._lock:
                if p.pattern_id not in self._patterns:
                    self._patterns[p.pattern_id] = p
                    imported += 1
        if imported > 0:
            self._persist_all()
        return imported

    def _load(self) -> None:
        if self._store_path is None or not self._store_path.exists():
            return
        try:
            with open(self._store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for pid, pdict in data.items():
                self._patterns[pid] = FixPattern.from_dict(pdict)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass


__all__ = ["IssueType", "FixPattern", "ExperienceStore"]
