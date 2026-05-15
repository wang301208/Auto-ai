from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class LoadLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CognitiveLoad:
    active_tasks: int = 0
    pending_decisions: int = 0
    context_window_usage: float = 0.0
    memory_pressure: float = 0.0
    emotional_valence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def total_load(self) -> float:
        task_load = min(1.0, self.active_tasks / 10.0)
        decision_load = min(1.0, self.pending_decisions / 5.0)
        return (
            task_load * 0.3
            + decision_load * 0.2
            + self.context_window_usage * 0.25
            + self.memory_pressure * 0.15
            + abs(self.emotional_valence) * 0.1
        )

    @property
    def level(self) -> LoadLevel:
        t = self.total_load
        if t < 0.3:
            return LoadLevel.LOW
        elif t < 0.6:
            return LoadLevel.MODERATE
        elif t < 0.85:
            return LoadLevel.HIGH
        return LoadLevel.CRITICAL

    @property
    def needs_relief(self) -> bool:
        return self.total_load >= 0.7


@dataclass
class CapabilityBoundary:
    capability: str
    confidence: float = 0.0
    evidence_count: int = 0
    last_tested: float = 0.0
    known_limitations: list[str] = field(default_factory=list)

    @property
    def is_within_boundary(self) -> bool:
        return self.confidence >= 0.3

    @property
    def needs_learning(self) -> bool:
        return self.confidence < 0.5 or self.evidence_count < 3


@dataclass
class KnowledgeGap:
    domain: str
    depth: float = 0.0
    relevance: float = 0.0
    examples_needed: int = 1
    discovered_at: float = field(default_factory=time.time)

    @property
    def priority(self) -> float:
        return self.relevance * (1.0 - self.depth)

    @property
    def is_critical(self) -> bool:
        return self.priority >= 0.7 and self.depth < 0.2


@dataclass
class AwarenessSnapshot:
    cognitive_load: CognitiveLoad = field(default_factory=CognitiveLoad)
    capabilities: list[CapabilityBoundary] = field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def overall_self_awareness(self) -> float:
        load_score = 1.0 - self.cognitive_load.total_load
        cap_scores = [c.confidence for c in self.capabilities] if self.capabilities else [0.5]
        cap_avg = sum(cap_scores) / len(cap_scores)
        gap_scores = [1.0 - g.depth for g in self.knowledge_gaps] if self.knowledge_gaps else [0.5]
        gap_avg = sum(gap_scores) / len(gap_scores)
        return load_score * 0.3 + cap_avg * 0.4 + (1.0 - gap_avg) * 0.3


class SelfAwarenessLoop:
    """自我意识回路: 持续内省Agent自身状态。"""

    def __init__(self, agent_id: str = "aware"):
        self.agent_id = agent_id
        self._load = CognitiveLoad()
        self._capabilities: dict[str, CapabilityBoundary] = {}
        self._gaps: list[KnowledgeGap] = []
        self._reflection_count = 0
        self._history: list[AwarenessSnapshot] = []

    def update_load(self, active_tasks: int = 0, pending_decisions: int = 0,
                    context_usage: float = 0.0, memory_pressure: float = 0.0,
                    emotional_valence: float = 0.0) -> CognitiveLoad:
        self._load = CognitiveLoad(
            active_tasks=active_tasks,
            pending_decisions=pending_decisions,
            context_window_usage=context_usage,
            memory_pressure=memory_pressure,
            emotional_valence=emotional_valence,
        )
        return self._load

    def register_capability(self, name: str, confidence: float = 0.5,
                            limitations: list[str] | None = None) -> CapabilityBoundary:
        cap = CapabilityBoundary(
            capability=name,
            confidence=confidence,
            evidence_count=1,
            last_tested=time.time(),
            known_limitations=limitations or [],
        )
        self._capabilities[name] = cap
        return cap

    def test_capability(self, name: str, success: bool) -> None:
        cap = self._capabilities.get(name)
        if cap is None:
            cap = self.register_capability(name)
        cap.evidence_count += 1
        cap.last_tested = time.time()
        alpha = 0.3
        if success:
            cap.confidence = cap.confidence * (1 - alpha) + 1.0 * alpha
        else:
            cap.confidence = cap.confidence * (1 - alpha) + 0.0 * alpha

    def discover_gap(self, domain: str, relevance: float = 0.5, depth: float = 0.0) -> KnowledgeGap:
        for gap in self._gaps:
            if gap.domain == domain:
                gap.relevance = max(gap.relevance, relevance)
                gap.depth = max(gap.depth, depth)
                return gap
        gap = KnowledgeGap(domain=domain, relevance=relevance, depth=depth)
        self._gaps.append(gap)
        logger.info(f"发现知识缺口: {domain} (relevance={relevance:.2f}, depth={depth:.2f})")
        return gap

    def reflect(self) -> AwarenessSnapshot:
        snapshot = AwarenessSnapshot(
            cognitive_load=self._load,
            capabilities=list(self._capabilities.values()),
            knowledge_gaps=list(self._gaps),
        )
        self._history.append(snapshot)
        self._reflection_count += 1
        if len(self._history) > 100:
            self._history = self._history[-100:]
        return snapshot

    def get_learning_plan(self) -> list[KnowledgeGap]:
        critical = [g for g in self._gaps if g.is_critical]
        critical.sort(key=lambda g: g.priority, reverse=True)
        return critical

    def suggest_relief(self) -> list[str]:
        suggestions = []
        if self._load.needs_relief:
            if self._load.active_tasks > 5:
                suggestions.append("减少并行任务数，聚焦关键目标")
            if self._load.context_window_usage > 0.8:
                suggestions.append("压缩上下文，遗忘低相关性记忆")
            if self._load.memory_pressure > 0.7:
                suggestions.append("将工作记忆转移到长期记忆")
            if self._load.pending_decisions > 3:
                suggestions.append("延迟非关键决策，优先处理紧急决策")
        return suggestions

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "reflection_count": self._reflection_count,
            "cognitive_load": {
                "total": self._load.total_load,
                "level": self._load.level.value,
                "needs_relief": self._load.needs_relief,
            },
            "capabilities": len(self._capabilities),
            "knowledge_gaps": len(self._gaps),
            "critical_gaps": len([g for g in self._gaps if g.is_critical]),
            "self_awareness": self.reflect().overall_self_awareness if self._history else 0.5,
        }
