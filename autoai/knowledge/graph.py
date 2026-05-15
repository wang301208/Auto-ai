"""知识图谱自构建: Agent自主构建、维护、推理知识图谱。

核心能力:
- 从观察/经验中自动提取实体和关系
- 知识自动链接(语义相似度+结构邻近)
- 冲突检测与消解
- 图谱动态生长与修剪
- 多跳推理与路径发现
"""

from __future__ import annotations

import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class NodeType(Enum):
    CONCEPT = "concept"
    ENTITY = "entity"
    EVENT = "event"
    PROCEDURE = "procedure"
    PROPERTY = "property"
    DOMAIN = "domain"


class EdgeType(Enum):
    IS_A = "is_a"
    PART_OF = "part_of"
    CAUSES = "causes"
    RELATED = "related"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    IMPLIES = "implies"
    INSTANCE_OF = "instance_of"


@dataclass
class KnowledgeNode:
    node_id: str
    label: str
    node_type: NodeType = NodeType.CONCEPT
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "observation"
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = 0.0

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = time.time()

    def merge_attributes(self, other: dict[str, Any], weight: float = 0.5) -> None:
        for k, v in other.items():
            if k not in self.attributes:
                self.attributes[k] = v
            elif isinstance(v, (int, float)) and isinstance(self.attributes[k], (int, float)):
                self.attributes[k] = self.attributes[k] * (1 - weight) + v * weight

    @property
    def importance(self) -> float:
        recency = 1.0 / (1.0 + self.age / 86400.0)
        frequency = min(1.0, self.access_count / 10.0)
        return 0.5 * self.confidence + 0.25 * recency + 0.25 * frequency


@dataclass
class KnowledgeEdge:
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.RELATED
    weight: float = 1.0
    confidence: float = 1.0
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def is_strong(self) -> bool:
        return self.weight >= 0.7 and self.confidence >= 0.7

    def add_evidence(self, source: str) -> None:
        if source not in self.evidence:
            self.evidence.append(source)
            self.confidence = min(1.0, 0.5 + 0.1 * len(self.evidence))

    def weaken(self, factor: float = 0.8) -> None:
        self.weight *= factor
        self.confidence *= factor


@dataclass
class InferencePath:
    start_id: str
    end_id: str
    node_ids: list[str]
    edge_ids: list[str]
    total_weight: float
    length: int

    @property
    def confidence(self) -> float:
        return self.total_weight / self.length if self.length > 0 else 0.0


@dataclass
class Conflict:
    node_a_id: str
    node_b_id: str
    conflict_type: str
    description: str
    resolution: str = "unresolved"
    resolved_at: float = 0.0


