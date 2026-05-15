from __future__ import annotations

import time
import uuid
import json
import logging
import contextlib
from dataclasses import dataclass, field
from typing import Any, Optional, Iterator
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class SpanKind(Enum):
    THOUGHT = "thought"
    DECISION = "decision"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    SELF_MODIFY = "self_modify"
    MEMORY_OP = "memory_op"
    GOVERNANCE = "governance"
    MESH_COMM = "mesh_comm"


@dataclass
class BaseSpan:
    """分布式追踪Span基类：记录Agent的每一个思考、决策、行动。"""
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str = ""
    kind: SpanKind = SpanKind.THOUGHT
    name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    status: str = "ok"

    @property
    def duration_ms(self) -> float:
        if self.end_time > 0:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        self.events.append({"name": name, "timestamp": time.time(), "attributes": attributes or {}})

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        self.end_time = time.time()

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
        }


class ThoughtSpan(BaseSpan):
    """思考Span：记录Agent的推理过程。"""
    kind = SpanKind.THOUGHT
    reasoning_chain: str = ""
    confidence: float = 0.0


class DecisionSpan(BaseSpan):
    """决策Span：记录Agent的决策及理由。"""
    kind = SpanKind.DECISION
    decision: str = ""
    alternatives: list[str] = field(default_factory=list)
    rationale: str = ""


class ActionSpan(BaseSpan):
    """行动Span：记录Agent的执行及结果。"""
    kind = SpanKind.ACTION
    action_type: str = ""
    result: Any = None
    success: bool = True


class TelemetryTracer:
    """分布式追踪器：全链路追踪Agent的Thought→Decision→Action。"""

    def __init__(self, service_name: str = "autoai", export_path: str | None = None):
        self.service_name = service_name
        self.export_path = Path(export_path) if export_path else None
        self._traces: dict[str, list[BaseSpan]] = {}
        self._active_spans: dict[str, BaseSpan] = {}
        self._current_trace_id: str = ""

    def start_trace(self, name: str = "", attributes: dict | None = None) -> str:
        trace_id = uuid.uuid4().hex[:32]
        self._current_trace_id = trace_id
        self._traces[trace_id] = []
        root = BaseSpan(
            trace_id=trace_id,
            kind=SpanKind.THOUGHT,
            name=name or "trace_root",
            attributes={"service": self.service_name, **(attributes or {})},
        )
        self._traces[trace_id].append(root)
        self._active_spans[root.span_id] = root
        return trace_id

    def start_span(self, kind: SpanKind, name: str, parent_span_id: str = "",
                   attributes: dict | None = None) -> BaseSpan:
        trace_id = self._current_trace_id
        if trace_id not in self._traces:
            trace_id = self.start_trace(name)
        span_cls = {
            SpanKind.THOUGHT: ThoughtSpan,
            SpanKind.DECISION: DecisionSpan,
            SpanKind.ACTION: ActionSpan,
        }.get(kind, BaseSpan)
        span = span_cls(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            kind=kind,
            name=name,
            attributes=attributes or {},
        )
        self._traces[trace_id].append(span)
        self._active_spans[span.span_id] = span
        return span

    def end_span(self, span: BaseSpan) -> None:
        span.end()
        self._active_spans.pop(span.span_id, None)

    @contextlib.contextmanager
    def span(self, kind: SpanKind, name: str, **kwargs) -> Iterator[BaseSpan]:
        s = self.start_span(kind, name, **kwargs)
        try:
            yield s
        except Exception as e:
            s.status = "error"
            s.set_attribute("error", str(e))
            raise
        finally:
            self.end_span(s)

    def get_trace(self, trace_id: str) -> list[BaseSpan]:
        return self._traces.get(trace_id, [])

    def export_trace(self, trace_id: str) -> dict:
        spans = self.get_trace(trace_id)
        return {
            "trace_id": trace_id,
            "service": self.service_name,
            "spans": [s.to_dict() for s in spans],
            "span_count": len(spans),
            "total_duration_ms": sum(s.duration_ms for s in spans),
        }

    def save_trace(self, trace_id: str) -> None:
        if not self.export_path:
            return
        data = self.export_trace(trace_id)
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        trace_file = self.export_path / f"trace_{trace_id}.json"
        trace_file.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def get_stats(self) -> dict:
        total_spans = sum(len(spans) for spans in self._traces.values())
        return {
            "total_traces": len(self._traces),
            "total_spans": total_spans,
            "active_spans": len(self._active_spans),
        }


_global_tracer: Optional[TelemetryTracer] = None


def get_tracer(service_name: str = "autoai", export_path: str | None = None) -> TelemetryTracer:
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = TelemetryTracer(service_name, export_path)
    return _global_tracer
