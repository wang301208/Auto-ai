"""Knowledge Mesh: Decentralized knowledge sharing between agents.

Phase 19.3: Agents share knowledge fragments through:
  - Knowledge publishing (agent posts a knowledge fragment)
  - Knowledge querying (agents search by topic/skill/tags)
  - Deduplication (similar fragments merged, best version kept)
  - Versioning (knowledge evolves, old versions accessible)
  - Reputation-weighted quality (higher-reputation agents' knowledge ranked higher)

No central knowledge base — knowledge lives in the mesh, agents pull what they need.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from autoai.logs import logger


class KnowledgeStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    MERGED = "merged"
    REVOKED = "revoked"


@dataclass
class KnowledgeFragment:
    fragment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    title: str = ""
    content: str = ""
    topic: str = ""
    tags: list[str] = field(default_factory=list)
    author_id: str = ""
    version: int = 1
    parent_id: str = ""
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    quality_score: float = 0.5
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:12]


@dataclass
class KnowledgeQuery:
    topic: str = ""
    tags: list[str] = field(default_factory=list)
    author_id: str = ""
    min_quality: float = 0.0
    max_results: int = 10
    include_deprecated: bool = False


@dataclass
class KnowledgeVersion:
    fragment_id: str
    version: int
    content: str
    content_hash: str
    timestamp: str


class KnowledgeMesh:
    """Decentralized knowledge sharing network.

    Usage:
        mesh = KnowledgeMesh()
        mesh.register_agent("a1", reputation=0.9)
        fid = mesh.publish("a1", "Fix pattern for circular imports",
                           content="Use lazy imports...",
                           topic="python", tags=["import", "circular"])
        results = mesh.query(KnowledgeQuery(topic="python", tags=["import"]))
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_versions: int = 10,
        decay_factor: float = 0.95,
    ) -> None:
        self._sim_threshold = similarity_threshold
        self._max_versions = max_versions
        self._decay_factor = decay_factor
        self._agents: dict[str, float] = {}
        self._fragments: dict[str, KnowledgeFragment] = {}
        self._versions: dict[str, list[KnowledgeVersion]] = defaultdict(list)
        self._topic_index: dict[str, list[str]] = defaultdict(list)
        self._tag_index: dict[str, list[str]] = defaultdict(list)
        self._author_index: dict[str, list[str]] = defaultdict(list)

    def register_agent(self, agent_id: str, reputation: float = 1.0) -> None:
        self._agents[agent_id] = max(0.0, min(1.0, reputation))

    def update_reputation(self, agent_id: str, reputation: float) -> None:
        if agent_id in self._agents:
            self._agents[agent_id] = max(0.0, min(1.0, reputation))

    def publish(
        self,
        author_id: str,
        title: str,
        content: str,
        topic: str = "",
        tags: list[str] | None = None,
        quality_score: float | None = None,
    ) -> str:
        if author_id not in self._agents:
            self._agents[author_id] = 0.5

        reputation = self._agents[author_id]
        effective_quality = quality_score if quality_score is not None else reputation

        duplicate_id = self._find_duplicate(content, topic)
        if duplicate_id and duplicate_id in self._fragments:
            existing = self._fragments[duplicate_id]
            if effective_quality > existing.quality_score:
                return self._create_version(existing, content, author_id, effective_quality)
            return duplicate_id

        fragment = KnowledgeFragment(
            title=title,
            content=content,
            topic=topic,
            tags=tags or [],
            author_id=author_id,
            quality_score=effective_quality,
        )

        self._fragments[fragment.fragment_id] = fragment
        self._index_fragment(fragment)

        logger.debug(f"[KnowledgeMesh] Published: {fragment.fragment_id} by {author_id}")
        return fragment.fragment_id

    def query(self, query: KnowledgeQuery) -> list[KnowledgeFragment]:
        candidates: dict[str, float] = {}

        if query.topic:
            for fid in self._topic_index.get(query.topic, []):
                candidates[fid] = candidates.get(fid, 0.0) + 2.0

        if query.tags:
            for tag in query.tags:
                for fid in self._tag_index.get(tag, []):
                    candidates[fid] = candidates.get(fid, 0.0) + 1.0

        if query.author_id:
            for fid in self._author_index.get(query.author_id, []):
                candidates[fid] = candidates.get(fid, 0.0) + 0.5

        if not query.topic and not query.tags and not query.author_id:
            candidates = {fid: 0.0 for fid in self._fragments}

        results = []
        for fid, score in candidates.items():
            frag = self._fragments.get(fid)
            if frag is None:
                continue
            if frag.status != KnowledgeStatus.ACTIVE and not query.include_deprecated:
                continue
            if frag.quality_score < query.min_quality:
                continue

            age_days = self._age_in_days(frag.created_at)
            time_decay = self._decay_factor ** age_days
            final_score = (
                score * 0.4
                + frag.quality_score * 0.3
                + (frag.usage_count / (frag.usage_count + 1)) * 0.2
                + time_decay * 0.1
            )

            results.append((frag, final_score))

        results.sort(key=lambda x: x[1], reverse=True)
        selected = [r[0] for r in results[:query.max_results]]

        for frag in selected:
            frag.usage_count += 1

        return selected

    def deprecate(self, fragment_id: str) -> bool:
        frag = self._fragments.get(fragment_id)
        if frag is None:
            return False
        frag.status = KnowledgeStatus.DEPRECATED
        return True

    def revoke(self, fragment_id: str, author_id: str) -> bool:
        frag = self._fragments.get(fragment_id)
        if frag is None or frag.author_id != author_id:
            return False
        frag.status = KnowledgeStatus.REVOKED
        self._unindex_fragment(frag)
        return True

    def get_versions(self, fragment_id: str) -> list[KnowledgeVersion]:
        return self._versions.get(fragment_id, [])

    def get_fragment(self, fragment_id: str) -> KnowledgeFragment | None:
        return self._fragments.get(fragment_id)

    def merge_fragments(self, primary_id: str, secondary_id: str) -> bool:
        primary = self._fragments.get(primary_id)
        secondary = self._fragments.get(secondary_id)
        if primary is None or secondary is None:
            return False
        if primary.topic != secondary.topic:
            return False

        merged_content = f"{primary.content}\n\n--- Merged from {secondary_id} ---\n{secondary.content}"
        self._create_version(primary, merged_content, primary.author_id, primary.quality_score)
        secondary.status = KnowledgeStatus.MERGED
        return True

    def _create_version(
        self,
        fragment: KnowledgeFragment,
        new_content: str,
        author_id: str,
        quality: float,
    ) -> str:
        version_record = KnowledgeVersion(
            fragment_id=fragment.fragment_id,
            version=fragment.version,
            content=fragment.content,
            content_hash=fragment.content_hash,
            timestamp=fragment.created_at,
        )
        self._versions[fragment.fragment_id].append(version_record)

        if len(self._versions[fragment.fragment_id]) > self._max_versions:
            self._versions[fragment.fragment_id] = self._versions[fragment.fragment_id][-self._max_versions:]

        fragment.version += 1
        fragment.content = new_content
        fragment.content_hash = hashlib.sha256(new_content.encode()).hexdigest()[:12]
        fragment.quality_score = quality
        fragment.created_at = datetime.now(timezone.utc).isoformat()

        return fragment.fragment_id

    def _find_duplicate(self, content: str, topic: str) -> str | None:
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        for fid in self._topic_index.get(topic, []):
            frag = self._fragments.get(fid)
            if frag and frag.content_hash == content_hash:
                return fid
        return None

    def _index_fragment(self, fragment: KnowledgeFragment) -> None:
        if fragment.topic:
            self._topic_index[fragment.topic].append(fragment.fragment_id)
        for tag in fragment.tags:
            self._tag_index[tag].append(fragment.fragment_id)
        self._author_index[fragment.author_id].append(fragment.fragment_id)

    def _unindex_fragment(self, fragment: KnowledgeFragment) -> None:
        if fragment.topic:
            self._topic_index[fragment.topic] = [
                fid for fid in self._topic_index[fragment.topic] if fid != fragment.fragment_id
            ]
        for tag in fragment.tags:
            self._tag_index[tag] = [
                fid for fid in self._tag_index[tag] if fid != fragment.fragment_id
            ]

    @staticmethod
    def _age_in_days(iso_timestamp: str) -> float:
        try:
            created = datetime.fromisoformat(iso_timestamp)
            delta = datetime.now(timezone.utc) - created
            return max(0.0, delta.total_seconds() / 86400.0)
        except Exception:
            return 0.0

    @property
    def fragment_count(self) -> int:
        return sum(1 for f in self._fragments.values() if f.status == KnowledgeStatus.ACTIVE)

    def get_status(self) -> dict[str, Any]:
        return {
            "agents": len(self._agents),
            "total_fragments": len(self._fragments),
            "active_fragments": self.fragment_count,
            "topics": list(self._topic_index.keys()),
            "tags": list(self._tag_index.keys()),
        }


__all__ = [
    "KnowledgeMesh",
    "KnowledgeFragment",
    "KnowledgeQuery",
    "KnowledgeStatus",
    "KnowledgeVersion",
]