class KnowledgeGraph:
    """知识图谱: Agent的内部知识表示与推理引擎。"""

    def __init__(self, graph_id: str = "default"):
        self.graph_id = graph_id
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[str, KnowledgeEdge] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._conflicts: list[Conflict] = []
        self._inferences_made: int = 0
        self._auto_link_threshold: float = 0.6
        self._prune_threshold: float = 0.05
        self._created_at = time.time()

    def _make_id(self, *parts: str) -> str:
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def add_node(
        self,
        label: str,
        node_type: NodeType = NodeType.CONCEPT,
        attributes: dict[str, Any] | None = None,
        confidence: float = 1.0,
        source: str = "observation",
    ) -> KnowledgeNode:
        existing = self.find_node(label, node_type)
        if existing:
            if attributes:
                existing.merge_attributes(attributes)
            existing.confidence = min(1.0, existing.confidence + 0.1 * confidence)
            existing.touch()
            return existing
        node_id = self._make_id(label, node_type.value)
        node = KnowledgeNode(
            node_id=node_id,
            label=label,
            node_type=node_type,
            attributes=attributes or {},
            confidence=confidence,
            source=source,
        )
        self._nodes[node_id] = node
        self._adjacency[node_id] = set()
        logger.debug(f"知识图谱: 新增节点 '{label}' ({node_type.value})")
        return node

    def find_node(self, label: str, node_type: NodeType | None = None) -> KnowledgeNode | None:
        for node in self._nodes.values():
            if node.label == label:
                if node_type is None or node.node_type == node_type:
                    return node
        return None

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        node = self._nodes.get(node_id)
        if node:
            node.touch()
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.RELATED,
        weight: float = 1.0,
        confidence: float = 1.0,
        evidence: str = "",
    ) -> KnowledgeEdge | None:
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        if source_id == target_id:
            return None
        for edge in self._edges.values():
            if edge.source_id == source_id and edge.target_id == target_id and edge.edge_type == edge_type:
                if evidence:
                    edge.add_evidence(evidence)
                edge.weight = min(1.0, edge.weight + 0.1 * weight)
                return edge
        edge_id = self._make_id(source_id, target_id, edge_type.value)
        edge = KnowledgeEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            confidence=confidence,
            evidence=[evidence] if evidence else [],
        )
        self._edges[edge_id] = edge
        self._adjacency.setdefault(source_id, set()).add(target_id)
        self._adjacency.setdefault(target_id, set()).add(source_id)
        if edge_type == EdgeType.CONTRADICTS:
            self._register_conflict(source_id, target_id, edge_id)
        return edge

    def _register_conflict(self, node_a_id: str, node_b_id: str, edge_id: str) -> None:
        conflict = Conflict(
            node_a_id=node_a_id,
            node_b_id=node_b_id,
            conflict_type="contradiction",
            description=f"节点{node_a_id}与{node_b_id}矛盾",
        )
        self._conflicts.append(conflict)

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        edges_to_remove = [
            eid for eid, e in self._edges.items()
            if e.source_id == node_id or e.target_id == node_id
        ]
        for eid in edges_to_remove:
            del self._edges[eid]
        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        for neighbors in self._adjacency.values():
            neighbors.discard(node_id)
        return True

    def neighbors(self, node_id: str, edge_type: EdgeType | None = None) -> list[KnowledgeNode]:
        if node_id not in self._adjacency:
            return []
        result = []
        for nid in self._adjacency[node_id]:
            if nid not in self._nodes:
                continue
            if edge_type is not None:
                has_edge = any(
                    e.edge_type == edge_type
                    for e in self._edges.values()
                    if (e.source_id == node_id and e.target_id == nid)
                    or (e.target_id == node_id and e.source_id == nid)
                )
                if not has_edge:
                    continue
            result.append(self._nodes[nid])
        return result

    def find_paths(self, start_id: str, end_id: str, max_depth: int = 5) -> list[InferencePath]:
        if start_id not in self._nodes or end_id not in self._nodes:
            return []
        paths: list[InferencePath] = []
        visited: set[str] = set()
        self._dfs_paths(start_id, end_id, max_depth, [start_id], [], 1.0, visited, paths)
        paths.sort(key=lambda p: p.total_weight, reverse=True)
        return paths[:10]

    def _dfs_paths(
        self,
        current: str,
        target: str,
        max_depth: int,
        node_path: list[str],
        edge_path: list[str],
        weight: float,
        visited: set[str],
        results: list[InferencePath],
    ) -> None:
        if current == target:
            results.append(InferencePath(
                start_id=node_path[0],
                end_id=target,
                node_ids=list(node_path),
                edge_ids=list(edge_path),
                total_weight=weight,
                length=len(edge_path),
            ))
            return
        if len(node_path) > max_depth:
            return
        visited.add(current)
        for eid, edge in self._edges.items():
            next_id = None
            if edge.source_id == current and edge.target_id not in visited:
                next_id = edge.target_id
            elif edge.target_id == current and edge.source_id not in visited:
                next_id = edge.source_id
            if next_id is not None:
                new_weight = weight * edge.weight * edge.confidence
                if new_weight < 0.01:
                    continue
                node_path.append(next_id)
                edge_path.append(eid)
                self._dfs_paths(next_id, target, max_depth, node_path, edge_path, new_weight, visited, results)
                node_path.pop()
                edge_path.pop()
        visited.discard(current)

    def auto_link(self, similarity_fn: Any = None) -> int:
        """自动链接: 基于属性相似度为节点创建RELATED边。"""
        linked = 0
        nodes = list(self._nodes.values())
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i + 1:]:
                if n1.node_type != n2.node_type:
                    continue
                sim = self._compute_similarity(n1, n2)
                if sim >= self._auto_link_threshold:
                    edge = self.add_edge(
                        n1.node_id, n2.node_id,
                        EdgeType.RELATED, weight=sim, confidence=sim * 0.8,
                        evidence="auto_link",
                    )
                    if edge:
                        linked += 1
        return linked

    def _compute_similarity(self, a: KnowledgeNode, b: KnowledgeNode) -> float:
        if not a.attributes or not b.attributes:
            label_sim = 1.0 if a.label == b.label else 0.0
            return label_sim
        common = set(a.attributes) & set(b.attributes)
        if not common:
            return 0.0
        match = 0
        for k in common:
            if a.attributes[k] == b.attributes[k]:
                match += 1
        return match / len(common)

    def infer_transitive(self) -> int:
        """传递推理: A is_a B, B is_a C => A is_a C。"""
        inferred = 0
        is_a_edges = [e for e in self._edges.values() if e.edge_type == EdgeType.IS_A]
        for e1 in is_a_edges:
            for e2 in is_a_edges:
                if e1.target_id == e2.source_id and e1.source_id != e2.target_id:
                    existing = any(
                        e.source_id == e1.source_id and e.target_id == e2.target_id
                        for e in self._edges.values()
                        if e.edge_type == EdgeType.IS_A
                    )
                    if not existing:
                        edge = self.add_edge(
                            e1.source_id, e2.target_id,
                            EdgeType.IS_A,
                            weight=min(e1.weight, e2.weight) * 0.9,
                            confidence=min(e1.confidence, e2.confidence) * 0.9,
                            evidence="transitive_inference",
                        )
                        if edge:
                            inferred += 1
                            self._inferences_made += 1
        return inferred

    def detect_conflicts(self) -> list[Conflict]:
        """检测知识冲突(包括已有的和新发现的)。"""
        new_conflicts = []
        for edge in self._edges.values():
            if edge.edge_type == EdgeType.CONTRADICTS and edge.is_strong:
                existing = any(
                    (c.node_a_id == edge.source_id and c.node_b_id == edge.target_id)
                    or (c.node_a_id == edge.target_id and c.node_b_id == edge.source_id)
                    for c in self._conflicts
                )
                if not existing:
                    conflict = Conflict(
                        node_a_id=edge.source_id,
                        node_b_id=edge.target_id,
                        conflict_type="contradiction",
                        description=f"矛盾边: {edge.source_id} vs {edge.target_id}",
                    )
                    self._conflicts.append(conflict)
                    new_conflicts.append(conflict)
        all_strong = [c for c in self._conflicts if c.resolution == "unresolved"]
        return new_conflicts if new_conflicts else all_strong

    def resolve_conflict(self, conflict: Conflict, winner_id: str) -> None:
        """解决冲突: 保留胜者，削弱败者。"""
        loser_id = conflict.node_b_id if winner_id == conflict.node_a_id else conflict.node_a_id
        if loser_id in self._nodes:
            self._nodes[loser_id].confidence *= 0.5
        for edge in self._edges.values():
            if edge.edge_type == EdgeType.CONTRADICTS:
                if edge.source_id == conflict.node_a_id and edge.target_id == conflict.node_b_id:
                    edge.weaken(0.1)
        conflict.resolution = f"winner:{winner_id}"
        conflict.resolved_at = time.time()

    def prune(self, threshold: float | None = None) -> int:
        """修剪低重要性节点。"""
        th = threshold or self._prune_threshold
        to_prune = [nid for nid, node in self._nodes.items() if node.importance < th]
        for nid in to_prune:
            self.remove_node(nid)
        return len(to_prune)

    def observe_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        subject_type: NodeType = NodeType.CONCEPT,
        object_type: NodeType = NodeType.CONCEPT,
        edge_type: EdgeType = EdgeType.RELATED,
        confidence: float = 1.0,
    ) -> tuple[KnowledgeNode, KnowledgeEdge, KnowledgeNode]:
        """观察三元组并自动构建图谱。"""
        src = self.add_node(subject, subject_type, confidence=confidence, source="triple_observation")
        tgt = self.add_node(obj, object_type, confidence=confidence, source="triple_observation")
        edge = self.add_edge(
            src.node_id, tgt.node_id, edge_type,
            weight=confidence, confidence=confidence,
            evidence=f"{predicate}:observed",
        )
        if edge is None:
            edge = KnowledgeEdge(
                edge_id=self._make_id(src.node_id, tgt.node_id, "fallback"),
                source_id=src.node_id,
                target_id=tgt.node_id,
                edge_type=edge_type,
                weight=confidence,
                confidence=confidence,
            )
        return src, edge, tgt

    def query_related(self, label: str, depth: int = 2) -> list[KnowledgeNode]:
        """查询与某概念相关的所有节点(广度优先)。"""
        start = self.find_node(label)
        if not start:
            return []
        visited: set[str] = {start.node_id}
        frontier: set[str] = {start.node_id}
        result = [start]
        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for neighbor in self.neighbors(nid):
                    if neighbor.node_id not in visited:
                        visited.add(neighbor.node_id)
                        next_frontier.add(neighbor.node_id)
                        result.append(neighbor)
            frontier = next_frontier
            if not frontier:
                break
        return result

    @property
    def conflicts(self) -> list[Conflict]:
        return list(self._conflicts)

    @property
    def stats(self) -> dict[str, Any]:
        unresolved = [c for c in self._conflicts if c.resolution == "unresolved"]
        return {
            "graph_id": self.graph_id,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "node_types": {t.value: sum(1 for n in self._nodes.values() if n.node_type == t) for t in NodeType},
            "edge_types": {t.value: sum(1 for e in self._edges.values() if e.edge_type == t) for t in EdgeType},
            "conflicts_total": len(self._conflicts),
            "conflicts_unresolved": len(unresolved),
            "inferences_made": self._inferences_made,
            "avg_confidence": (
                sum(n.confidence for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0.0
            ),
        }
