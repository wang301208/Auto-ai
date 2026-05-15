"""跨域知识迁移: 将一个领域的知识迁移到另一个领域。

核心机制:
- 类比映射: 找到结构相似的不同领域
- 关系迁移: 将源域的关系映射到目标域
- 抽象桥梁: 通过共同抽象层连接不同域
- 验证反馈: 迁移结果在新域中验证有效性
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class TransferStatus(Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PARTIAL = "partial"


@dataclass
class DomainBridge:
    """域桥: 两个领域之间的映射关系。"""
    bridge_id: str
    source_domain: str
    target_domain: str
    concept_map: dict[str, str] = field(default_factory=dict)
    relation_map: dict[str, str] = field(default_factory=dict)
    structural_similarity: float = 0.0
    transferability_score: float = 0.0
    status: TransferStatus = TransferStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    validations: int = 0
    successes: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.validations if self.validations > 0 else 0.0

    def record_validation(self, success: bool) -> None:
        self.validations += 1
        if success:
            self.successes += 1
        if self.validations >= 3:
            if self.success_rate >= 0.7:
                self.status = TransferStatus.VALIDATED
            elif self.success_rate >= 0.4:
                self.status = TransferStatus.PARTIAL
            else:
                self.status = TransferStatus.REJECTED

    def map_concept(self, source_concept: str) -> str | None:
        return self.concept_map.get(source_concept)

    def map_relation(self, source_relation: str) -> str | None:
        return self.relation_map.get(source_relation)


@dataclass
class TransferResult:
    """迁移结果: 一次知识迁移的输出。"""
    bridge_id: str
    transferred_knowledge: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    domain_utility: float = 0.0
    warnings: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_reliable(self) -> bool:
        return self.confidence >= 0.6 and len(self.warnings) == 0

    @property
    def quality(self) -> float:
        return self.confidence * self.domain_utility


@dataclass
class AnalogyCandidate:
    """类比候选: 两个可能类比的概念对。"""
    source_concept: str
    target_concept: str
    structural_score: float = 0.0
    semantic_score: float = 0.0
    contextual_score: float = 0.0

    @property
    def overall_score(self) -> float:
        return 0.4 * self.structural_score + 0.4 * self.semantic_score + 0.2 * self.contextual_score


class CrossDomainTransfer:
    """跨域知识迁移引擎。"""

    def __init__(self):
        self._bridges: dict[str, DomainBridge] = {}
        self._domain_profiles: dict[str, dict[str, Any]] = {}
        self._transfer_history: list[TransferResult] = []
        self._abstraction_layers: dict[str, str] = {}

    def register_domain(
        self,
        domain: str,
        concepts: list[str],
        relations: list[tuple[str, str, str]] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """注册领域知识概况。"""
        self._domain_profiles[domain] = {
            "concepts": concepts,
            "relations": relations or [],
            "attributes": attributes or {},
            "registered_at": time.time(),
        }
        logger.debug(f"跨域迁移: 注册领域 '{domain}', {len(concepts)}个概念")

    def discover_bridges(self, domain_a: str, domain_b: str) -> DomainBridge | None:
        """发现两个领域之间的桥接映射。"""
        prof_a = self._domain_profiles.get(domain_a)
        prof_b = self._domain_profiles.get(domain_b)
        if not prof_a or not prof_b:
            return None
        analogies = self._find_analogies(prof_a, prof_b)
        if not analogies:
            return None
        concept_map = {}
        for a in analogies:
            if a.overall_score >= 0.4:
                concept_map[a.source_concept] = a.target_concept
        struct_sim = self._compute_structural_similarity(prof_a, prof_b, concept_map)
        rel_map = self._infer_relation_mapping(prof_a, prof_b, concept_map)
        transferability = struct_sim * (len(concept_map) / max(len(prof_a["concepts"]), 1))
        bridge_id = f"bridge_{domain_a}_{domain_b}_{len(self._bridges)}"
        bridge = DomainBridge(
            bridge_id=bridge_id,
            source_domain=domain_a,
            target_domain=domain_b,
            concept_map=concept_map,
            relation_map=rel_map,
            structural_similarity=struct_sim,
            transferability_score=transferability,
        )
        self._bridges[bridge_id] = bridge
        logger.info(
            f"跨域迁移: 发现桥接 {domain_a}->{domain_b}, "
            f"映射{len(concept_map)}概念, 相似度{struct_sim:.2f}"
        )
        return bridge

    def _find_analogies(
        self,
        prof_a: dict[str, Any],
        prof_b: dict[str, Any],
    ) -> list[AnalogyCandidate]:
        candidates = []
        for c_a in prof_a["concepts"]:
            for c_b in prof_b["concepts"]:
                struct = self._concept_structural_match(c_a, c_b, prof_a, prof_b)
                semantic = self._concept_semantic_match(c_a, c_b)
                contextual = 0.5
                if struct > 0.3 or semantic > 0.3:
                    candidates.append(AnalogyCandidate(
                        source_concept=c_a,
                        target_concept=c_b,
                        structural_score=struct,
                        semantic_score=semantic,
                        contextual_score=contextual,
                    ))
        candidates.sort(key=lambda a: a.overall_score, reverse=True)
        used_source: set[str] = set()
        used_target: set[str] = set()
        filtered = []
        for a in candidates:
            if a.source_concept not in used_source and a.target_concept not in used_target:
                filtered.append(a)
                used_source.add(a.source_concept)
                used_target.add(a.target_concept)
        return filtered[:20]

    def _concept_structural_match(
        self,
        c_a: str,
        c_b: str,
        prof_a: dict[str, Any],
        prof_b: dict[str, Any],
    ) -> float:
        rel_a = [r for r in prof_a["relations"] if c_a in (r[0], r[2])]
        rel_b = [r for r in prof_b["relations"] if c_b in (r[0], r[2])]
        if not rel_a and not rel_b:
            return 0.5
        if not rel_a or not rel_b:
            return 0.1
        role_types_a = {r[1] for r in rel_a}
        role_types_b = {r[1] for r in rel_b}
        overlap = len(role_types_a & role_types_b)
        total = len(role_types_a | role_types_b)
        return overlap / total if total > 0 else 0.0

    def _concept_semantic_match(self, c_a: str, c_b: str) -> float:
        if c_a == c_b:
            return 1.0
        if c_a.lower() == c_b.lower():
            return 0.9
        set_a = set(c_a.lower().replace("_", " ").split())
        set_b = set(c_b.lower().replace("_", " ").split())
        if set_a & set_b:
            return len(set_a & set_b) / len(set_a | set_b)
        return 0.0

    def _compute_structural_similarity(
        self,
        prof_a: dict[str, Any],
        prof_b: dict[str, Any],
        concept_map: dict[str, str],
    ) -> float:
        if not concept_map:
            return 0.0
        rel_a = prof_a["relations"]
        rel_b = prof_b["relations"]
        mapped_rels_a = 0
        matching_rels = 0
        for s, r, o in rel_a:
            if s in concept_map and o in concept_map:
                mapped_rels_a += 1
                s_m = concept_map[s]
                o_m = concept_map[o]
                for s2, r2, o2 in rel_b:
                    if s2 == s_m and o2 == o_m:
                        matching_rels += 1
                        break
        if mapped_rels_a == 0:
            return len(concept_map) / max(len(prof_a["concepts"]), 1) * 0.5
        return matching_rels / mapped_rels_a

    def _infer_relation_mapping(
        self,
        prof_a: dict[str, Any],
        prof_b: dict[str, Any],
        concept_map: dict[str, str],
    ) -> dict[str, str]:
        rel_map: dict[str, str] = {}
        rel_type_pairs: dict[tuple[str, str], int] = {}
        for s, r_a, o in prof_a["relations"]:
            if s not in concept_map or o not in concept_map:
                continue
            s_m, o_m = concept_map[s], concept_map[o]
            for s2, r_b, o2 in prof_b["relations"]:
                if s2 == s_m and o2 == o_m:
                    pair = (r_a, r_b)
                    rel_type_pairs[pair] = rel_type_pairs.get(pair, 0) + 1
        for (r_a, r_b), count in rel_type_pairs.items():
            if r_a not in rel_map or count > rel_type_pairs.get((r_a, rel_map[r_a]), 0):
                rel_map[r_a] = r_b
        return rel_map

    def transfer(
        self,
        bridge: DomainBridge,
        knowledge: list[dict[str, Any]],
        validate_fn: Any = None,
    ) -> TransferResult:
        """通过桥接将知识从源域迁移到目标域。"""
        transferred = []
        warnings = []
        for item in knowledge:
            mapped_item = {}
            for k, v in item.items():
                if k == "concept":
                    mapped = bridge.map_concept(str(v))
                    if mapped:
                        mapped_item[k] = mapped
                    else:
                        warnings.append(f"无法映射概念: {v}")
                        mapped_item[k] = v
                elif k == "relation":
                    mapped = bridge.map_relation(str(v))
                    mapped_item[k] = mapped or v
                else:
                    mapped_item[k] = v
            if mapped_item:
                transferred.append(mapped_item)
        confidence = bridge.structural_similarity * bridge.transferability_score
        if bridge.status == TransferStatus.VALIDATED:
            confidence = min(1.0, confidence * 1.3)
        elif bridge.status == TransferStatus.REJECTED:
            confidence *= 0.3
        domain_utility = bridge.success_rate if bridge.validations > 0 else 0.5
        result = TransferResult(
            bridge_id=bridge.bridge_id,
            transferred_knowledge=transferred,
            confidence=confidence,
            domain_utility=domain_utility,
            warnings=warnings,
        )
        self._transfer_history.append(result)
        return result

    def set_abstraction(self, concept: str, abstraction: str) -> None:
        """为概念设置抽象层(跨域共享)。"""
        self._abstraction_layers[concept] = abstraction

    def find_shared_abstractions(self, domain_a: str, domain_b: str) -> list[str]:
        """找到两个域共享的抽象概念。"""
        prof_a = self._domain_profiles.get(domain_a, {})
        prof_b = self._domain_profiles.get(domain_b, {})
        concepts_a = set(prof_a.get("concepts", []))
        concepts_b = set(prof_b.get("concepts", []))
        shared = []
        for c_a in concepts_a:
            abs_a = self._abstraction_layers.get(c_a, c_a)
            for c_b in concepts_b:
                abs_b = self._abstraction_layers.get(c_b, c_b)
                if abs_a == abs_b and c_a != c_b:
                    shared.append(abs_a)
        return list(set(shared))

    def get_bridge(self, bridge_id: str) -> DomainBridge | None:
        return self._bridges.get(bridge_id)

    @property
    def stats(self) -> dict[str, Any]:
        validated = sum(1 for b in self._bridges.values() if b.status == TransferStatus.VALIDATED)
        avg_confidence = (
            sum(r.confidence for r in self._transfer_history) / len(self._transfer_history)
            if self._transfer_history else 0.0
        )
        return {
            "domains_registered": len(self._domain_profiles),
            "bridges_discovered": len(self._bridges),
            "bridges_validated": validated,
            "transfers_done": len(self._transfer_history),
            "avg_transfer_confidence": avg_confidence,
            "abstractions_defined": len(self._abstraction_layers),
        }
