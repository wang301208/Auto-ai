"""语义压缩引擎: 将大量知识压缩为紧凑的概念摘要。

核心思想:
- 信息瓶颈原理: 保留任务相关信息，丢弃噪声
- 概念抽象: 从具体实例中提取共性
- 渐进压缩: 细节->中等->抽象 三级压缩
- 熵感知: 根据信息熵决定压缩力度
"""

from __future__ import annotations

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class CompressionLevel(Enum):
    NONE = 0
    DETAIL = 1
    MODERATE = 2
    ABSTRACT = 3


@dataclass
class ConceptDigest:
    """概念摘要: 一个知识片段的压缩表示。"""
    digest_id: str
    source_ids: list[str]
    abstract: str
    key_attributes: dict[str, Any] = field(default_factory=dict)
    coverage: float = 1.0
    fidelity: float = 1.0
    compression_ratio: float = 1.0
    level: CompressionLevel = CompressionLevel.NONE
    created_at: float = field(default_factory=time.time)

    @property
    def quality(self) -> float:
        return self.coverage * self.fidelity


@dataclass
class KnowledgeChunk:
    """待压缩的知识片段。"""
    chunk_id: str
    content: str
    attributes: dict[str, Any] = field(default_factory=dict)
    tokens: int = 0
    importance: float = 1.0
    domain: str = "general"

    @property
    def entropy(self) -> float:
        if not self.content:
            return 0.0
        freq: dict[str, int] = {}
        for c in self.content:
            freq[c] = freq.get(c, 0) + 1
        total = len(self.content)
        ent = 0.0
        for count in freq.values():
            p = count / total
            if p > 0:
                ent -= p * math.log2(p)
        return ent


