from __future__ import annotations

import time
import uuid
import random
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DreamPhase(Enum):
    COLLECT = "collect"
    ASSOCIATE = "associate"
    RECOMBINE = "recombine"
    EVALUATE = "evaluate"
    INTEGRATE = "integrate"


@dataclass
class DreamInsight:
    """梦境洞见: Agent在自由联想中发现的新认知。"""
    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    source_memories: list[str] = field(default_factory=list)
    novelty_score: float = 0.0
    relevance_score: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    integrated: bool = False


@dataclass
class DreamSession:
    """梦境会话: 一次完整的记忆重组过程。"""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    memories_sampled: int = 0
    associations_found: int = 0
    insights: list[DreamInsight] = field(default_factory=list)
    phase: DreamPhase = DreamPhase.COLLECT

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def insight_count(self) -> int:
        return len(self.insights)


class DreamEngine:
    """梦境重组引擎: Agent在休眠期对长期记忆做自由联想, 发现隐含关联, 生成新洞见。

    灵感来自人类REM睡眠: 记忆巩固+创造性重组。
    """

    def __init__(self, llm_call: Callable | None = None, memory_provider: Any = None):
        self.llm_call = llm_call
        self.memory = memory_provider
        self._sessions: list[DreamSession] = []
        self._all_insights: list[DreamInsight] = []

    async def dream(self, agent_id: str = "", num_cycles: int = 3,
                    memory_sample_size: int = 20) -> DreamSession:
        """执行一次完整的梦境重组会话。"""
        session = DreamSession(agent_id=agent_id)
        logger.info(f"梦境开始: agent={agent_id}, 周期={num_cycles}")

        memories = self._collect_memories(memory_sample_size)
        session.memories_sampled = len(memories)
        session.phase = DreamPhase.ASSOCIATE

        for cycle in range(num_cycles):
            associations = self._find_associations(memories)
            session.associations_found += len(associations)

            recombined = self._recombine(associations)

            insights = self._evaluate_insights(recombined)
            session.insights.extend(insights)
            self._all_insights.extend(insights)

            if len(memories) > 5:
                memories = random.sample(memories, min(len(memories), memory_sample_size))

        session.phase = DreamPhase.INTEGRATE
        integrated = self._integrate_insights(session.insights)
        for insight in session.insights:
            if insight.insight_id in integrated:
                insight.integrated = True

        session.end_time = time.time()
        session.phase = DreamPhase.INTEGRATE
        self._sessions.append(session)
        logger.info(f"梦境结束: {session.insight_count}个洞见, {len(integrated)}个已整合, 耗时{session.duration_ms:.0f}ms")
        return session

    def _collect_memories(self, sample_size: int) -> list[dict]:
        if self.memory:
            try:
                if hasattr(self.memory, 'get_relevant'):
                    return self.memory.get_relevant("", k=sample_size)
                if hasattr(self.memory, '_items'):
                    return [{"content": m.content, "id": k} for k, m in list(self.memory._items.items())[:sample_size]]
            except Exception as e:
                logger.error(f"收集记忆失败: {e}")
        return [{"content": f"模拟记忆{i}", "id": f"mem_{i}"} for i in range(sample_size)]

    def _find_associations(self, memories: list[dict]) -> list[dict]:
        associations = []
        for i, m1 in enumerate(memories):
            for j, m2 in enumerate(memories):
                if i >= j:
                    continue
                c1 = m1.get("content", "").lower()
                c2 = m2.get("content", "").lower()
                c1_words = set(c1.split())
                c2_words = set(c2.split())
                overlap = c1_words & c2_words
                if len(overlap) >= 2 or (c1_words and len(overlap) / max(1, len(c1_words | c2_words)) > 0.15):
                    associations.append({
                        "memory_a": m1, "memory_b": m2,
                        "shared_concepts": list(overlap),
                        "strength": len(overlap) / max(1, len(c1_words | c2_words)),
                    })
        return associations[:50]

    def _recombine(self, associations: list[dict]) -> list[dict]:
        recombined = []
        for assoc in associations:
            a_content = assoc["memory_a"].get("content", "")
            b_content = assoc["memory_b"].get("content", "")
            shared = assoc.get("shared_concepts", [])
            recombination = {
                "premise_a": a_content[:200],
                "premise_b": b_content[:200],
                "bridge_concepts": shared,
                "novel_combination": f"如果'{a_content[:50]}'与'{b_content[:50]}'通过{shared}关联, 那么...",
                "strength": assoc.get("strength", 0),
            }
            recombined.append(recombination)
        return recombined

    def _evaluate_insights(self, recombined: list[dict]) -> list[DreamInsight]:
        insights = []
        for rec in recombined:
            novelty = min(1.0, rec.get("strength", 0) * 2 + random.uniform(0, 0.3))
            relevance = rec.get("strength", 0) + random.uniform(0, 0.2)
            if novelty > 0.3:
                content = rec.get("novel_combination", "")
                if self.llm_call:
                    try:
                        prompt = f"从以下记忆关联中提炼一个有价值的洞见:\n{content}\n\n洞见:"
                        content = str(self.llm_call(prompt))
                    except Exception:
                        pass
                insight = DreamInsight(
                    content=content,
                    source_memories=[rec.get("premise_a", "")[:50], rec.get("premise_b", "")[:50]],
                    novelty_score=novelty,
                    relevance_score=min(1.0, relevance),
                    confidence=novelty * relevance,
                )
                insights.append(insight)
        return insights

    def _integrate_insights(self, insights: list[DreamInsight]) -> list[str]:
        integrated = []
        for insight in insights:
            if insight.confidence > 0.15 and insight.novelty_score > 0.3:
                integrated.append(insight.insight_id)
                if self.memory and hasattr(self.memory, 'store'):
                    try:
                        self.memory.store(
                            f"[梦境洞见] {insight.content[:200]}",
                            importance=insight.confidence,
                        )
                    except Exception:
                        pass
        return integrated

    def get_dream_stats(self) -> dict:
        total_insights = sum(s.insight_count for s in self._sessions)
        integrated = sum(1 for i in self._all_insights if i.integrated)
        return {
            "total_sessions": len(self._sessions),
            "total_insights": total_insights,
            "integrated_insights": integrated,
            "integration_rate": integrated / max(1, total_insights),
        }
