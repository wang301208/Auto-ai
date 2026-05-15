from __future__ import annotations

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricSample:
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)


class Metric:
    def __init__(self, name: str, metric_type: MetricType, description: str = "", unit: str = ""):
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.unit = unit
        self._samples: list[MetricSample] = []
        self._value: float = 0.0

    def increment(self, value: float = 1.0, labels: dict | None = None) -> None:
        if self.metric_type == MetricType.COUNTER:
            self._value += value
        self._samples.append(MetricSample(value=self._value, labels=labels or {}))

    def set(self, value: float, labels: dict | None = None) -> None:
        self._value = value
        self._samples.append(MetricSample(value=value, labels=labels or {}))

    def observe(self, value: float, labels: dict | None = None) -> None:
        self._samples.append(MetricSample(value=value, labels=labels or {}))

    @property
    def value(self) -> float:
        return self._value

    def percentile(self, p: float) -> float:
        if not self._samples:
            return 0.0
        values = sorted(s.value for s in self._samples)
        idx = int(len(values) * p)
        return values[min(idx, len(values) - 1)]


class MetricsCollector:
    """指标收集器：Agent自分析自身telemetry的核心。"""

    def __init__(self):
        self._metrics: dict[str, Metric] = {}
        self._setup_default_metrics()

    def _setup_default_metrics(self) -> None:
        self.counter("llm_calls_total", "LLM调用总数", "calls")
        self.counter("llm_tokens_total", "LLM Token消耗总数", "tokens")
        self.counter("llm_cost_total", "LLM成本累计", "usd")
        self.counter("agent_tasks_total", "Agent任务总数", "tasks")
        self.counter("agent_errors_total", "Agent错误总数", "errors")
        self.counter("self_modify_total", "自修改总数", "modifications")
        self.counter("self_modify_success_total", "自修改成功总数", "modifications")
        self.gauge("agent_load", "Agent当前负载", "ratio")
        self.gauge("memory_usage_bytes", "内存使用量", "bytes")
        self.histogram("llm_latency_ms", "LLM延迟", "ms")
        self.histogram("task_duration_ms", "任务执行时长", "ms")
        self.histogram("self_modify_impact", "自修改影响评分", "score")

    def counter(self, name: str, description: str = "", unit: str = "") -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(name, MetricType.COUNTER, description, unit)
        return self._metrics[name]

    def gauge(self, name: str, description: str = "", unit: str = "") -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(name, MetricType.GAUGE, description, unit)
        return self._metrics[name]

    def histogram(self, name: str, description: str = "", unit: str = "") -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(name, MetricType.HISTOGRAM, description, unit)
        return self._metrics[name]

    def record_llm_call(self, model: str, prompt_tokens: int, completion_tokens: int,
                        cost: float, latency_ms: float) -> None:
        self._metrics["llm_calls_total"].increment(labels={"model": model})
        self._metrics["llm_tokens_total"].increment(prompt_tokens + completion_tokens, labels={"model": model})
        self._metrics["llm_cost_total"].increment(cost, labels={"model": model})
        self._metrics["llm_latency_ms"].observe(latency_ms, labels={"model": model})

    def record_task(self, task_type: str, duration_ms: float, success: bool) -> None:
        self._metrics["agent_tasks_total"].increment(labels={"type": task_type})
        self._metrics["task_duration_ms"].observe(duration_ms, labels={"type": task_type})
        if not success:
            self._metrics["agent_errors_total"].increment(labels={"type": task_type})

    def record_self_modify(self, success: bool, impact_score: float = 0.0) -> None:
        self._metrics["self_modify_total"].increment()
        if success:
            self._metrics["self_modify_success_total"].increment()
        self._metrics["self_modify_impact"].observe(impact_score)

    def get_summary(self) -> dict:
        result = {}
        for name, metric in self._metrics.items():
            entry: dict[str, Any] = {"type": metric.metric_type.value, "value": metric.value}
            if metric.metric_type == MetricType.HISTOGRAM and metric._samples:
                values = [s.value for s in metric._samples]
                entry["count"] = len(values)
                entry["p50"] = metric.percentile(0.5)
                entry["p95"] = metric.percentile(0.95)
                entry["p99"] = metric.percentile(0.99)
            result[name] = entry
        return result

    def detect_anomalies(self) -> list[dict]:
        anomalies = []
        error_rate = 0.0
        tasks = self._metrics.get("agent_tasks_total")
        errors = self._metrics.get("agent_errors_total")
        if tasks and tasks.value > 0 and errors:
            error_rate = errors.value / tasks.value
            if error_rate > 0.1:
                anomalies.append({"type": "high_error_rate", "value": error_rate, "threshold": 0.1})
        latency = self._metrics.get("llm_latency_ms")
        if latency and latency._samples:
            p95 = latency.percentile(0.95)
            if p95 > 5000:
                anomalies.append({"type": "high_latency_p95", "value": p95, "threshold": 5000})
        return anomalies
