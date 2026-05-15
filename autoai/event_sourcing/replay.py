from __future__ import annotations

import time
import logging
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from autoai.event_sourcing.stream import EventStream, AgentEvent, EventRecord, AgentEventType

logger = logging.getLogger(__name__)


class TimeTravelDebugger:
    """时间旅行调试器: 在任意时间点重建Agent完整状态, 回放意识流。"""

    def __init__(self, stream: EventStream):
        self.stream = stream
        self._breakpoints: dict[int, str] = {}
        self._watch_filters: list[Callable[[AgentEvent], bool]] = []

    def goto(self, sequence: int) -> dict:
        """时间旅行到指定事件序号, 重建Agent状态。"""
        if sequence < 1 or sequence > self.stream.total_events:
            return {"error": f"无效序号: {sequence}, 范围[1, {self.stream.total_events}]"}
        snapshot = self.stream.snapshot_at(sequence)
        events = self.stream.replay(until=sequence)
        state = self._rebuild_state(events)
        logger.info(f"时间旅行: 到达事件#{sequence}, 状态含{len(state)}个维度")
        return {
            "sequence": sequence,
            "snapshot": snapshot,
            "state": state,
            "event_count": len(events),
            "last_event": events[-1].to_dict() if events else None,
        }

    def replay_range(self, start: int, end: int, step: int = 1) -> list[dict]:
        """回放指定范围内的事件。"""
        results = []
        for seq in range(start, end + 1, step):
            record = self.stream.get_event_at(seq)
            if record:
                results.append({
                    "sequence": seq,
                    "event": record.event.to_dict(),
                    "hash": record.record_hash,
                })
        return results

    def diff(self, seq_a: int, seq_b: int) -> dict:
        """对比两个时间点的Agent状态差异。"""
        events_a = self.stream.replay(until=seq_a)
        events_b = self.stream.replay(until=seq_b)
        state_a = self._rebuild_state(events_a)
        state_b = self._rebuild_state(events_b)
        changes = {}
        all_keys = set(state_a.keys()) | set(state_b.keys())
        for key in all_keys:
            va = state_a.get(key)
            vb = state_b.get(key)
            if va != vb:
                changes[key] = {"from": va, "to": vb}
        return {"seq_a": seq_a, "seq_b": seq_b, "changes": changes, "change_count": len(changes)}

    def counterfactual(self, sequence: int, alternative_event: AgentEvent) -> dict:
        """反事实推理: "如果当时选了B会怎样?" """
        original = self.stream.get_event_at(sequence)
        if not original:
            return {"error": f"事件#{sequence}不存在"}
        events_before = self.stream.replay(until=sequence - 1)
        alt_events = events_before + [alternative_event]
        alt_state = self._rebuild_state(alt_events)
        orig_events = self.stream.replay(until=sequence)
        orig_state = self._rebuild_state(orig_events)
        divergence = {}
        for key in set(orig_state.keys()) | set(alt_state.keys()):
            ov = orig_state.get(key)
            av = alt_state.get(key)
            if ov != av:
                divergence[key] = {"actual": ov, "counterfactual": av}
        logger.info(f"反事实推理: 事件#{sequence}, 偏离维度={len(divergence)}")
        return {
            "sequence": sequence,
            "original_event": original.event.to_dict(),
            "alternative_event": alternative_event.to_dict(),
            "divergence": divergence,
            "divergence_count": len(divergence),
        }

    def set_breakpoint(self, sequence: int, label: str = "") -> None:
        self._breakpoints[sequence] = label or f"bp_{sequence}"

    def add_watch(self, filter_fn: Callable[[AgentEvent], bool]) -> None:
        self._watch_filters.append(filter_fn)

    def search_consciousness(self, query: str) -> list[dict]:
        """在Agent意识流中搜索特定内容。"""
        results = []
        query_lower = query.lower()
        for record in self.stream._events:
            if query_lower in record.event.content.lower():
                results.append({
                    "sequence": record.sequence_number,
                    "event_type": record.event.event_type.value,
                    "content": record.event.content[:200],
                    "timestamp": record.event.timestamp,
                })
        return results[:50]

    def _rebuild_state(self, events: list[AgentEvent]) -> dict:
        state: dict[str, Any] = {
            "total_thoughts": 0,
            "total_decisions": 0,
            "total_actions": 0,
            "total_mutations": 0,
            "total_errors": 0,
            "last_thought": None,
            "last_decision": None,
            "emotions": [],
            "knowledge_gained": [],
        }
        for event in events:
            if event.event_type == AgentEventType.THOUGHT:
                state["total_thoughts"] += 1
                state["last_thought"] = event.content[:200]
            elif event.event_type == AgentEventType.DECISION:
                state["total_decisions"] += 1
                state["last_decision"] = event.content[:200]
            elif event.event_type == AgentEventType.ACTION:
                state["total_actions"] += 1
                if not getattr(event, 'success', True):
                    state["total_errors"] += 1
            elif event.event_type == AgentEventType.SELF_MODIFY:
                state["total_mutations"] += 1
            elif event.event_type == AgentEventType.EMOTION:
                state["emotions"].append({
                    "type": getattr(event, 'emotion_type', ''),
                    "intensity": getattr(event, 'intensity', 0),
                })
            elif event.event_type == AgentEventType.MEMORY_OP:
                state["knowledge_gained"].append(event.content[:100])
        return state


class StateRebuilder:
    """状态重建器: 从事件流重建任意时刻的完整Agent状态。"""

    def __init__(self, stream: EventStream):
        self.stream = stream
        self._cache: dict[int, dict] = {}

    def rebuild_at(self, sequence: int) -> dict:
        if sequence in self._cache:
            return self._cache[sequence]
        events = self.stream.replay(until=sequence)
        state = self._build(events)
        self._cache[sequence] = state
        return state

    def _build(self, events: list[AgentEvent]) -> dict:
        return {
            "event_count": len(events),
            "types": list(set(e.event_type.value for e in events)),
            "agents": list(set(e.agent_id for e in events)),
            "time_range": (
                events[0].timestamp if events else 0,
                events[-1].timestamp if events else 0,
            ),
        }