class SemanticCompressor:
    """语义压缩器: 将知识图谱/文本压缩为紧凑表示。"""

    def __init__(self, target_ratio: float = 0.3):
        self._target_ratio = target_ratio
        self._digests: dict[str, ConceptDigest] = {}
        self._abstraction_rules: list[dict[str, Any]] = []
        self._compressions_done: int = 0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    def compress_chunks(
        self,
        chunks: list[KnowledgeChunk],
        level: CompressionLevel = CompressionLevel.MODERATE,
    ) -> ConceptDigest:
        """将多个知识片段压缩为一个概念摘要。"""
        if not chunks:
            return ConceptDigest(
                digest_id="empty",
                source_ids=[],
                abstract="",
                level=level,
            )
        source_ids = [c.chunk_id for c in chunks]
        total_tokens = sum(c.tokens for c in chunks)
        all_attrs: dict[str, list[Any]] = {}
        for chunk in chunks:
            for k, v in chunk.attributes.items():
                all_attrs.setdefault(k, []).append(v)
        key_attrs = self._extract_common_attrs(all_attrs, len(chunks))
        abstract = self._generate_abstract(chunks, level)
        output_tokens = len(abstract.split())
        coverage = self._compute_coverage(chunks, abstract)
        fidelity = self._compute_fidelity(chunks, key_attrs)
        ratio = output_tokens / total_tokens if total_tokens > 0 else 1.0
        digest_id = f"digest_{len(self._digests)}"
        digest = ConceptDigest(
            digest_id=digest_id,
            source_ids=source_ids,
            abstract=abstract,
            key_attributes=key_attrs,
            coverage=coverage,
            fidelity=fidelity,
            compression_ratio=ratio,
            level=level,
        )
        self._digests[digest_id] = digest
        self._compressions_done += 1
        self._total_input_tokens += total_tokens
        self._total_output_tokens += output_tokens
        return digest

    def _extract_common_attrs(self, all_attrs: dict[str, list[Any]], count: int) -> dict[str, Any]:
        result = {}
        for k, values in all_attrs.items():
            if len(values) < count * 0.5:
                continue
            numeric_vals = [v for v in values if isinstance(v, (int, float))]
            if numeric_vals:
                result[f"{k}_avg"] = sum(numeric_vals) / len(numeric_vals)
                result[f"{k}_min"] = min(numeric_vals)
                result[f"{k}_max"] = max(numeric_vals)
            else:
                freq: dict[str, int] = {}
                for v in values:
                    key = str(v)
                    freq[key] = freq.get(key, 0) + 1
                most_common = max(freq, key=freq.get)
                result[k] = most_common
        return result

    def _generate_abstract(self, chunks: list[KnowledgeChunk], level: CompressionLevel) -> str:
        if level == CompressionLevel.NONE:
            return " | ".join(c.content for c in chunks)
        if level == CompressionLevel.DETAIL:
            sentences = []
            for c in chunks:
                parts = c.content.split(". ")
                sentences.extend(parts[:3])
            return ". ".join(sentences[:10])
        if level == CompressionLevel.MODERATE:
            domains = sorted(set(c.domain for c in chunks))
            key_concepts: list[str] = []
            for c in chunks:
                words = c.content.split()
                key_concepts.extend(words[:5])
            unique = list(dict.fromkeys(key_concepts))[:15]
            return f"[{','.join(domains)}] {' '.join(unique)}"
        if level == CompressionLevel.ABSTRACT:
            domains = sorted(set(c.domain for c in chunks))
            avg_importance = sum(c.importance for c in chunks) / len(chunks)
            return f"[{','.join(domains)}] n={len(chunks)} importance={avg_importance:.2f}"
        return ""

    def _compute_coverage(self, chunks: list[KnowledgeChunk], abstract: str) -> float:
        if not chunks or not abstract:
            return 0.0
        abstract_words = set(abstract.lower().split())
        covered = 0
        total_unique = 0
        for chunk in chunks:
            chunk_words = set(chunk.content.lower().split())
            if chunk_words:
                overlap = len(abstract_words & chunk_words) / len(chunk_words)
                covered += overlap
                total_unique += 1
        return covered / total_unique if total_unique > 0 else 0.0

    def _compute_fidelity(self, chunks: list[KnowledgeChunk], key_attrs: dict[str, Any]) -> float:
        if not key_attrs:
            return 0.5
        total_match = 0
        total_check = 0
        for chunk in chunks:
            for k, v in key_attrs.items():
                base_k = k.replace("_avg", "").replace("_min", "").replace("_max", "")
                if base_k in chunk.attributes:
                    total_check += 1
                    if str(chunk.attributes[base_k]) == str(v):
                        total_match += 1
        return total_match / total_check if total_check > 0 else 0.5

    def progressive_compress(
        self,
        chunks: list[KnowledgeChunk],
    ) -> dict[CompressionLevel, ConceptDigest]:
        """渐进压缩: 生成三级压缩摘要。"""
        result = {}
        for level in (CompressionLevel.DETAIL, CompressionLevel.MODERATE, CompressionLevel.ABSTRACT):
            result[level] = self.compress_chunks(chunks, level)
        return result

    def decompress_hint(self, digest: ConceptDigest) -> str:
        """从摘要恢复提示(不是完整恢复，而是给Agent足够线索去回忆)。"""
        parts = [f"摘要: {digest.abstract}"]
        if digest.key_attributes:
            attr_str = ", ".join(f"{k}={v}" for k, v in digest.key_attributes.items())
            parts.append(f"关键属性: {attr_str}")
        parts.append(f"来源数: {len(digest.source_ids)}")
        parts.append(f"覆盖度: {digest.coverage:.2f}, 保真度: {digest.fidelity:.2f}")
        return "; ".join(parts)

    def get_digest(self, digest_id: str) -> ConceptDigest | None:
        return self._digests.get(digest_id)

    @property
    def stats(self) -> dict[str, Any]:
        actual_ratio = (
            self._total_output_tokens / self._total_input_tokens
            if self._total_input_tokens > 0 else 0.0
        )
        avg_quality = (
            sum(d.quality for d in self._digests.values()) / len(self._digests)
            if self._digests else 0.0
        )
        return {
            "compressions_done": self._compressions_done,
            "digests_stored": len(self._digests),
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "actual_ratio": actual_ratio,
            "target_ratio": self._target_ratio,
            "avg_quality": avg_quality,
        }
